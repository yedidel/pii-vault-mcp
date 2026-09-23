package bridge

import bridge.Bridge.ActionResponse
import bridge.Bridge.PolicyEvaluationResponse
import bridge.Bridge.StatusResponse
import bridge.mapper.toConnectorType
import bridge.policy.PolicyErrorCode
import bridge.policy.PolicyEvaluationService
import bridge.policy.VaultPolicyReply
import bridge.repository.WorkflowRepository
import bridge.workflow.WorkflowInitializationService
import com.fasterxml.jackson.databind.ObjectMapper
import io.grpc.Status
import org.springframework.stereotype.Service

/**
 * BridgeServiceImpl
 *
 * Entry point for incoming agent requests.
 * Persists the action, initializes a workflow and returns immediately.
 */
@Service
class BridgeServiceImpl(

    private val actionService: ActionService,

    private val workflowInitializationService: WorkflowInitializationService,

    private val workflowRepository: WorkflowRepository,

    private val objectMapper: ObjectMapper,

    private val policyEvaluationService: PolicyEvaluationService,

    ) : BridgeServiceGrpcKt.BridgeServiceCoroutineImplBase() {

    override suspend fun sendAction(
        request: Bridge.ActionRequest,
    ): ActionResponse {

        println(
            "--- [BRIDGE] Processing ${request.actionType} for agent ${request.agentId} ---"
        )

        val responseEntity =
            try {
                actionService.handleAction(request)
            } catch (e: Exception) {

                println(
                    "--- [BRIDGE] Action rejected: ${e.message} ---"
                )

                return ActionResponse.newBuilder()
                    .setStatus(Bridge.StatusType.FAILED)
                    .setDescription(
                        "Action rejected by bridge safety layer: ${e.message}"
                    )
                    .build()
            }

        // Idempotent SendAction: ActionService may reuse a recent identical
        // action. Never create a second workflow for the same request_id
        // (workflows.request_id is unique).
        val existingWorkflow =
            workflowRepository.findByRequestId(responseEntity.requestId)
        if (existingWorkflow != null) {
            println(
                "--- [BRIDGE] Reusing existing workflow " +
                    "${existingWorkflow.workflowId} for request " +
                    "${responseEntity.requestId} ---"
            )
            return ActionResponse.newBuilder()
                .setRequestId(responseEntity.requestId)
                .setWorkflowId(existingWorkflow.workflowId)
                .setStatus(responseEntity.status)
                .setDescription(
                    responseEntity.description.ifBlank {
                        "Duplicate request detected; returning existing workflow."
                    }
                )
                .build()
        }

        val parameters =
            objectMapper.convertValue(
                request.parametersMap,
                Map::class.java,
            ) as Map<String, String>

        val workflow = try {
            workflowInitializationService.initializeWorkflow(
                requestId = responseEntity.requestId,
                agentId = request.agentId,
                userInstallId = request.userInstallId,
                actionType = request.actionType,
                connectorType = request.connectorType.toConnectorType(),
                connectorContext = request.connectorContext,
                parameters = parameters,
            )
        } catch (e: Exception) {
            println("========== WORKFLOW INIT FAILED ==========")
            e.printStackTrace()
            throw Status.INTERNAL
                .withDescription(
                    "Workflow initialization failed: ${e.message ?: e.javaClass.simpleName}"
                )
                .withCause(e)
                .asRuntimeException()
        }

        return ActionResponse.newBuilder()
            .setRequestId(responseEntity.requestId)
            .setWorkflowId(workflow.workflowId)
            .setStatus(Bridge.StatusType.RECEIVED)
            .setDescription(
                "Action received and workflow initiated."
            )
            .build()
    }

    override suspend fun getActionStatus(
        request: Bridge.StatusRequest,
    ): StatusResponse {

        val action =
            actionService.getActionById(request.requestId)

        return StatusResponse.newBuilder()
            .setRequestId(action.requestId)
            .setStatus(action.status)
            .setResultData(action.resultData ?: "")
            .setUpdatedAt(StatusTimestamps.fromLocalDateTime(action.updatedAt))
            .build()
    }

    override suspend fun evaluatePolicy(
        request: Bridge.PolicyEvaluationRequest,
    ): PolicyEvaluationResponse {
        val reply = policyEvaluationService.evaluate(
            agentId = request.agentId,
            userInstallId = request.userInstallId,
            actionType = request.actionType,
            fieldNames = request.fieldNamesList.toList(),
        )
        when (reply) {
            is VaultPolicyReply.Success -> {
                return PolicyEvaluationResponse.newBuilder()
                    .setPolicyRequestId(reply.policyRequestId)
                    .setActionType(reply.actionType.ifBlank { request.actionType.uppercase() })
                    .setDecision(reply.decision)
                    .addAllAgentAllowed(reply.agentAllowed)
                    .addAllVaultRequired(reply.vaultRequired)
                    .setUserApprovalRequired(reply.userApprovalRequired)
                    .build()
            }
            is VaultPolicyReply.Failure -> {
                throw policyErrorStatus(reply.error.code)
                    .withDescription(reply.error.message)
                    .asRuntimeException()
            }
        }
    }

    private fun policyErrorStatus(code: PolicyErrorCode): Status {
        return when (code) {
            PolicyErrorCode.VAULT_DISCONNECTED -> Status.UNAVAILABLE
            PolicyErrorCode.TIMEOUT -> Status.DEADLINE_EXCEEDED
            PolicyErrorCode.INVALID_REQUEST -> Status.INVALID_ARGUMENT
            PolicyErrorCode.INVALID_USER_INSTALL -> Status.FAILED_PRECONDITION
            PolicyErrorCode.UNKNOWN_ACTION -> Status.FAILED_PRECONDITION
            PolicyErrorCode.MALFORMED_POLICY -> Status.INTERNAL
            PolicyErrorCode.INTERNAL -> Status.INTERNAL
        }
    }
}
