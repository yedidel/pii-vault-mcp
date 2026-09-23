package bridge.workflow.events

import continuation.ConnectorType

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
     * Connector used to continue the workflow.
     */
    val connectorType: ConnectorType,

    /**
     * Opaque context understood only by the connector
     * (session id, thread id, webhook url, etc.).
     */
    val connectorContext: String,

    /**
     * Immutable action parameters.
     */
    val parameters: Map<String, String>,
)