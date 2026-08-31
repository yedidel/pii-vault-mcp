package bridge

import bridge.Bridge.ActionResponse
import bridge.Bridge.StatusResponse
import bridge.mapper.toConnectorType
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
                "Action received and workflow initiated. Use GetActionStatus to poll for completion."
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
            .build()
    }
}
