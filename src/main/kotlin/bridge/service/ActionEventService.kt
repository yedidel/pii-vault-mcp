package bridge
import bridge.Bridge.StatusType
import bridge.service.ActionStatusChangedEvent
import org.springframework.stereotype.Service

/**
 * Service that creates an ActionStatusChangedEvent when an action's status changes
 * to one that should be reported to the agent.
 */
@Service
class ActionEventService {

    // Status values that should be reported to the agent when an action reaches them.
    // Keep this set focused on states that require external notification.
    private val agentReportableStatuses = setOf(
        StatusType.REJECTED,
        StatusType.COMPLETED,
        StatusType.FAILED,
        StatusType.FAILED_APP_NOT_INSTALLED
    )

    /**
     * Check whether a status change should produce an ActionStatusChangedEvent.
     *
     * @param requestId the id of the request whose status changed
     * @param oldStatus the previous status
     * @param newStatus the current status
     * @param details optional map with extra information to include in the event
     * @return an ActionStatusChangedEvent when the change should be reported, or null otherwise
     *
     * Behavior:
     * - If the status did not change, return null.
     * - If the new status is in [agentReportableStatuses], construct and return an event.
     * - Otherwise return null.
     */
    fun checkIfChange(
        requestId: String,
        oldStatus: StatusType,
        newStatus: StatusType,
        details: Map<String, String> = emptyMap()
    ): ActionStatusChangedEvent? {
        // No change -> nothing to report.
        if (oldStatus == newStatus) {
            return null
        }

        // If the new status should be reported, build the event with provided details.
        if (newStatus in agentReportableStatuses) {
            return ActionStatusChangedEvent(
                requestId = requestId,
                previousStatusType = oldStatus,
                currentStatusType = newStatus,
                details = details
            )
        }

        // Status changed but not to a reportable one -> nothing to report.
        return null
    }
}
