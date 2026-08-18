package connectors.webhook

import org.springframework.http.MediaType
import org.springframework.http.client.JdkClientHttpRequestFactory
import org.springframework.stereotype.Service
import org.springframework.web.client.RestClient
import java.net.http.HttpClient

@Service
class WebhookTransport {

    private val client = RestClient.builder()
        .requestFactory(
            JdkClientHttpRequestFactory(
                HttpClient.newBuilder()
                    .version(HttpClient.Version.HTTP_1_1)
                    .build()
            )
        )
        .build()
    fun send(
        callbackUrl: String,
        notification: WebhookNotification,
    ) {

        client.post()
            .uri(callbackUrl)
            .contentType(MediaType.APPLICATION_JSON)
            .body(notification)
            .retrieve()
            .toBodilessEntity()
    }
}