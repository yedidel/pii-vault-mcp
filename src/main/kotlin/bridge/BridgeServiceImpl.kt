package bridge

import bridge.Bridge.ActionResponse
import bridge.Bridge.StatusResponse
import org.springframework.stereotype.Service

/**
 * gRPC server implementation for the Bridge service.
 * Manages request delegation to ActionService (Database) and ActionProducer (Kafka).
 */
@Service
class BridgeServiceImpl(
    private val actionService: ActionService,    // DB Operations (Main Branch)
    private val actionProducer: ActionProducer   // Kafka Operations (Feature Branch)
) : BridgeServiceGrpcKt.BridgeServiceCoroutineImplBase() {

    /**
     * Receives an action request, processes it in the DB,
     * and broadcasts it via Kafka for downstream services.
     */
    override suspend fun sendAction(request: Bridge.ActionRequest): ActionResponse {
        println("Received ${request.actionType} request from agent ${request.agentId}")

        // 1. Process and save to Database (returns response with requestId)
        val response = actionService.handleAction(request)

        // 2. Send to Kafka (The new logic from your feature branch)
        // We pass the request to Kafka so other services can react to it
        actionProducer.sendAction(request)

        return response
    }

    /**
     * Retrieves the current status of a specific request from the Database.
     */
    override suspend fun getActionStatus(request: Bridge.StatusRequest): StatusResponse {
        val action = actionService.getActionById(request.requestId)

        return StatusResponse.newBuilder()
            .setRequestId(action.requestId)
            .setStatus(action.status)
            .build()
    }
}