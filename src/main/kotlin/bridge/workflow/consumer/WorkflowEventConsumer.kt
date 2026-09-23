package bridge.workflow.consumer

import bridge.workflow.WorkflowEngine
import bridge.workflow.WorkflowEventMapper
import org.slf4j.LoggerFactory
import org.springframework.kafka.annotation.KafkaListener
import org.springframework.stereotype.Component

/**
 * Consumes workflow events from Kafka and forwards them to the workflow engine.
 *
 * Malformed or unknown payloads are logged and skipped so they cannot
 * retry indefinitely on the listener error handler.
 */
@Component
class WorkflowEventConsumer(

    private val workflowEventMapper: WorkflowEventMapper,

    private val workflowEngine: WorkflowEngine

) {

    private val logger = LoggerFactory.getLogger(javaClass)

    @KafkaListener(
        topics = ["workflow-events"],
        groupId = "workflow-engine",
        containerFactory = "kafkaListenerContainerFactory"
    )
    fun consume(message: String) {
        try {
            val event = workflowEventMapper.fromJson(message)
            workflowEngine.process(event)
        } catch (error: Exception) {
            logger.error(
                "Ignoring unprocessable workflow-events payload: {}",
                error.message,
                error,
            )
        }
    }
}
