package connectors.thread

import continuation.ConnectorType
import connectors.api.ContinuationConnector
import continuation.ContinuationRequest
import org.slf4j.LoggerFactory
import org.springframework.stereotype.Component

@Component
class ThreadContinuation : ContinuationConnector {

    private val logger =
        LoggerFactory.getLogger(javaClass)

    override val type =
        ConnectorType.THREAD

    override fun continueWorkflow(
        request: ContinuationRequest,
    ) {

        logger.info(
            "thread continuation requested. requestId={}",
            request.requestId,
        )

        // todo:
        // resume the existing conversation thread
    }
}