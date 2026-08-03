package connectors.webhook

data class WebhookNotification(
    val workflowId: String,
    val requestId: String,
    val status: String,
    val message: String,
)