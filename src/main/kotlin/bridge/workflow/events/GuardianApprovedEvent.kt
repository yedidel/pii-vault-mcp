package bridge.workflow.events

import bridge.workflow.WorkflowEventType
import java.time.Instant
import java.util.UUID

/**
 * Published after the Guardian approves the requesting agent.
 */
data class GuardianApprovedEvent(

    override val eventId: UUID = UUID.randomUUID(),

    override val workflowId: String,

    override val requestId: String,

    override val timestamp: Instant = Instant.now(),

    override val eventType: WorkflowEventType = WorkflowEventType.GUARDIAN_APPROVED,

    val context: ActionContext,

    val trustLevel: String
) : WorkflowEvent