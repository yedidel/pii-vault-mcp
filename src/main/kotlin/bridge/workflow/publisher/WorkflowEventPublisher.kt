package bridge.workflow.publisher

import bridge.workflow.events.WorkflowEvent

/**
 * Publishes workflow events.
 *
 * The workflow engine depends only on this abstraction and is
 * independent of the underlying messaging infrastructure.
 */
interface WorkflowEventPublisher {

    /**
     * Publishes a workflow event.
     *
     * @param event workflow event to publish.
     */
    fun publish(event: WorkflowEvent)
}