package bridge
import bridge.ActionEventService
import bridge.repository.ActionRepository
import com.fasterxml.jackson.databind.ObjectMapper
import org.springframework.stereotype.Service
import bridge.Bridge.*
import bridge.model.ActionEntity
import bridge.service.ActionEventPublisherService
import io.grpc.Status
import org.springframework.web.client.RestTemplate

// Data model for Agent authentication response
data class AuthResponse(
    val status: String = "unauthorized",
    val trust_level: String = "none"
)
@Service

class ActionService(
    private val actionRepository: ActionRepository,
    private val objectMapper: ObjectMapper,
    private val actionEventService: ActionEventService,
    private val actionEventPublisherServiceService:ActionEventPublisherService){
    // REST client used to communicate with the Guardian (Project C)
    private val restTemplate = RestTemplate()
    // Guardian Authentication Endpoint
    private val GUARDIAN_AUTH_URL = "http://localhost:8001/v1/authenticate/agent?did="

    /**
     * Validates the request and checks if the agent is authorized.
     */
    fun handleAction(request: ActionRequest): ActionResponse {
        // 1. Ask the Guardian if the Agent is authorized
        if (!isAgentAuthorized(request.agentId)) {
            println("--- [SECURITY] Agent ${request.agentId} is NOT authorized by Guardian ---")
            throw Status.UNAUTHENTICATED
                .withDescription("Agent not authorized by The Guardian")
                .asException()
        }

        // 2. Continue with existing logic (Legal action check, Parameters, etc.)
        val actionType = request.actionType.uppercase()
        if (!isLegalAction(actionType)) return failure("Unknown action type $actionType")

        return processAction(request)
    }

    /**
     * Checks with The Guardian (Project C) if the Agent is legitimate.
     * Uses the Agent's Identity (DID) to verify credentials.
     */
    private fun isAgentAuthorized(agentId: String): Boolean {
        return try {
            val auth = restTemplate.getForObject("$GUARDIAN_AUTH_URL$agentId", AuthResponse::class.java)
            auth?.status == "verified"
        } catch (e: Exception) {
            println("--- [ERROR] Guardian auth unreachable: ${e.message} ---")
            false // Block by default if Guardian is down for maximum security
        }
    }

    /**
     * Checks whether the requested action type is supported by the system.
     */
    private fun isLegalAction(actionType: String): Boolean {
        return actionType in allowedActionTypes
    }

    /**
     * Validates that the parameters provided in the request
     * match the required parameters for the given action type.
     */
    private fun validateParameters(actionType: String, parameters: Map<String, String>): Boolean {
        return when (actionType) {
            "PAYMENT" -> parameters.containsKey("amount") && parameters.containsKey("currency")
            "TRANSACTION" -> parameters.containsKey("amount") && parameters.containsKey("currency") && parameters.containsKey("target")
            "FILL_FORM" -> parameters.containsKey("id") && parameters.containsKey("email") && parameters.containsKey("password") && parameters.containsKey("name")
            else -> false
        }
    }

    /**
     * Processes an action request with idempotency logic.
     * * Checks for an existing pending request with the same signature to prevent duplicates.
     * If not found, persists a new action entity with a unique requestId.
     *
     * @param request The incoming action request.
     * @return Response with the requestId and initial status.
     */
    private fun processAction(request: ActionRequest): ActionResponse {
        // Serialize parameters to JSON to create a unique signature for the request
        val parametersJson = objectMapper.writeValueAsString(request.parametersMap)

        // Step 1: Idempotency Check
        // Define a 2-minute window to look for identical recent actions
        val timeWindow = java.time.LocalDateTime.now().minusMinutes(2)

        val existingAction = actionRepository.findRecentIdenticalAction(
            request.agentId,
            request.actionType.uppercase(),
            parametersJson,
            timeWindow
        )

        if (existingAction != null) {
            println("--- [DB] Idempotency Match: Reusing existing ID ${existingAction.requestId} ---")
            return ActionResponse.newBuilder()
                .setRequestId(existingAction.requestId)
                .setStatus(existingAction.status)
                .setDescription("Duplicate request detected within time window")
                .build()
        }

        // Step 2: Persistence
        // Generate a unique UUID for the new transaction and save it to Postgres
        val requestId = java.util.UUID.randomUUID().toString()
        val newEntity = ActionEntity(
            requestId = requestId,
            agentId = request.agentId,
            userInstallId = request.userInstallId,
            actionType = request.actionType.uppercase(),
            parametersJson = parametersJson,
            status = StatusType.RECEIVED,
            resultData = null
        )

        actionRepository.save(newEntity)
        println("--- [DB] New Action Created and Persisted: $requestId ---")

        // Step 3: Final Response Construction
        return ActionResponse.newBuilder()
            .setRequestId(requestId)
            .setStatus(StatusType.RECEIVED)
            .setDescription("Action identity verified and request accepted")
            .build()
    }
    /**
     * List of all action types supported by the system.
     */
    val allowedActionTypes =
        setOf(
            "PAYMENT",
            "TRANSACTION",
            "FILL_FORM",
        )

    /**
     * Builds an ActionResponse with FAILED status
     * and the provided error message.
     */
    private fun failure(message: String): ActionResponse {
        return ActionResponse.newBuilder()
            .setStatus(StatusType.FAILED)
            .setDescription(message)
            .build()
    }

    /**
     * Retrieves an action from the database by requestId.
     * Throws NOT_FOUND if the action does not exist.
     */
    fun getActionById(requestId: String): ActionEntity {
        val optional = actionRepository.findById(requestId)
        if (optional.isEmpty) {
            throw Status.NOT_FOUND.asException()
        }
        //jpa return wraper optinal that return val or no to avoid from sitation that use in null object
        //here we extrct the object
        return optional.get();

    }
    /**
     * Updates an existing action record in the database with the final status and result data
     * received from the Vault.
     *
     * This method transitions the action from its initial state to a final state, ensuring
     * that the cryptographic proof or status message is persisted for future audits.
     *
     * @throws StatusException if the requestId does not exist in the database.
     */
    fun updateActionStatus(requestId: String, finalStatus: StatusType, resultData: String?) {
        val action = actionRepository.findById(requestId).orElseThrow {
            Status.NOT_FOUND
                .withDescription("Action with ID $requestId not found")
                .asException()
        }

        val oldStatus = action.status
        // Update fields from the Vault response
        action.status = finalStatus
        action.resultData = resultData
        // Persist changes to the database
        actionRepository.save(action)
        val event =actionEventService.checkIfChange(requestId,oldStatus,finalStatus)
        if(event!=null){
            actionEventPublisherServiceService.publish(event)
        }
        println("--- [DB] Persistence Update: Action $requestId transitioned to $finalStatus ---")
    }
    /**
     * Data model for the Guardian's response.
     * Maps the JSON fields from the Project C REST API.
     */
    data class TrustInfo(
        val status: String = "unknown",
        val trust_score: Double = 0.0
    )
}