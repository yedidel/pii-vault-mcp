package bridge

import bridge.Bridge.ActionResponse
import bridge.Bridge.StatusResponse
import org.springframework.stereotype.Service

/**
 * gRPC server for the Bridge service.
 * Handles request delegation to Database (ActionService) and Kafka (ActionProducer).
 */
@Service
class BridgeServiceImpl(
    private val actionService: ActionService,
    private val actionProducer: ActionProducer
) : BridgeServiceGrpcKt.BridgeServiceCoroutineImplBase() {

    /**
     * Receives and processes an agent action.
     * Persists to Postgres and broadcasts via Kafka.
     */
    override suspend fun sendAction(request: Bridge.ActionRequest): ActionResponse {
        println("Processing ${request.actionType} for agent: ${request.agentId}")

        // 1. Database persistence
        val response = actionService.handleAction(request)

        // 2. Kafka event streaming
        actionProducer.sendActionToKafka(request)

        return response
    }

    /**
     * Fetches the current action status from the database by Request ID.
     */
    override suspend fun getActionStatus(request: Bridge.StatusRequest): StatusResponse {
        val action = actionService.getActionById(request.requestId)

        return StatusResponse.newBuilder()
            .setRequestId(action.requestId)
            .setStatus(action.status)
            .build()
    }
}