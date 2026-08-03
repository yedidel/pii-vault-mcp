package continuation

data class ContinuationRequest(

    val workflowId: String,

    val requestId: String,

    /**
     * opaque data used by the connector
     */
    val connectorContext: String,

    val status: String,

    val message: String,
)