package bridge.workflow.events

import bridge.workflow.WorkflowEventType
import java.time.Instant
import java.util.UUID

/**
 * Base contract for every workflow event.
 */
sealed interface WorkflowEvent {

    val eventId: UUID

    val workflowId: String

    val requestId: String

    val timestamp: Instant

    val eventType: WorkflowEventType
}