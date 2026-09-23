package bridge.workflow

import bridge.workflow.events.ActionContext

/**
 * Runtime workflow state.
 *
 * Unlike ActionContext, which is immutable,
 * WorkflowContext changes during workflow execution.
 */
data class WorkflowContext(

    val workflowId: String,

    val requestId: String,

    val actionContext: ActionContext,

    var currentState: WorkflowState,

    var currentStep: WorkflowStep,
)