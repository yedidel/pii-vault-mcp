package connectors.polling

import continuation.ConnectorType
import connectors.api.ContinuationConnector
import continuation.ContinuationRequest
import org.slf4j.LoggerFactory
import org.springframework.stereotype.Component

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
            "polling continuation requested. requestId={}",
            request.requestId,
        )

        // todo:
        // polling agents will fetch workflow updates
    }
}