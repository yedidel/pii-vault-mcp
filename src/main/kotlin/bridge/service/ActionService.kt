package bridge
import bridge.repository.ActionRepository
import com.fasterxml.jackson.databind.ObjectMapper
import org.springframework.stereotype.Service
import bridge.Bridge.*
import bridge.model.ActionEntity
import io.grpc.Status
import java.util.UUID

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
     * Creates a new requestId, converts parameters to JSON,
     * saves the action in the database, and returns an ActionResponse
     * with status RECEIVED.
     */
    private fun processAction(request: ActionRequest): ActionResponse {
        val requestId = UUID.randomUUID().toString()
        //data of the action
        val parametersJson = objectMapper.writeValueAsString(request.parametersMap)
        //snapshot of the process in case of fail
        val contextJson = objectMapper.writeValueAsString(
            mapOf(
                "agentId" to request.agentId,
                "actionType" to request.actionType.uppercase(),
                "parameters" to request.parametersMap,
                "status" to StatusType.WAITING_FOR_USER.name
            )
        )
        val newEntity = ActionEntity(
            requestId = requestId,
            agentId = request.agentId,
            userInstallId = request.userInstallId,
            actionType = request.actionType.uppercase(),
            parametersJson = parametersJson,
            contextJson = contextJson,
            status = StatusType.WAITING_FOR_USER,
            resultData = null
        )
        val savedEntity = actionRepository.save(newEntity)

        updateStatus(
            savedEntity.requestId,
            StatusType.IN_PROGRESS
        )
        //to do - saved to Kafka
        return ActionResponse.newBuilder()
            .setRequestId(savedEntity.requestId)
            .setStatus(savedEntity.status)
            .setDescription("Request accepted")
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

    //Update request status after external event To do: update to get information from user
    fun updateStatus(requestId: String, newStatus: StatusType): ActionEntity {
        val action = getActionById(requestId)

        action.status = newStatus
        actionRepository.save(action)

        if (newStatus == StatusType.IN_PROGRESS) {
            resumeProcess(action)
        }
        return action
    }

    // Continues the request process after user approval using the saved context
    private fun resumeProcess(action: ActionEntity) {
        println("Resuming process for requestId=${action.requestId}")
        val context = objectMapper.readValue(
            action.contextJson,
            Map::class.java
        )
        val actionType = context["actionType"] as String
        when (actionType) {
            "PAYMENT" -> {
                val parameters = context["parameters"] as Map<*, *>
                val amount = parameters["amount"]
                val currency = parameters["currency"]

                println("Processing payment: amount=$amount currency=$currency")

                action.status = StatusType.COMPLETED
                actionRepository.save(action)
                println("Request completed")
            }

            "TRANSACTION" -> {
                println("Processing transaction")
            }

            "FILL_FORM" -> {
                println("Processing form filling")
            }
        }

    }
}
