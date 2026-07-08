package bridge.workflow.handler

import bridge.workflow.*
import bridge.workflow.events.ActionCreatedEvent
import org.springframework.stereotype.Component

/**
 * Handles the initial ActionCreatedEvent.
 * This is the entry point of every workflow.
 */
@Component
class ActionCreatedEventHandler :
    AbstractWorkflowEventHandler<ActionCreatedEvent>() {

    override val eventType = WorkflowEventType.ACTION_CREATED

    override fun handle(
        context: WorkflowContext,
        event: ActionCreatedEvent
    ): WorkflowDecision {

        return WorkflowDecision(

            commands = listOf(

                TransitionCommand(

                    workflowId = event.workflowId,

                    nextState = WorkflowState.WAITING_FOR_GUARDIAN,

                    nextStep = WorkflowStep.VERIFY_AGENT

                ),

                VerifyAgentCommand(

                    workflowId = event.workflowId,

                    requestId = event.requestId,

                    context = event.context

                )

            )

        )
    }
}