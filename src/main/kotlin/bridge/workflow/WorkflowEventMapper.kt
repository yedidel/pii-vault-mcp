package bridge.workflow

import bridge.workflow.events.ActionCreatedEvent
import bridge.workflow.events.GuardianApprovedEvent
import bridge.workflow.events.GuardianRejectedEvent
import bridge.workflow.events.WorkflowCompletedEvent
import bridge.workflow.events.WorkflowEvent
import bridge.workflow.events.WorkflowFailedEvent
import bridge.workflow.events.ActionResponseReceivedEvent
import com.fasterxml.jackson.databind.JsonNode
import com.fasterxml.jackson.databind.ObjectMapper
import org.springframework.stereotype.Component

/**
 * Maps Kafka JSON messages into workflow events.
 *
 * This class centralizes event deserialization and keeps
 * WorkflowEventConsumer free from mapping logic.
 */
@Component
class WorkflowEventMapper(
    private val objectMapper: ObjectMapper
) {

    /**
     * Deserialize a Kafka message into a WorkflowEvent.
     */
    fun fromJson(message: String): WorkflowEvent {

        val node: JsonNode = objectMapper.readTree(message)

        val eventType = WorkflowEventType.valueOf(
            node["eventType"].asText()
        )

        return when (eventType) {

            WorkflowEventType.ACTION_CREATED ->
                objectMapper.treeToValue(
                    node,
                    ActionCreatedEvent::class.java
                )

            WorkflowEventType.GUARDIAN_APPROVED ->
                objectMapper.treeToValue(
                    node,
                    GuardianApprovedEvent::class.java
                )

            WorkflowEventType.GUARDIAN_REJECTED ->
                objectMapper.treeToValue(
                    node,
                    GuardianRejectedEvent::class.java
                )

            WorkflowEventType.ACTION_RESPONSE_RECEIVED ->
                objectMapper.treeToValue(
                    node,
                    ActionResponseReceivedEvent::class.java
                )

            WorkflowEventType.WORKFLOW_COMPLETED ->
                objectMapper.treeToValue(
                    node,
                    WorkflowCompletedEvent::class.java
                )

            WorkflowEventType.WORKFLOW_FAILED ->
                objectMapper.treeToValue(
                    node,
                    WorkflowFailedEvent::class.java
                )
        }
    }
}