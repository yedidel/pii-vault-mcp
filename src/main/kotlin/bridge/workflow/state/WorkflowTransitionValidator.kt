package bridge.workflow.state
import bridge.workflow.WorkflowState
import org.springframework.stereotype.Component

/**
 * Validates legal transitions between workflow states.
 *
 * Every workflow state change must be validated before it is persisted.
 */
@Component
class WorkflowTransitionValidator {

    /**
     * Returns true if the requested transition is allowed.
     */
    fun isValidTransition(
        currentState: WorkflowState,
        nextState: WorkflowState
    ): Boolean {

        return when (currentState) {

            WorkflowState.RECEIVED ->
                nextState == WorkflowState.WAITING_FOR_GUARDIAN

            WorkflowState.WAITING_FOR_GUARDIAN ->
                nextState == WorkflowState.WAITING_FOR_VAULT_RESPONSE ||
                        nextState == WorkflowState.FAILED

            WorkflowState.WAITING_FOR_VAULT_RESPONSE ->
                nextState == WorkflowState.IN_PROGRESS ||
                        nextState == WorkflowState.COMPLETED ||
                        nextState == WorkflowState.FAILED

            WorkflowState.IN_PROGRESS ->
                nextState == WorkflowState.COMPLETED ||
                        nextState == WorkflowState.FAILED

            WorkflowState.COMPLETED,
            WorkflowState.FAILED ->
                false
        }
    }
}