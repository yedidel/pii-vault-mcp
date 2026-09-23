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
    private val objectMapper: ObjectMapper
) {

    /**
     * Validates the incoming request and persists a new action.
     *
     * Agent verification is performed later by the workflow engine.
     */
    fun handleAction(request: ActionRequest): ActionResponse {


        // Validate the requested action type.
        val actionType = request.actionType.uppercase()
        if (!isLegalAction(actionType)) return failure("Unknown action type $actionType")

        val sensitiveError = FillFormParameterPolicy.validate(actionType, request.parametersMap)
        if (sensitiveError != null) return failure(sensitiveError)

        return processAction(request)
    }


    /**
     * Checks whether the requested action type is supported by the system.
     */
    private fun isLegalAction(actionType: String): Boolean {
        return actionType in allowedActionTypes
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
            .setDescription("Action received successfully")
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