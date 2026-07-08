package bridge.workflow.consumer

import bridge.workflow.WorkflowEngine
import bridge.workflow.WorkflowEventMapper
import org.springframework.kafka.annotation.KafkaListener
import org.springframework.stereotype.Component

/**
 * Consumes workflow events from Kafka and forwards them to the workflow engine.
 *
 * This class contains no business logic.
 * Its only responsibility is adapting Kafka messages into WorkflowEvent
 * instances and delegating them to the engine.
 */
@Component
class WorkflowEventConsumer(

    private val workflowEventMapper: WorkflowEventMapper,

    private val workflowEngine: WorkflowEngine

) {

    @KafkaListener(
        topics = ["workflow-events"],
        groupId = "workflow-engine",
        containerFactory = "kafkaListenerContainerFactory"
    )
    fun consume(message: String) {

        val event = workflowEventMapper.fromJson(message)

        workflowEngine.process(event)
    }
}