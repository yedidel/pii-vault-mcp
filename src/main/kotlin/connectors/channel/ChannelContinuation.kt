package connectors.channel

import continuation.ConnectorType
import continuation.ContinuationRequest
import connectors.api.ContinuationConnector
import org.slf4j.LoggerFactory
import org.springframework.stereotype.Component

/**
 * Generic HTTP continuation: POST JSON to [ContinuationRequest.connectorContext].
 * This is not the Claude Channel / Adapter MCP wake path.
 */
@Component
class ChannelContinuation(
    private val transport: HttpChannelTransport,
) : ContinuationConnector {

    private val logger =
        LoggerFactory.getLogger(javaClass)

    override val type =
        ConnectorType.CHANNEL

    override fun continueWorkflow(
        request: ContinuationRequest,
    ) {

        logger.info(
            "Channel continuation. requestId={}",
            request.requestId,
        )

        transport.sendEvent(
            endpoint = request.connectorContext,
            notification = NotifyAgent(
                workflowId = request.workflowId,
                requestId = request.requestId,
                status = request.status,
                message = request.message,
            ),
        )
    }
}