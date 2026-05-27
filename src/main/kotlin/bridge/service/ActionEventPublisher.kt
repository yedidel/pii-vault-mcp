package bridge.service

import org.springframework.stereotype.Service

/**
 * Service that publishes internal action status change events to the agent layer.
 *
 * Converts an [ActionStatusChangedEvent] into a notification via
 */
@Service
class ActionEventPublisherService(
    private val agentNotificationService: AgentNotificationService
) {
    /**
     * Receive an action status change event and forward it to the agent notifier.
     * @param event the status-change event to publish
     * Behavior:
     * Uses [AgentNotificationService.sendStatusUpdate] to build the notification DTO.
     */
    fun publish(event: ActionStatusChangedEvent) {
        // Convert the event into a notification DTO for the agent.
        val notification = agentNotificationService.sendStatusUpdate(event)

        // Simple output for debugging/observability. Replace with real logging if needed.
        println(notification)
    }
}
