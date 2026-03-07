package bridge
import bridge.Bridge.ActionResponse
import bridge.Bridge.StatusResponse
import org.springframework.stereotype.Service
/**
 * gRPC server implementation for the Bridge service.
 * Responsible for receiving requests from agents and delegating them to ActionService.
 */
@Service
class BridgeServiceImpl(
    private val actionService: ActionService
) : BridgeServiceGrpcKt.BridgeServiceCoroutineImplBase() {
    // suspend function – can wait for long operations without blocking a thread
    /**
     * Receives an action request from the agent and forwards it to ActionService
     * for validation and processing.
     */
    override suspend fun sendAction(request: Bridge.ActionRequest): ActionResponse {
        println(
            "Received ${request.actionType} request from agent ${request.agentId} ",
        )
        return actionService.handleAction(request);
    }
    /**
     * Returns the current status of a request based on its requestId.
     */
    override suspend fun getActionStatus(request: Bridge.StatusRequest): Bridge.StatusResponse  {
        val action=actionService.getActionById(request.requestId);
        return StatusResponse.newBuilder()
            .setRequestId(action.requestId)
            .setStatus(action.status).build()
    }

}
