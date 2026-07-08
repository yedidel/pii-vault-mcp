package bridge.workflow

/**
 * Internal workflow state managed by the Bridge.
 *
 * This is not the same as Bridge.StatusType.
 * StatusType is exposed to agents, while WorkflowState is used only
 * inside the workflow engine.
 */
enum class WorkflowState {
    RECEIVED,
    WAITING_FOR_GUARDIAN,
    WAITING_FOR_VAULT_RESPONSE,
    IN_PROGRESS,
    COMPLETED,
    FAILED
}