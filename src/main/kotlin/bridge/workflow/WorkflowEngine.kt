package bridge.workflow

import bridge.workflow.events.WorkflowEvent
import bridge.workflow.handler.AbstractWorkflowEventHandler
import bridge.workflow.state.WorkflowTransitionValidator
import org.springframework.beans.factory.ObjectProvider
import org.springframework.stereotype.Component

@Component
class WorkflowEngine(

    private val contextLoader: WorkflowContextLoader,

    private val commandExecutor: WorkflowCommandExecutor,

    private val handlers: ObjectProvider<List<AbstractWorkflowEventHandler<*>>>,

    private val transitionValidator: WorkflowTransitionValidator

) {

    fun process(event: WorkflowEvent) {

        println("--- [WORKFLOW] Processing event type: ${event.eventType} for workflow: ${event.workflowId} ---")

        val context = contextLoader.load(event.workflowId)

        if (!transitionValidator.shouldProcessEvent(context.currentState, event.eventType)) {
            println(
                """
                Ignoring duplicate workflow event
                Workflow : ${event.workflowId}
                Event    : ${event.eventType}
                State    : ${context.currentState}
                """.trimIndent()
            )
            return
        }

        val handler = findHandler(event)
            ?: throw IllegalStateException(
                "No handler registered for event type: ${event.eventType}"
            )

        @Suppress("UNCHECKED_CAST")
        val typedHandler =
            handler as AbstractWorkflowEventHandler<WorkflowEvent>

        val decision = typedHandler.handle(context, event)

        commandExecutor.execute(decision)

        println("--- [WORKFLOW] Event processing completed for workflow: ${event.workflowId} ---")
    }

    /**
     * Resume an unfinished workflow after application restart.
     *
     * Recovery is state-driven, not event-driven.
     * It does not publish fake Kafka events.
     */
    fun resume(workflowId: String) {

        val context = contextLoader.load(workflowId)

        println(
            """
            ----- [WORKFLOW RECOVERY] Resuming workflow -----
            Workflow : ${context.workflowId}
            Request  : ${context.requestId}
            State    : ${context.currentState}
            Step     : ${context.currentStep}
            """.trimIndent()
        )

        val decision =
            when (context.currentState) {

                WorkflowState.RECEIVED ->
                    WorkflowDecision(
                        commands = listOf(
                            TransitionCommand(
                                workflowId = context.workflowId,
                                nextState = WorkflowState.WAITING_FOR_GUARDIAN,
                                nextStep = WorkflowStep.VERIFY_AGENT
                            ),
                            VerifyAgentCommand(
                                workflowId = context.workflowId,
                                requestId = context.requestId,
                                context = context.actionContext
                            )
                        )
                    )

                WorkflowState.WAITING_FOR_GUARDIAN ->
                    WorkflowDecision(
                        commands = listOf(
                            VerifyAgentCommand(
                                workflowId = context.workflowId,
                                requestId = context.requestId,
                                context = context.actionContext
                            )
                        )
                    )

                WorkflowState.WAITING_FOR_VAULT_RESPONSE ->
                    WorkflowDecision(
                        commands = listOf(
                            RequestVaultEvaluationCommand(
                                workflowId = context.workflowId,
                                requestId = context.requestId,
                                amount = context.actionContext.parameters["amount"] ?: "",
                                currency = context.actionContext.parameters["currency"] ?: ""
                            )
                        )
                    )

                WorkflowState.IN_PROGRESS -> {
                    println(
                        "--- [WORKFLOW RECOVERY] Workflow is IN_PROGRESS. No recovery command defined yet for ${context.workflowId} ---"
                    )
                    WorkflowDecision(emptyList())
                }

                WorkflowState.COMPLETED,
                WorkflowState.FAILED ->
                    WorkflowDecision(emptyList())
            }

        commandExecutor.execute(decision)

        println("--- [WORKFLOW RECOVERY] Resume completed for workflow: ${context.workflowId} ---")
    }

    private fun findHandler(
        event: WorkflowEvent
    ): AbstractWorkflowEventHandler<*>? {

        return handlers
            .getIfAvailable()
            ?.find { it.eventType == event.eventType }
    }
}