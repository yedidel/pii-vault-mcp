package bridge

import com.fasterxml.jackson.databind.ObjectMapper
import org.springframework.kafka.core.KafkaTemplate
import org.springframework.stereotype.Service

@Service
class ActionProducer(
    private val kafkaTemplate: KafkaTemplate<String, String>,
    private val objectMapper: ObjectMapper // Using Jackson's ObjectMapper to convert to JSON
) {

    /**
     * Sends a detailed JSON message to the Kafka 'agent-actions' topic.
     * Includes all metadata and parameters received from the gRPC request.
     */
    fun sendActionToKafka(request: Bridge.ActionRequest) {
        val topic = "agent-actions"

        // 1. Create a structured Map with all the data you want to send
        val messagePayload = mapOf(
            "timestamp" to System.currentTimeMillis(),
            "agentId" to request.agentId,
            "userInstallId" to request.userInstallId,
            "actionType" to request.actionType,
            "parameters" to request.parametersMap // This includes amount, currency, etc.
        )

        // 2. Convert the Map to a JSON string
        // This makes the data much more relevant and readable in Kafka-UI
        val jsonMessage = objectMapper.writeValueAsString(messagePayload)

        // 3. Async send to Kafka with the agentId as the message Key
        kafkaTemplate.send(topic, request.agentId, jsonMessage).whenComplete { result, ex ->
            if (ex == null) {
                // Log successful delivery to the console
                println("✅ Kafka: Message delivered to offset ${result.recordMetadata.offset()}")
            } else {
                // Log failure for troubleshooting
                System.err.println("❌ Kafka Error: ${ex.message}")
            }
        }
    }
}