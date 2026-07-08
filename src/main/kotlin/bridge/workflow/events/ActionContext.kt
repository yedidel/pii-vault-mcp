package bridge.workflow.events

/**
 * Immutable context describing the action that initiated the workflow.
 *
 * This object is shared by all workflow events.
 */
data class ActionContext(

    /**
     * Agent that initiated the workflow.
     */
    val agentId: String,

    /**
     * User installation identifier.
     */
    val userInstallId: String,

    /**
     * Requested action type.
     */
    val actionType: String,

    /**
     * Platform from which the action originated.
     */
    val platform: String,

    /**
     * External agent session identifier.
     */
    val sessionId: String,

    /**
     * Immutable action parameters.
     */
    val parameters: Map<String, String>
)