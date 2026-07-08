package bridge.workflow

import bridge.Bridge
import bridge.workflow.events.ActionContext
import bridge.workflow.events.WorkflowEvent

/**
 * Represents a command produced by the workflow engine.
 *
 * Commands are executed by the WorkflowEngine after a handler
 * finishes processing an event.
 */
sealed interface WorkflowCommand

/**
 * Transition the workflow to another state.
 */
data class TransitionCommand(

    val workflowId: String,

    val nextState: WorkflowState,

    val nextStep: WorkflowStep

) : WorkflowCommand

/**
 * Publish a new workflow event.
 */
data class PublishEventCommand(

    val event: WorkflowEvent

) : WorkflowCommand

/**
 * Verify the requesting agent using the Guardian.
 */
data class VerifyAgentCommand(

    val workflowId: String,

    val requestId: String,

    val context: ActionContext

) : WorkflowCommand

/**
 * Ask the Vault to evaluate the request.
 *
 * The Vault decides whether:
 * - the action can be executed outside the Vault,
 * - user approval is required,
 * - the Vault should execute the sensitive part itself.
 */
data class RequestVaultEvaluationCommand(

    val workflowId: String,

    val requestId: String,

    val amount: String,

    val currency: String

) : WorkflowCommand

/**
 * Notify the external agent.
 */
data class NotifyAgentCommand(

    val requestId: String,

    val message: String

) : WorkflowCommand

data class UpdateActionStatusCommand(

    val requestId: String,

    val status: Bridge.StatusType,

    val resultData: String? = null

) : WorkflowCommand