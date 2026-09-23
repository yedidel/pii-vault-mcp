package connectors.webhook

import connectors.api.ContinuationConnector
import continuation.ConnectorType
import continuation.ContinuationRequest
import org.springframework.stereotype.Component

@Component
class WebhookContinuation(
    private val transport: WebhookTransport,
) : ContinuationConnector {

    override val type =
        ConnectorType.WEBHOOK

    override fun continueWorkflow(
        request: ContinuationRequest,
    ) {

        transport.send(
            callbackUrl = request.connectorContext,
            notification = WebhookNotification(
                workflowId = request.workflowId,
                requestId = request.requestId,
                status = request.status,
                message = request.message,
            ),
        )
    }
}