package bridge.workflow

import bridge.repository.ActionRepository
import bridge.repository.WorkflowRepository
import com.fasterxml.jackson.databind.ObjectMapper
import org.springframework.stereotype.Component

/**
 * Loads the runtime context required by the workflow engine.
 */
@Component
class WorkflowContextLoader(

    private val workflowRepository: WorkflowRepository,

    private val actionRepository: ActionRepository,

    private val objectMapper: ObjectMapper

) {

    fun load(workflowId: String): WorkflowContext {

        val workflow = workflowRepository
            .findById(workflowId)
            .orElseThrow {
                IllegalArgumentException("Workflow $workflowId not found.")
            }

        val action = actionRepository
            .findById(workflow.requestId)
            .orElseThrow {
                IllegalArgumentException("Action ${workflow.requestId} not found.")
            }

        val parameters =
            if (action.parametersJson == null)
                emptyMap()
            else
                objectMapper.readValue(
                    action.parametersJson,
                    Map::class.java
                ) as Map<String, String>

        val actionContext = bridge.workflow.events.ActionContext(
            agentId = action.agentId,
            userInstallId = action.userInstallId,
            actionType = action.actionType,
            platform = workflow.platform,
            sessionId = workflow.agentSessionId,
            parameters = parameters
        )

        return WorkflowContext(
            workflowId = workflow.workflowId,
            requestId = workflow.requestId,
            actionContext = actionContext,
            currentState = workflow.currentState,
            currentStep = workflow.currentStep

        )

    }

}