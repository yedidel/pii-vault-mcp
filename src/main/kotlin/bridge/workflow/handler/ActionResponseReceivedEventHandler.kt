package bridge.workflow.handler

import bridge.Bridge.StatusType
import bridge.workflow.NotifyAgentCommand
import bridge.workflow.TransitionCommand
import bridge.workflow.UpdateActionStatusCommand
import bridge.workflow.WorkflowContext
import bridge.workflow.WorkflowDecision
import bridge.workflow.WorkflowEventType
import bridge.workflow.WorkflowState
import bridge.workflow.WorkflowStep
import bridge.workflow.events.ActionResponseReceivedEvent
import org.springframework.stereotype.Component

@Component
class ActionResponseReceivedEventHandler :
    AbstractWorkflowEventHandler<ActionResponseReceivedEvent>() {

    override val eventType = WorkflowEventType.ACTION_RESPONSE_RECEIVED

    override fun handle(
        context: WorkflowContext,
        event: ActionResponseReceivedEvent
    ): WorkflowDecision {

        return when (event.responseStatus.uppercase()) {

            "APPROVED",
            "COMPLETED",
            "SUCCESS" -> WorkflowDecision(

                commands = listOf(

                    TransitionCommand(
                        workflowId = event.workflowId,
                        nextState = WorkflowState.COMPLETED,
                        nextStep = WorkflowStep.NOTIFY_AGENT
                    ),

                    UpdateActionStatusCommand(
                        requestId = event.requestId,
                        status = StatusType.COMPLETED,
                        resultData = event.resultData
                    ),

                    NotifyAgentCommand(
                        requestId = event.requestId,
                        message = "Action completed successfully"
                    )

                )
            )

            "REJECTED" -> WorkflowDecision(

                commands = listOf(

                    TransitionCommand(
                        workflowId = event.workflowId,
                        nextState = WorkflowState.FAILED,
                        nextStep = WorkflowStep.NOTIFY_AGENT
                    ),

                    UpdateActionStatusCommand(
                        requestId = event.requestId,
                        status = StatusType.REJECTED,
                        resultData = event.resultData
                    ),

                    NotifyAgentCommand(
                        requestId = event.requestId,
                        message = "Action rejected by Vault"
                    )

                )
            )

            else -> WorkflowDecision(

                commands = listOf(

                    TransitionCommand(
                        workflowId = event.workflowId,
                        nextState = WorkflowState.FAILED,
                        nextStep = WorkflowStep.NOTIFY_AGENT
                    ),

                    UpdateActionStatusCommand(
                        requestId = event.requestId,
                        status = StatusType.FAILED,
                        resultData = event.resultData
                            ?: "Unhandled Vault status: ${event.responseStatus}"
                    ),

                    NotifyAgentCommand(
                        requestId = event.requestId,
                        message = "Action failed"
                    )

                )
            )
        }
    }
}
