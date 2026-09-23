package connectors.channel

import org.springframework.http.MediaType
import org.springframework.stereotype.Service
import org.springframework.web.client.RestClient

@Service
class ChannelTransport {

    private val client =
        RestClient.create()

    fun sendEvent(
        endpoint: String,
        notification: NotifyAgent,
    ) {

        client.post()
            .uri(endpoint)
            .contentType(MediaType.APPLICATION_JSON)
            .body(notification)
            .retrieve()
            .toBodilessEntity()
    }
}