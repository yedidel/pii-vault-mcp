package bridge.workflow.handler

import bridge.workflow.WorkflowContext
import bridge.workflow.WorkflowDecision
import bridge.workflow.WorkflowEventType
import bridge.workflow.events.WorkflowEvent

/**
 * Handles a specific workflow event.
 *
 * Implementations contain only business logic and return a
 * WorkflowDecision describing what the engine should do next.
 */
interface WorkflowEventHandler<T : WorkflowEvent> {

    /**
     * Supported event type.
     */
    val eventType: WorkflowEventType

    /**
     * Process the event using the current workflow context.
     */
    fun handle(
        context: WorkflowContext,
        event: T
    ): WorkflowDecision
}