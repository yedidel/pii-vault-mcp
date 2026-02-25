package bridge
import bridge.Bridge.StatusRequest
import bridge.Bridge.StatusResponse
import bridge.Bridge.ActionResponse
import bridge.Bridge.ActionRequest
import bridge.Bridge.StatusType
import java.util.UUID

/**
 * gRPC service implementation for the Bridge component.
 */
class BridgeServiceImpl : BridgeServiceGrpcKt.BridgeServiceCoroutineImplBase() {
    // suspend function – can wait for long operations without blocking a thread
    override suspend fun sendAction(request: Bridge.ActionRequest): ActionResponse {
        println(
            "Received payment request from agent ${request.agentId} ")

        return ActionResponse.newBuilder()
            .setRequestId(UUID.randomUUID().toString())
            .setStatus(StatusType.RECEIVED)
            .build()
    }

    /**
     * return the status of request by the agent pool
     */
    override suspend fun getActionStatus(request:Bridge.StatusRequest): Bridge.StatusResponse{
        return StatusResponse.newBuilder()
            .setRequestId(request.requestId)
            .setStatus(StatusType.RECEIVED).build()
    }
}
