package bridge
import bridge.Bridge.ActionRequest
import bridge.Bridge.ActionResponse
import bridge.Bridge.StatusType
import java.util.UUID

/**
 * gRPC service implementation for the Bridge component.
 */
class BridgeServiceImpl : BridgeServiceGrpcKt.BridgeServiceCoroutineImplBase() {
    // suspend function – can wait for long operations without blocking a thread
    override suspend fun sendAction(request: Bridge.ActionRequest): ActionResponse {
        println(
            "Received ${request.action} request from agent ${request.agentId} " +
                "for target ${request.targetDomain}",
        )

        return ActionResponse.newBuilder()
            .setRequestId(UUID.randomUUID().toString())
            .setStatus(StatusType.RECEIVED)
            .build()
    }
}
