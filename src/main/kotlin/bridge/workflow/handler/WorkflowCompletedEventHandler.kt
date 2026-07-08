package bridge.workflow.handler
import bridge.workflow.NotifyAgentCommand
import bridge.workflow.TransitionCommand
import bridge.workflow.WorkflowContext
import bridge.workflow.WorkflowDecision
import bridge.workflow.WorkflowEventType
import bridge.workflow.WorkflowState
import bridge.workflow.WorkflowStep
import bridge.workflow.events.WorkflowCompletedEvent
import org.springframework.stereotype.Component

@Component
class WorkflowCompletedEventHandler :
    AbstractWorkflowEventHandler<WorkflowCompletedEvent>() {

    override val eventType =
        WorkflowEventType.WORKFLOW_COMPLETED

    override fun handle(
        context: WorkflowContext,
        event: WorkflowCompletedEvent
    ): WorkflowDecision {

        return WorkflowDecision(

            commands = listOf(

                TransitionCommand(
                    workflowId = event.workflowId,
                    nextState = WorkflowState.COMPLETED,
                    nextStep = WorkflowStep.FINISHED
                ),

                NotifyAgentCommand(
                    requestId = event.requestId,
                    message = "Workflow completed successfully."
                )

            )

        )

    }

}