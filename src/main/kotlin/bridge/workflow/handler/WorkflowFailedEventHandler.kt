package bridge.workflow.handler
import bridge.workflow.NotifyAgentCommand
import bridge.workflow.WorkflowContext
import bridge.workflow.WorkflowDecision
import bridge.workflow.WorkflowEventType
import bridge.workflow.events.WorkflowFailedEvent
import org.springframework.stereotype.Component

@Component
class WorkflowFailedEventHandler :
    AbstractWorkflowEventHandler<WorkflowFailedEvent>() {

    override val eventType =
        WorkflowEventType.WORKFLOW_FAILED

    override fun handle(
        context: WorkflowContext,
        event: WorkflowFailedEvent
    ): WorkflowDecision {

        return WorkflowDecision(

            commands = listOf(

                NotifyAgentCommand(
                    requestId = event.requestId,
                    message = event.failureReason
                )

            )

        )

    }

}