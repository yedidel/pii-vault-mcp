package bridge.workflow.publisher

import bridge.workflow.events.WorkflowEvent
import com.fasterxml.jackson.databind.ObjectMapper
import org.springframework.kafka.core.KafkaTemplate
import org.springframework.stereotype.Service

/**
 * Kafka implementation of WorkflowEventPublisher.
 *
 * Responsible only for serializing and publishing workflow events.
 */
@Service
class KafkaWorkflowEventPublisher(
    private val kafkaTemplate: KafkaTemplate<String, String>,
    private val objectMapper: ObjectMapper
) : WorkflowEventPublisher {

    companion object {
        private const val TOPIC = "workflow-events"
    }

    override fun publish(event: WorkflowEvent) {

        val payload = objectMapper.writeValueAsString(event)

        kafkaTemplate
            .send(
                TOPIC,
                event.workflowId,
                payload
            )
            .whenComplete { result, exception ->

                if (exception == null) {

                    println(
                        """
                        Workflow event published

                        Event : ${event.eventType}
                        Workflow : ${event.workflowId}
                        Offset : ${result.recordMetadata.offset()}
                        """.trimIndent()
                    )

                } else {

                    println(
                        """
                        Failed publishing workflow event

                        Event : ${event.eventType}

                        Error : ${exception.message}
                        """.trimIndent()
                    )

                }

            }

    }
}