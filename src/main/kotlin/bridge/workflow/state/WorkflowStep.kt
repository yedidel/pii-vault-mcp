package bridge.workflow

/**
 * Represents the current execution step performed by the workflow engine.
 */
enum class WorkflowStep {
    ACTION_RECEIVED,
    VERIFY_AGENT,
    /** Command issued when entering WAITING_FOR_VAULT_RESPONSE. */
    REQUEST_VAULT_EVALUATION,
    NOTIFY_AGENT,
    FINISHED
}