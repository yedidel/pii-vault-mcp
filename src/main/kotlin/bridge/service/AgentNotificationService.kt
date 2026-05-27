package bridge.service
import bridge.Bridge
import org.springframework.stereotype.Service

/**
 * Service responsible for converting internal action status change events
 * into a `NotifyAgent` message that can be sent to an external agent.
 *
 * Keep logic here small: map status to a human-readable message and include details.
 */
@Service
class AgentNotificationService {

    /**
     * Build a `NotifyAgent` object from an `ActionStatusChangedEvent`.
     *
     * - Chooses a simple, user-facing message based on the event's current status.
     * - Preserves the original `details` map so callers can include debug or context info.
     *
     * @param event the status-change event to convert
     * @return a `NotifyAgent` DTO ready to be serialized/sent to the agent
     */
    fun sendStatusUpdate(event: ActionStatusChangedEvent): NotifyAgent {
        // Map internal status to a short, clear message for the agent.
        val message = when (event.currentStatusType) {
            Bridge.StatusType.COMPLETED -> "The action completed successfully"
            Bridge.StatusType.FAILED -> "The action failed"
            Bridge.StatusType.REJECTED -> "The action was rejected by the user"
            Bridge.StatusType.FAILED_APP_NOT_INSTALLED -> "The required application is not installed"
            // Fallback message for any other status values.
            else -> "The action status has changed"
        }

        // Return a simple DTO that carries id, status, message and optional details.
        return NotifyAgent(
            requestId = event.requestId,
            statusType = event.currentStatusType,
            message = message,
            details = event.details
        )
    }
}

/**
 * Data transfer object sent to the agent.
 *
 * @param requestId the identifier of the original request/action
 * @param statusType the current status enum value
 * @param message a short human-readable message describing the status
 * @param details optional key/value map with extra context or diagnostics
 */
data class NotifyAgent(
    val requestId: String,
    val statusType: Bridge.StatusType,
    val message: String,
    val details: Map<String, String> = emptyMap()
)
