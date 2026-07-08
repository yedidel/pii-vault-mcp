package bridge.workflow

import bridge.ActionService
import bridge.integration.AgentGateway
import bridge.integration.GuardianGateway
import bridge.integration.VaultGateway
import bridge.workflow.publisher.WorkflowEventPublisher
import bridge.workflow.state.WorkflowTransitionService
import org.springframework.stereotype.Component

@Component
class WorkflowCommandExecutor(

    private val transitionService: WorkflowTransitionService,

    private val guardianGateway: GuardianGateway,

    private val vaultGateway: VaultGateway,

    private val workflowEventPublisher: WorkflowEventPublisher,

    private val agentGateway: AgentGateway,

    private val actionService: ActionService

) {

    fun execute(decision: WorkflowDecision) {
        decision.commands.forEach(::execute)
    }

    private fun execute(command: WorkflowCommand) {

        when (command) {

            is TransitionCommand -> {
                transitionService.transition(
                    workflowId = command.workflowId,
                    nextState = command.nextState,
                    nextStep = command.nextStep
                )
            }

            is PublishEventCommand -> {
                workflowEventPublisher.publish(command.event)
            }

            is VerifyAgentCommand -> {
                guardianGateway.verifyAgent(
                    workflowId = command.workflowId,
                    requestId = command.requestId,
                    context = command.context
                )
            }

            is RequestVaultEvaluationCommand -> {
                vaultGateway.requestApproval(
                    workflowId = command.workflowId,
                    requestId = command.requestId,
                    amount = command.amount,
                    currency = command.currency
                )
            }

            is NotifyAgentCommand -> {
                agentGateway.notify(
                    requestId = command.requestId,
                    message = command.message
                )
            }

            is UpdateActionStatusCommand -> {
                actionService.updateActionStatus(
                    requestId = command.requestId,
                    finalStatus = command.status,
                    resultData = command.resultData
                )
            }
        }
    }
}