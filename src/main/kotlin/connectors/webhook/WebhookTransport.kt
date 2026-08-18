package connectors.webhook

import com.fasterxml.jackson.databind.ObjectMapper
import org.springframework.http.MediaType
import org.springframework.http.client.JdkClientHttpRequestFactory
import org.springframework.stereotype.Service
import org.springframework.web.client.RestClient
import java.net.http.HttpClient

@Service
class WebhookTransport(
    private val objectMapper: ObjectMapper
) {
    private val client = RestClient.builder()
        .requestFactory(
            JdkClientHttpRequestFactory(
                HttpClient.newBuilder()
                    .version(HttpClient.Version.HTTP_1_1)
                    .build()
            )
        )
        .build()

    fun send(callbackUrl: String, notification: WebhookNotification) {
        val bodyJson = objectMapper.writeValueAsString(notification)
        var request = client.post()
            .uri(callbackUrl)
            .contentType(MediaType.APPLICATION_JSON)

        WebhookSignature.secretFromEnv().let { secret ->
            request = request.header(
                WebhookSignature.HEADER_NAME,
                WebhookSignature.sign(bodyJson, secret),
            )
        }

        request
            .body(bodyJson)
            .retrieve()
            .toBodilessEntity()
    }
}