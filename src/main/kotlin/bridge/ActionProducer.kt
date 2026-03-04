package bridge
import org.springframework.kafka.core.KafkaTemplate
import org.springframework.stereotype.Service

@Service
class ActionProducer(private val kafkaTemplate: KafkaTemplate<String, String>) {

    fun sendActionToKafka(agentId: String, actionType: String) {
        val topic = "agent-actions"
        val message = "Agent $agentId reported: $actionType"

        // שליחה אסינכרונית עם בדיקה אם הצליח
        val future = kafkaTemplate.send(topic, agentId, message)

        future.whenComplete { result, ex ->
            if (ex == null) {
                println("✅ Kafka: Message sent successfully to offset ${result.recordMetadata.offset()}")
            } else {
                System.err.println("❌ Kafka Error: ${ex.message}")
            }
        }
    }
}