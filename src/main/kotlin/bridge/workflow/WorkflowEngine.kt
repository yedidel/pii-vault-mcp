package bridge.workflow

import bridge.workflow.events.WorkflowEvent
import bridge.workflow.handler.AbstractWorkflowEventHandler
import org.springframework.stereotype.Component
import org.springframework.beans.factory.ObjectProvider

/**
 * Orchestrates workflow execution.
 *
 * Responsibilities:
 * - Load workflow context from repository
 * - Route incoming events to the appropriate handler
 * - Execute the resulting commands
 *
 * The engine contains no business logic; it is a pure orchestrator.
 */
@Component
class WorkflowEngine(

    private val contextLoader: WorkflowContextLoader,

    private val commandExecutor: WorkflowCommandExecutor,

    // Use ObjectProvider to resolve all handlers at runtime without explicit wiring
    private val handlers: ObjectProvider<List<AbstractWorkflowEventHandler<*>>>

) {

    /**
     * Process an incoming workflow event.
     */
    fun process(event: WorkflowEvent) {
        println("--- [WORKFLOW] Processing event type: ${event.eventType} for workflow: ${event.workflowId} ---")

        try {
            // Load the current workflow context
            val context = contextLoader.load(event.workflowId)

            // Find the handler for this event type
            val handler = findHandler(event)
            if (handler == null) {
                println("--- [WORKFLOW] WARNING: No handler found for event type: ${event.eventType} ---")
                return
            }

            // Handle the event and get the decision
            @Suppress("UNCHECKED_CAST")
            val typedHandler = handler as AbstractWorkflowEventHandler<WorkflowEvent>
            val decision = typedHandler.handle(context, event)

            // Execute all commands in the decision
            commandExecutor.execute(decision)

            println("--- [WORKFLOW] Event processing completed for workflow: ${event.workflowId} ---")
        } catch (e: Exception) {
            println("--- [WORKFLOW ERROR] Failed to process event ${event.eventType}: ${e.message} ---")
            e.printStackTrace()
        }
    }

    /**
     * Find the handler for the given event type.
     */
    private fun findHandler(event: WorkflowEvent): AbstractWorkflowEventHandler<*>? {
        return handlers.getIfAvailable()?.find { handler ->
            handler.eventType == event.eventType
        }
    }
}

