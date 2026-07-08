package bridge.workflow
import bridge.model.WorkflowEntity
import bridge.repository.WorkflowRepository
import bridge.workflow.events.ActionContext
import bridge.workflow.events.ActionCreatedEvent
import bridge.workflow.publisher.WorkflowEventPublisher
import org.springframework.stereotype.Service
import java.util.UUID
import com.fasterxml.jackson.databind.ObjectMapper


/**
 * Initializes workflows and triggers the workflow engine.
 *
 * Responsibility:
 * - Create a Workflow entity for a new action
 * - Publish ActionCreatedEvent to Kafka so the workflow engine can start processing
 */
@Service
class WorkflowInitializationService(

    private val workflowRepository: WorkflowRepository,
    private val workflowEventPublisher: WorkflowEventPublisher,
    private val objectMapper: ObjectMapper

) {

    /**
     * Create a workflow for an incoming action and publish the initial event.
     *
     * @param requestId The action request ID
     * @param agentId The agent ID
     * @param userInstallId The user installation ID
     * @param actionType The action type
     * @param platform The platform (e.g., "claude", "openai")
     * @param sessionId The agent session ID
     * @param parameters The action parameters
     * @return The created WorkflowEntity
     */
    fun initializeWorkflow(
        requestId: String,
        agentId: String,
        userInstallId: String,
        actionType: String,
        platform: String,
        sessionId: String,
        parameters: Map<String, String>
    ): WorkflowEntity {
        // Build action context
        val actionContext = ActionContext(
            agentId = agentId,
            userInstallId = userInstallId,
            actionType = actionType,
            platform = platform,
            sessionId = sessionId,
            parameters = parameters
        )

        val workflowId = UUID.randomUUID().toString()
        val contextJson = objectMapper.writeValueAsString(actionContext)
        // Create the workflow entity
        val workflow = WorkflowEntity(
            workflowId = workflowId,
            requestId = requestId,
            platform = platform,
            agentSessionId = sessionId,
            currentState = WorkflowState.RECEIVED,
            currentStep = WorkflowStep.ACTION_RECEIVED,
            contextJson = contextJson
        )

        val savedWorkflow = workflowRepository.save(workflow)

        // Publish ActionCreatedEvent to Kafka
        val event = ActionCreatedEvent(
            workflowId = workflowId,
            requestId = requestId,
            context = actionContext
        )

        workflowEventPublisher.publish(event)

        println("--- [WORKFLOW] Workflow initialized: $workflowId for request: $requestId ---")

        return savedWorkflow
    }
}

