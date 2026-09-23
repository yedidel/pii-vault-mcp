package bridge.workflow

import bridge.model.WorkflowEntity
import bridge.repository.WorkflowRepository
import bridge.workflow.events.ActionContext
import bridge.workflow.events.ActionCreatedEvent
import bridge.workflow.publisher.WorkflowEventPublisher
import com.fasterxml.jackson.databind.ObjectMapper
import continuation.ConnectorType
import org.springframework.stereotype.Service
import java.util.UUID

/**
 * Initializes workflows and triggers the workflow engine.
 *
 * Responsibility:
 * - Create a workflow entity for a new action
 * - Publish ActionCreatedEvent so the workflow engine can start processing
 */
@Service
class WorkflowInitializationService(

    private val workflowRepository: WorkflowRepository,

    private val workflowEventPublisher: WorkflowEventPublisher,

    private val objectMapper: ObjectMapper,

    ) {

    /**
     * Create a workflow for an incoming action.
     */
    fun initializeWorkflow(

        requestId: String,

        agentId: String,

        userInstallId: String,

        actionType: String,

        connectorType: ConnectorType,

        connectorContext: String,

        parameters: Map<String, String>,

        ): WorkflowEntity {

        val actionContext = ActionContext(
            agentId = agentId,
            userInstallId = userInstallId,
            actionType = actionType,
            connectorType = connectorType,
            connectorContext = connectorContext,
            parameters = parameters,
        )

        val workflowId =
            UUID.randomUUID().toString()

        val contextJson =
            objectMapper.writeValueAsString(actionContext)

        val workflow = WorkflowEntity(
            workflowId = workflowId,
            requestId = requestId,
            connectorType = connectorType,
            connectorContext = connectorContext,
            currentState = WorkflowState.RECEIVED,
            currentStep = WorkflowStep.ACTION_RECEIVED,
            contextJson = contextJson,
        )

        val savedWorkflow =
            workflowRepository.save(workflow)

        workflowEventPublisher.publish(
            ActionCreatedEvent(
                workflowId = workflowId,
                requestId = requestId,
                context = actionContext,
            )
        )

        println(
            "--- [workflow] initialized workflow=$workflowId request=$requestId ---"
        )

        return savedWorkflow
    }
}