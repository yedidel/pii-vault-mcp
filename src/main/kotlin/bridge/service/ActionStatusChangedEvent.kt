package bridge.service
import bridge.Bridge.StatusType

data class ActionStatusChangedEvent(
    val requestId: String,
    val previousStatusType: StatusType,
    val currentStatusType: StatusType,
)