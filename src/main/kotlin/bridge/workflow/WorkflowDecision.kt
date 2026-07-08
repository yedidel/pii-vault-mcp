package bridge.workflow

/**
 * Result returned by a workflow event handler.
 *
 * The workflow engine executes every command
 * contained in the decision.
 */
data class WorkflowDecision(

    val commands: List<WorkflowCommand>

)