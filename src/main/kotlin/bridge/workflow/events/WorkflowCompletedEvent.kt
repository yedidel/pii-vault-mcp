package bridge.workflow.events

import bridge.workflow.WorkflowEventType
import java.time.Instant
import java.util.UUID

/**
 * Legacy Kafka payload type. Not published by the active workflow.
 * Terminal NotifyAgent is issued from ACTION_RESPONSE_RECEIVED / GUARDIAN_REJECTED.
 * Kept so leftover bus messages can be deserialized and ignored.
 */
data class WorkflowCompletedEvent(

    override val eventId: UUID = UUID.randomUUID(),

    override val workflowId: String,

    override val requestId: String,

    override val timestamp: Instant = Instant.now(),

    override val eventType: WorkflowEventType = WorkflowEventType.WORKFLOW_COMPLETED,

    val context: ActionContext
) : WorkflowEvent
