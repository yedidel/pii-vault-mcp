package bridge.workflow.handler

import bridge.workflow.NotifyAgentCommand
import bridge.workflow.PublishEventCommand
import bridge.workflow.WorkflowContext
import bridge.workflow.WorkflowState
import bridge.workflow.WorkflowStep
import bridge.workflow.events.ActionContext
import bridge.workflow.events.ActionResponseReceivedEvent
import bridge.workflow.events.GuardianRejectedEvent
import continuation.ConnectorType
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test

class TerminalWorkflowDecisionTest {

    private val actionContext = ActionContext(
        agentId = "agent-123",
        userInstallId = "install-1",
        actionType = "PAYMENT",
        connectorType = ConnectorType.WEBHOOK,
        connectorContext = "http://127.0.0.1:8000/webhook/bridge",
        parameters = mapOf("amount" to "100", "currency" to "ILS"),
    )

    private val workflowContext = WorkflowContext(
        workflowId = "wf-1",
        requestId = "req-1",
        actionContext = actionContext,
        currentState = WorkflowState.WAITING_FOR_VAULT_RESPONSE,
        currentStep = WorkflowStep.REQUEST_VAULT_EVALUATION,
    )

    @Test
    fun waitForVaultResponseIsNotAWorkflowStep() {
        assertTrue(WorkflowStep.entries.none { it.name == "WAIT_FOR_VAULT_RESPONSE" })
    }

    @Test
    fun vaultApprovedNotifiesExactlyOnceAndDoesNotPublishLegacyEvents() {
        val event = ActionResponseReceivedEvent(
            workflowId = "wf-1",
            requestId = "req-1",
            responseStatus = "APPROVED",
            resultData = "ok",
            context = actionContext,
        )
        val decision = ActionResponseReceivedEventHandler().handle(workflowContext, event)
        assertEquals(1, decision.commands.filterIsInstance<NotifyAgentCommand>().size)
        assertTrue(decision.commands.none { it is PublishEventCommand })
    }

    @Test
    fun guardianRejectedNotifiesExactlyOnceAndDoesNotPublishLegacyEvents() {
        val event = GuardianRejectedEvent(
            workflowId = "wf-1",
            requestId = "req-1",
            context = actionContext,
            reason = "Agent not verified",
        )
        val decision = GuardianRejectedEventHandler().handle(workflowContext, event)
        assertEquals(1, decision.commands.filterIsInstance<NotifyAgentCommand>().size)
        assertTrue(decision.commands.none { it is PublishEventCommand })
    }
}
