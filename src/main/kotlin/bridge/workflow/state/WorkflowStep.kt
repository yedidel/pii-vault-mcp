package bridge.workflow

/**
 * Represents the current execution step performed by the workflow engine.
 */
enum class WorkflowStep {
    ACTION_RECEIVED,
    VERIFY_AGENT,
    REQUEST_VAULT_EVALUATION,
    WAIT_FOR_VAULT_RESPONSE,
    NOTIFY_AGENT,
    FINISHED
}