package bridge
import bridge.Bridge.StatusResponse
import bridge.Bridge.ActionResponse
import bridge.Bridge.StatusType
import java.util.UUID
import io.grpc.Status

/**
 * gRPC service implementation for the Bridge component.
 */
class BridgeServiceImpl : BridgeServiceGrpcKt.BridgeServiceCoroutineImplBase() {
    // suspend function – can wait for long operations without blocking a thread
    override suspend fun sendAction(request: Bridge.ActionRequest): ActionResponse {
        println(
            "Received ${request.actionType} request from agent ${request.agentId} ")
        //
        if (!isAgentAuthorized(request.agentId)) {
            throw Status.UNAUTHENTICATED
                .withDescription("Agent not authorized")
                .asException()
        }
        val actionType= request.actionType.uppercase();
        if(!isLegalAction(actionType)) {
            return failure("Unknown action type $actionType");
        }
        if (!validateParameters(actionType, request.parametersMap)) {
            return failure("Missing or invalid parameters of request $actionType");
        }
        return processAction(request);
    }

    /**
     * return the status of request by the agent pool
     */
    override suspend fun getActionStatus(request:Bridge.StatusRequest): Bridge.StatusResponse{
        return StatusResponse.newBuilder()
            .setRequestId(request.requestId)
            .setStatus(StatusType.RECEIVED).build()
    }
    private fun isAgentAuthorized(agentId: String): Boolean {
        return true // stub for now
    }
    val allowedActionTypes=setOf(
        "PAYMENT",
        "TRANSACTION",
        "FILL_FORM"
    )
    private fun failure(message: String): ActionResponse {
        return ActionResponse.newBuilder()
            .setStatus(StatusType.FAILED)
            .setDescription(message)
            .build()
    }
    private fun isLegalAction(actionType: String): Boolean {
        if(actionType in allowedActionTypes){
            return true;
        }
        return false;
    }
    private fun validateParameters(actionType: String,parameters: Map<String, String>):Boolean {
        return when (actionType) {
            //like write if
            "PAYMENT" -> {
                parameters.containsKey("amount")&&parameters.containsKey("currency")
            }
            "TRANSACTION" -> {
                parameters.containsKey("amount")&&
                parameters.containsKey("currency")&&
                parameters.containsKey("target")
            }
            "FILL_FORM" -> {
                parameters.containsKey("id")&&
                parameters.containsKey("email")&&
                parameters.containsKey("password")&&
                parameters.containsKey("name")
            }
            else -> false;
        }
    }
    private fun processAction(request: Bridge.ActionRequest): ActionResponse {
        val requestId = UUID.randomUUID().toString();
        //TO DO -save to db and Kafka
        return ActionResponse.newBuilder()
            .setRequestId(requestId)
            .setStatus(StatusType.RECEIVED)
            .setDescription("Request accepted")
            .build()
    }
}