package connectors.thread

import continuation.ConnectorType
import connectors.api.ContinuationConnector
import continuation.ContinuationRequest
import org.slf4j.LoggerFactory
import org.springframework.stereotype.Component

/**
 * Prototype stub. THREAD continuation is not implemented.
 */
@Component
class ThreadContinuation : ContinuationConnector {

    private val logger =
        LoggerFactory.getLogger(javaClass)

    override val type =
        ConnectorType.THREAD

    override fun continueWorkflow(
        request: ContinuationRequest,
    ) {
        logger.warn(
            "THREAD connector is not implemented. requestId={}",
            request.requestId,
        )
    }
}
