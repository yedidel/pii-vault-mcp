package bridge.workflow.state
import bridge.workflow.WorkflowEventType
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

    /**
     * Returns whether the workflow should process the incoming event.
     *
     * This method is also used as a lightweight idempotency mechanism.
     * If the workflow has already advanced beyond the stage expected
     * for this event, the event is ignored.
     */
    fun shouldProcessEvent(
        currentState: WorkflowState,
        eventType: WorkflowEventType
    ): Boolean {

        return when (eventType) {

            WorkflowEventType.ACTION_CREATED ->
                currentState == WorkflowState.RECEIVED

            WorkflowEventType.GUARDIAN_APPROVED,
            WorkflowEventType.GUARDIAN_REJECTED ->
                currentState == WorkflowState.WAITING_FOR_GUARDIAN

            WorkflowEventType.ACTION_RESPONSE_RECEIVED ->
                currentState == WorkflowState.WAITING_FOR_VAULT_RESPONSE

            WorkflowEventType.WORKFLOW_COMPLETED,
            WorkflowEventType.WORKFLOW_FAILED ->
                currentState == WorkflowState.IN_PROGRESS
        }
    }
}