package bridge

import org.springframework.kafka.annotation.KafkaListener
import org.springframework.stereotype.Service

@Service
class ActionConsumer {

    /**
     * This method listens to the Kafka topic and prints received messages.
     * It acts as the 'Worker' that processes the tasks asynchronously.
     */
    @KafkaListener(topics = ["agent-actions"], groupId = "bridge-group")
    fun consume(message: String) {
        println("==========================================")
        println("KAFKA CONSUMER: Received new action task!")
        println("Message Content: $message")
        println("==========================================")

        // In the future, this is where we will call the Bank API
        // or update the DB status to 'COMPLETED'.
    }
}