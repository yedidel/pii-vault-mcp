package bridge

import bridge.Bridge.ActionResponse
import bridge.Bridge.StatusResponse
import bridge.workflow.WorkflowInitializationService
import com.fasterxml.jackson.databind.ObjectMapper
import org.springframework.stereotype.Service
import bridge.mapper.toConnectorType
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

        val parameters =
            objectMapper.convertValue(
                request.parametersMap,
                Map::class.java,
            ) as Map<String, String>

        println("Reached initializeWorkflow")
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
            throw e
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
            .build()
    }
}