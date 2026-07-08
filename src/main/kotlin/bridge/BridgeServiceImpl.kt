package bridge

import bridge.Bridge.ActionResponse
import bridge.Bridge.StatusResponse
import org.springframework.stereotype.Service
import bridge.workflow.WorkflowInitializationService
import com.fasterxml.jackson.databind.ObjectMapper

/**
 * BridgeServiceImpl
 * * This class serves as the central orchestrator for the PII Vault Ecosystem.
 * It manages the communication between gRPC clients (Agents), the Database,
 * the Guardian (Reputation Service), and the Vault (User Authorization Service).
 */
@Service
class BridgeServiceImpl(
    private val actionService: ActionService,
    private val workflowInitializationService: WorkflowInitializationService,
    private val objectMapper: ObjectMapper
) : BridgeServiceGrpcKt.BridgeServiceCoroutineImplBase() {


    /**
     * Orchestrates the initial action intake.
     * The workflow engine (event-driven) orchestrates the rest.
     *
     * Steps:
     * 1. Validate agent with Guardian
     * 2. Persist action
     * 3. Initialize workflow and publish ActionCreatedEvent
     * 4. Return immediately (workflow engine handles the rest)
     */
    override suspend fun sendAction(request: Bridge.ActionRequest): ActionResponse {
        println("--- [BRIDGE] Processing ${request.actionType} for agent ${request.agentId} ---")

        // STEP 1: Guardian Reputation Check & Action Persistence
        // We consult the Guardian service before proceeding. If the domain is malicious
        // or the agent is unauthorized, handleAction will throw an exception or block the flow.
        val responseEntity = try {
            actionService.handleAction(request)
        } catch (e: Exception) {
            println("--- [BRIDGE] Action rejected by safety protocols: ${e.message} ---")
            return ActionResponse.newBuilder()
                .setStatus(Bridge.StatusType.FAILED)
                .setDescription("Action rejected by bridge safety layer: ${e.message}")
                .build()
        }

        val requestId = responseEntity.requestId

        // STEP 2: Initialize Workflow
        // Create a workflow and publish ActionCreatedEvent.
        // The workflow engine will consume this event and orchestrate the rest.
        val parameters = objectMapper.convertValue(request.parametersMap, Map::class.java) as Map<String, String>

        workflowInitializationService.initializeWorkflow(
            requestId = requestId,
            agentId = request.agentId,
            userInstallId = request.userInstallId,
            actionType = request.actionType,
            platform = request.platform,
            sessionId = request.sessionId,
            parameters = parameters
        )

        // STEP 3: Return initial response to agent
        // The workflow engine now orchestrates the rest asynchronously.
        return ActionResponse.newBuilder()
            .setRequestId(requestId)
            .setStatus(Bridge.StatusType.RECEIVED)
            .setDescription("Action received and workflow initiated. Use GetActionStatus to poll for completion.")
            .build()
    }


    /**
     * Queries the database for the current status of a specific action.
     */
    override suspend fun getActionStatus(request: Bridge.StatusRequest): StatusResponse {
        val action = actionService.getActionById(request.requestId)
        return StatusResponse.newBuilder()
            .setRequestId(action.requestId)
            .setStatus(action.status)
            .build()
    }
}