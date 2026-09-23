package bridge.workflow

/**
 * Identifies every event that can be processed by the workflow engine.
 */
enum class WorkflowEventType {

    /**
     * A new workflow has been created.
     */
    ACTION_CREATED,

    /**
     * The Guardian approved the requesting agent.
     */
    GUARDIAN_APPROVED,

    /**
     * The Guardian rejected the requesting agent.
     */
    GUARDIAN_REJECTED,

    // Vault internals are intentionally not modeled by the Bridge workflow.
    // The Vault contract returns a single ActionResponse. Use
    // ACTION_RESPONSE_RECEIVED to represent that protocol-level response.
    ACTION_RESPONSE_RECEIVED,

    /**
     * Legacy bus type. Not published by the active workflow.
     * Kept so leftover Kafka messages can be deserialized and ignored.
     */
    WORKFLOW_COMPLETED,

    /**
     * Legacy bus type. Not published by the active workflow.
     * Kept so leftover Kafka messages can be deserialized and ignored.
     */
    WORKFLOW_FAILED
}