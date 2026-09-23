package bridge.workflow.state

import bridge.workflow.WorkflowEventType
import bridge.workflow.WorkflowState
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test

class WorkflowTransitionValidatorTest {

    private val validator = WorkflowTransitionValidator()

    @Test
    fun liveHappyPathTransitionsAreAllowed() {
        assertTrue(
            validator.isValidTransition(
                WorkflowState.RECEIVED,
                WorkflowState.WAITING_FOR_GUARDIAN,
            )
        )
        assertTrue(
            validator.isValidTransition(
                WorkflowState.WAITING_FOR_GUARDIAN,
                WorkflowState.WAITING_FOR_VAULT_RESPONSE,
            )
        )
        assertTrue(
            validator.isValidTransition(
                WorkflowState.WAITING_FOR_VAULT_RESPONSE,
                WorkflowState.COMPLETED,
            )
        )
        assertTrue(
            validator.isValidTransition(
                WorkflowState.WAITING_FOR_VAULT_RESPONSE,
                WorkflowState.FAILED,
            )
        )
        assertFalse(
            WorkflowState.entries.any { it.name == "IN_PROGRESS" }
        )
    }

    @Test
    fun leftoverCompletionEventsAreNeverProcessed() {
        for (state in WorkflowState.entries) {
            assertFalse(
                validator.shouldProcessEvent(state, WorkflowEventType.WORKFLOW_COMPLETED)
            )
            assertFalse(
                validator.shouldProcessEvent(state, WorkflowEventType.WORKFLOW_FAILED)
            )
        }
    }
}
