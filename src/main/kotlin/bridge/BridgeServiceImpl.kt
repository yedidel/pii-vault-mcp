package bridge
import bridge.Bridge.ActionResponse
import bridge.Bridge.StatusResponse
import bridge.Bridge.StatusType
import bridge.model.ActionEntity
import bridge.repository.ActionRepository
import io.grpc.Status
import org.springframework.stereotype.Service
import java.util.UUID
import com.fasterxml.jackson.databind.ObjectMapper
/**
 * gRPC service implementation for the Bridge component.
 */
@Service
class BridgeServiceImpl(
    private val actionRepository: ActionRepository,
    private val objectMapper: ObjectMapper,
) : BridgeServiceGrpcKt.BridgeServiceCoroutineImplBase() {
    // suspend function – can wait for long operations without blocking a thread
    override suspend fun sendAction(request: Bridge.ActionRequest): ActionResponse {
        println(
            "Received ${request.actionType} request from agent ${request.agentId} ",
        )
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
     * return the status of request by the agent pool
     */
    override suspend fun getActionStatus(request: Bridge.StatusRequest): Bridge.StatusResponse  {
        val optional=actionRepository.findById(request.requestId);
        if(optional.isEmpty){
            throw Status.NOT_FOUND.asException()
        }
        //jpa return wraper optinal that return val or no to avoid from sitation that use in null object
        //here we extrct the object
        val action=optional.get();
        return StatusResponse.newBuilder()
            .setRequestId(action.requestId)
            .setStatus(action.status).build()
    }

    private fun isAgentAuthorized(agentId: String): Boolean {
        return true // stub for now
    }

    val allowedActionTypes =
        setOf(
            "PAYMENT",
            "TRANSACTION",
            "FILL_FORM",
        )

    private fun failure(message: String): ActionResponse {
        return ActionResponse.newBuilder()
            .setStatus(StatusType.FAILED)
            .setDescription(message)
            .build()
    }

    private fun isLegalAction(actionType: String): Boolean {
        if (actionType in allowedActionTypes)
            {
                return true
            }
        return false
    }

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

    private fun processAction(request: Bridge.ActionRequest): ActionResponse {
        val requestId = UUID.randomUUID().toString()
        val parametersJson = objectMapper.writeValueAsString(request.parametersMap)
        val newEntity = ActionEntity(
            requestId = requestId,
            agentId = request.agentId,
            userInstallId = request.userInstallId,
            actionType = request.actionType.uppercase(),
            parametersJson = parametersJson,
            status = StatusType.RECEIVED,
            resultData = null
        );
        val savedEntity = actionRepository.save(newEntity)
        //to do - saved to Kafka
        return ActionResponse.newBuilder()
            .setRequestId(savedEntity.requestId)
            .setStatus(savedEntity.status)
            .setDescription("Request accepted")
            .build()
    }
}
