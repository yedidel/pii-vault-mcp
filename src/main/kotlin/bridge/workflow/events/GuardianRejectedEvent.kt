package bridge.workflow.events

import bridge.workflow.WorkflowEventType
import java.time.Instant
import java.util.UUID

/**
 * Published after the Guardian rejects the requesting agent.
 */
data class GuardianRejectedEvent(

    override val eventId: UUID = UUID.randomUUID(),

    override val workflowId: String,

    override val requestId: String,

    override val timestamp: Instant = Instant.now(),

    override val eventType: WorkflowEventType = WorkflowEventType.GUARDIAN_REJECTED,

    val context: ActionContext,

    val reason: String
) : WorkflowEvent