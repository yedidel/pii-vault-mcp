package bridge.workflow.handler

import bridge.Bridge.StatusType
import bridge.workflow.*
import bridge.workflow.events.ActionResponseReceivedEvent
import bridge.workflow.events.WorkflowCompletedEvent
import bridge.workflow.events.WorkflowFailedEvent
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

                    PublishEventCommand(
                        WorkflowCompletedEvent(
                            workflowId = event.workflowId,
                            requestId = event.requestId,
                            context = event.context
                        )
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

                    PublishEventCommand(
                        WorkflowFailedEvent(
                            workflowId = event.workflowId,
                            requestId = event.requestId,
                            context = event.context,
                            failureReason = event.resultData ?: "Vault rejected action"
                        )
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

                    PublishEventCommand(
                        WorkflowFailedEvent(
                            workflowId = event.workflowId,
                            requestId = event.requestId,
                            context = event.context,
                            failureReason = "Unhandled Vault status: ${event.responseStatus}"
                        )
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