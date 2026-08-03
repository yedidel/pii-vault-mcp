package connectors.channel

import org.slf4j.LoggerFactory
import org.springframework.http.MediaType
import org.springframework.stereotype.Service
import org.springframework.web.client.RestClient

@Service
class HttpChannelTransport {

    private val logger =
        LoggerFactory.getLogger(javaClass)

    private val client =
        RestClient.create()

    fun sendEvent(
        endpoint: String,
        notification: NotifyAgent,
    ) {

        logger.info(
            "Sending continuation to {}",
            endpoint,
        )

        client.post()
            .uri(endpoint)
            .contentType(MediaType.APPLICATION_JSON)
            .body(notification)
            .retrieve()
            .toBodilessEntity()

        logger.info(
            "Continuation sent successfully."
        )
    }
}