package bridge.workflow

import bridge.ActionService
import bridge.integration.GuardianGateway
import bridge.integration.VaultGateway
import bridge.workflow.publisher.WorkflowEventPublisher
import bridge.workflow.state.WorkflowTransitionService
import continuation.ContinuationRequest
import continuation.WorkflowContinuationService
import org.springframework.stereotype.Component

@Component
class WorkflowCommandExecutor(

    private val transitionService: WorkflowTransitionService,

    private val guardianGateway: GuardianGateway,

    private val vaultGateway: VaultGateway,

    private val workflowEventPublisher: WorkflowEventPublisher,

    private val workflowContinuationService: WorkflowContinuationService,

    private val actionService: ActionService,

    ) {

    fun execute(
        context: WorkflowContext,
        decision: WorkflowDecision,
    ) {
        decision.commands.forEach {
            println("Executing command: ${it::class.simpleName}")
            execute(context, it)
        }
    }

    private fun execute(
        context: WorkflowContext,
        command: WorkflowCommand,
    ) {

        when (command) {

            is TransitionCommand -> {
                val updated = transitionService.transition(
                    workflowId = command.workflowId,
                    nextState = command.nextState,
                    nextStep = command.nextStep,
                )
                // Keep the in-memory context aligned so later commands in
                // the same decision (e.g. NotifyAgent) see the new state.
                context.currentState = updated.currentState
                context.currentStep = updated.currentStep
            }

            is PublishEventCommand -> {
                workflowEventPublisher.publish(command.event)
            }

            is VerifyAgentCommand -> {
                guardianGateway.verifyAgent(
                    workflowId = command.workflowId,
                    requestId = command.requestId,
                    context = command.context,
                )
            }

            is RequestVaultEvaluationCommand -> {
                vaultGateway.requestEvaluation(command)
            }

            is NotifyAgentCommand -> {

                val request = ContinuationRequest(
                    workflowId = context.workflowId,
                    requestId = command.requestId,
                    connectorContext = context.actionContext.connectorContext,
                    status = context.currentState.name,
                    message = command.message,
                )

                workflowContinuationService.continueWorkflow(
                    connectorType = context.actionContext.connectorType,
                    request = request,
                )
            }

            is UpdateActionStatusCommand -> {
                actionService.updateActionStatus(
                    requestId = command.requestId,
                    finalStatus = command.status,
                    resultData = command.resultData,
                )
            }
        }
    }
}