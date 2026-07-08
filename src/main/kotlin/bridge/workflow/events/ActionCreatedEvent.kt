package bridge.workflow.events
import bridge.workflow.WorkflowEventType
import java.time.Instant
import java.util.UUID

/**
 * Published immediately after a new workflow is created.
 */
data class ActionCreatedEvent(

    override val eventId: UUID = UUID.randomUUID(),

    override val workflowId: String,

    override val requestId: String,

    override val timestamp: Instant = Instant.now(),

    override val eventType: WorkflowEventType = WorkflowEventType.ACTION_CREATED,

    val context: ActionContext

) : WorkflowEvent