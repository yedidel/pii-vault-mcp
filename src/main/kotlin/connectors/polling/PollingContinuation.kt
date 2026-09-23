package connectors.polling

import continuation.ConnectorType
import connectors.api.ContinuationConnector
import continuation.ContinuationRequest
import org.slf4j.LoggerFactory
import org.springframework.stereotype.Component

/**
 * Prototype stub. Bridge does not push status for POLLING connectors.
 * Adapter-side PollingWorker is the supported POLLING continuation.
 */
@Component
class PollingContinuation : ContinuationConnector {

    private val logger =
        LoggerFactory.getLogger(javaClass)

    override val type =
        ConnectorType.POLLING

    override fun continueWorkflow(
        request: ContinuationRequest,
    ) {
        logger.info(
            "POLLING connector is unsupported on Bridge; " +
                "Adapter PollingWorker must observe GetActionStatus. requestId={}",
            request.requestId,
        )
    }
}
