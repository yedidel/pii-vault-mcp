package bridge
import bridge.BridgeServiceGrpcKt
import bridge.Bridge.ActionRequest
import bridge.Bridge.ActionResponse
import bridge.Bridge.StatusType
import bridge.Bridge.ActionType

class BridgeServiceImpl :
    BridgeServiceGrpcKt.BridgeServiceCoroutineImplBase() {
        override suspend fun sendAction(
        request: Bridge.ActionRequest
    ): ActionResponse {

        return ActionResponse.newBuilder()
            .setRequestId(1)
            .setStatus(StatusType.DONE)
            .build()
    }
}