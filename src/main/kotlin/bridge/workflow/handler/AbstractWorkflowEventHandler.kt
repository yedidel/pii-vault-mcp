package bridge.workflow.handler

import bridge.workflow.WorkflowContext
import bridge.workflow.WorkflowDecision
import bridge.workflow.WorkflowEventType
import bridge.workflow.events.WorkflowEvent

/**
 * Base class for workflow event handlers.
 *
 * Every handler is responsible for one specific workflow event.
 * It receives the current workflow context and returns a decision
 * describing what should happen next.
 */
abstract class AbstractWorkflowEventHandler<T : WorkflowEvent> :
    WorkflowEventHandler<T> {

    abstract override val eventType: WorkflowEventType

    abstract override fun handle(
        context: WorkflowContext,
        event: T
    ): WorkflowDecision
}