package bridge.workflow

import bridge.repository.WorkflowRepository
import bridge.workflow.events.ActionContext
import com.fasterxml.jackson.databind.ObjectMapper
import org.springframework.stereotype.Component

@Component
class WorkflowContextLoader(

    private val workflowRepository: WorkflowRepository,

    private val objectMapper: ObjectMapper,

    ) {

    fun load(workflowId: String): WorkflowContext {

        val workflow = workflowRepository
            .findById(workflowId)
            .orElseThrow {
                IllegalArgumentException("Workflow $workflowId not found.")
            }

        val actionContext =
            objectMapper.readValue(
                workflow.contextJson,
                ActionContext::class.java
            )

        return WorkflowContext(
            workflowId = workflow.workflowId,
            requestId = workflow.requestId,
            actionContext = actionContext,
            currentState = workflow.currentState,
            currentStep = workflow.currentStep,
        )
    }
}