package bridge
import org.springframework.kafka.annotation.KafkaListener
import org.springframework.stereotype.Service
import com.fasterxml.jackson.module.kotlin.jacksonObjectMapper
import com.fasterxml.jackson.module.kotlin.readValue
import bridge.Bridge.StatusType

@Service
class ActionConsumer(private val actionService: ActionService) {

    /**
     * This method listens to the Kafka topic and prints received messages.
     * It acts as the Worker that processes the tasks asynchronously.
     */
    @KafkaListener(topics = ["agent-actions"], groupId = "bridge-group")
    fun consume(message: String) {
        println("===================================")
        println("KAFKA CONSUMER RECEIVED MESSAGE")
        println(message)
        println("===================================")
        val objectMapper = jacksonObjectMapper()

        //convert from string to kotlin object
        val payload = objectMapper.readTree(message)

        val requestId = payload["requestId"].asText()

        //start processing the action - update status
        actionService.updateStatus(
            requestId,
            StatusType.IN_PROGRESS
        )
        //to mock processing
        Thread.sleep(5000)

        //end the action
        actionService.updateStatus(
            requestId,
            StatusType.COMPLETED
        )
        // In the future, this is where we will call the Bank API
        // or update the DB status to 'COMPLETED'.
    }
}