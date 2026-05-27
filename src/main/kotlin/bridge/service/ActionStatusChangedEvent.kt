package bridge.service
import bridge.Bridge.StatusType

/**
 * Event produced when an action's status changes.
 *
 * This lightweight DTO carries the request identifier, the previous and current
 * status values, and an optional details map for additional context or diagnostics.
 *
 * @param requestId the identifier of the original request/action
 * @param previousStatusType the status value before the change
 * @param currentStatusType the status value after the change
 * @param details optional key/value map with extra context; defaults to an empty map
 */
data class ActionStatusChangedEvent(
    val requestId: String,
    val previousStatusType: StatusType,
    val currentStatusType: StatusType,
    val details: Map<String, String> = emptyMap()

)