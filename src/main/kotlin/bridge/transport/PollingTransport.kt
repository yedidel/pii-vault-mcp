package bridge.transport

import org.slf4j.LoggerFactory
import org.springframework.stereotype.Component

@Component
class PollingTransport : AgentTransport {

    private val logger = LoggerFactory.getLogger(javaClass)

    override val type = TransportType.POLLING

    override fun send(
        requestId: String,
        message: String
    ) {

        logger.info(
            "Polling transport: nothing to push. Agent will poll. requestId={}",
            requestId
        )
    }
}