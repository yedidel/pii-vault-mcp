package bridge
import bridge.repository.ActionRepository
import com.fasterxml.jackson.databind.ObjectMapper
import org.springframework.stereotype.Service
import bridge.Bridge.*
import bridge.model.ActionEntity
import io.grpc.Status


@Service
class ActionService(
    private val actionRepository: ActionRepository,
    private val objectMapper: ObjectMapper){

    /**
     * Validates the request and checks if the agent is authorized.
     * If everything is valid, forwards the request for processing.
     */
    fun handleAction(request: ActionRequest): ActionResponse {
        if (!isAgentAuthorized(request.agentId)) {
            throw Status.UNAUTHENTICATED
                .withDescription("Agent not authorized")
                .asException()
        }
        val actionType = request.actionType.uppercase()
        if (!isLegalAction(actionType)) {
            return failure("Unknown action type $actionType")
        }
        if (!validateParameters(actionType, request.parametersMap)) {
            return failure("Missing or invalid parameters of request $actionType")
        }
        return processAction(request)
    }

    /**
     * Checks whether the agent is authorized to perform actions.
     * In the future this will call the Guardian service.
     */
    private fun isAgentAuthorized(agentId: String): Boolean {
        return true // stub for now
    }

    /**
     * Checks whether the requested action type is supported by the system.
     */
    private fun isLegalAction(actionType: String): Boolean {
        if (actionType in allowedActionTypes)
        {
            return true
        }
        return false
    }

    /**
     * Validates that the parameters provided in the request
     * match the required parameters for the given action type.
     */
    private fun validateParameters(
        actionType: String,
        parameters: Map<String, String>,
    ): Boolean {
        return when (actionType) {
            // like write if
            "PAYMENT" -> {
                parameters.containsKey("amount") && parameters.containsKey("currency")
            }
            "TRANSACTION" -> {
                parameters.containsKey("amount") &&
                        parameters.containsKey("currency") &&
                        parameters.containsKey("target")
            }
            "FILL_FORM" -> {
                parameters.containsKey("id") &&
                        parameters.containsKey("email") &&
                        parameters.containsKey("password") &&
                        parameters.containsKey("name")
            }
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
        val parametersJson = objectMapper.writeValueAsString(request.parametersMap)

        // Define the idempotency window (e.g., 2 minutes)
        val timeWindow = java.time.LocalDateTime.now().minusMinutes(2)

        // Lookup any identical action within the time window
        val existingAction = actionRepository.findRecentIdenticalAction(
            request.agentId,
            request.actionType.uppercase(),
            parametersJson,
            timeWindow
        )

        if (existingAction != null) {
            println("--- [DB] Idempotency Match (Time Window): Reusing ID ${existingAction.requestId} ---")
            return ActionResponse.newBuilder()
                .setRequestId(existingAction.requestId)
                .setStatus(existingAction.status)
                .setDescription("Duplicate request detected within time window")
                .build()
        }

        // No recent match found; create and persist a new action
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
        println("--- [DB] New Action Created: $requestId ---")

        return ActionResponse.newBuilder()
            .setRequestId(requestId)
            .setStatus(StatusType.RECEIVED)
            .setDescription("Action accepted")
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

        // Update fields from the Vault response
        action.status = finalStatus
        action.resultData = resultData

        // Persist changes to the database
        actionRepository.save(action)
        println("--- [DB] Persistence Update: Action $requestId transitioned to $finalStatus ---")
    }
}
