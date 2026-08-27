package bridge.workflow.handler

import bridge.workflow.VaultEvaluationCommandFactory
import bridge.workflow.TransitionCommand
import bridge.workflow.WorkflowContext
import bridge.workflow.WorkflowDecision
import bridge.workflow.WorkflowEventType
import bridge.workflow.WorkflowState
import bridge.workflow.WorkflowStep
import bridge.workflow.events.GuardianApprovedEvent
import org.springframework.stereotype.Component

/**
 * Handles GuardianApprovedEvent.
 *
 * After the Guardian approves the requesting agent,
 * the request is forwarded to the Vault for evaluation.
 */
@Component
class GuardianApprovedEventHandler :
    AbstractWorkflowEventHandler<GuardianApprovedEvent>() {

    override val eventType =
        WorkflowEventType.GUARDIAN_APPROVED

    override fun handle(
        context: WorkflowContext,
        event: GuardianApprovedEvent
    ): WorkflowDecision {

        return WorkflowDecision(

            commands = listOf(

                TransitionCommand(
                    workflowId = event.workflowId,
                    nextState = WorkflowState.WAITING_FOR_VAULT_RESPONSE,
                    nextStep = WorkflowStep.REQUEST_VAULT_EVALUATION
                ),

                VaultEvaluationCommandFactory.fromContext(
                    workflowId = event.workflowId,
                    requestId = event.requestId,
                    context = event.context,
                )

            )

        )
    }
}