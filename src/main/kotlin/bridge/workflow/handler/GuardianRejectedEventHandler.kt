package bridge.workflow.handler
import bridge.workflow.PublishEventCommand
import bridge.workflow.TransitionCommand
import bridge.workflow.WorkflowContext
import bridge.workflow.WorkflowDecision
import bridge.workflow.WorkflowEventType
import bridge.workflow.WorkflowState
import bridge.workflow.WorkflowStep
import bridge.workflow.events.GuardianRejectedEvent
import bridge.workflow.events.WorkflowFailedEvent
import org.springframework.stereotype.Component

/**
 * Handles GuardianRejectedEvent.
 *
 * The workflow is terminated because the Guardian rejected the agent.
 */
@Component
class GuardianRejectedEventHandler :
    AbstractWorkflowEventHandler<GuardianRejectedEvent>() {

    override val eventType = WorkflowEventType.GUARDIAN_REJECTED

    override fun handle(
        context: WorkflowContext,
        event: GuardianRejectedEvent
    ): WorkflowDecision {

        return WorkflowDecision(
            commands = listOf(

                TransitionCommand(
                    workflowId = event.workflowId,
                    nextState = WorkflowState.FAILED,
                    nextStep = WorkflowStep.FINISHED
                ),

                PublishEventCommand(
                    WorkflowFailedEvent(
                        workflowId = event.workflowId,
                        requestId = event.requestId,
                        context = event.context,
                        failureReason = event.reason
                    )
                )

            )
        )
    }
}