package bridge.workflow

import bridge.ActionService
import bridge.integration.GuardianGateway
import bridge.integration.VaultGateway
import bridge.transport.AgentTransportRegistry
import bridge.workflow.publisher.WorkflowEventPublisher
import bridge.workflow.state.WorkflowTransitionService
import org.springframework.stereotype.Component

@Component
class WorkflowCommandExecutor(

    private val transitionService: WorkflowTransitionService,

    private val guardianGateway: GuardianGateway,

    private val vaultGateway: VaultGateway,

    private val workflowEventPublisher: WorkflowEventPublisher,

    private val transportRegistry: AgentTransportRegistry,

    private val actionService: ActionService

) {
    fun execute(context: WorkflowContext, decision: WorkflowDecision){
        decision.commands.forEach {execute(context, it) }
    }

    private fun execute(context: WorkflowContext,command: WorkflowCommand) {

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
                transportRegistry.send(
                    transport = context.continuationTransport,
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