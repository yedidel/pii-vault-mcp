package connectors.channel

data class NotifyAgent(
    val workflowId: String,
    val requestId: String,
    val status: String,
    val message: String,
)