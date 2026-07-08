package bridge.workflow.events

import bridge.workflow.WorkflowEventType
import java.time.Instant
import java.util.UUID

/**
 * Published after workflow execution fails.
 */
data class WorkflowFailedEvent(

    override val eventId: UUID = UUID.randomUUID(),

    override val workflowId: String,

    override val requestId: String,

    override val timestamp: Instant = Instant.now(),

    override val eventType: WorkflowEventType = WorkflowEventType.WORKFLOW_FAILED,

    val context: ActionContext,

    val failureReason: String
) : WorkflowEvent