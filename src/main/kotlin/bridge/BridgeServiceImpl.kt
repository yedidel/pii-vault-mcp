package bridge

import bridge.Bridge.ActionResponse
import bridge.Bridge.StatusResponse
import bridge.websocket.VaultWebSocketHandler
import org.springframework.stereotype.Service
import kotlinx.coroutines.delay


/**
 * BridgeServiceImpl
 * Implementation of the gRPC service that acts as a bridge between agents (like Claude)
 * and internal services, including Kafka messaging and Vault authorization.
 */
@Service
class BridgeServiceImpl(
    private val actionService: ActionService,
    private val vaultHandler: VaultWebSocketHandler,
    private val actionProducer: ActionProducer
) : BridgeServiceGrpcKt.BridgeServiceCoroutineImplBase() {

    /**
     * sendAction
     * Primary entry point for action requests. Processes business logic,
     * triggers Kafka events, and initiates the Vault authorization flow.
     */
    override suspend fun sendAction(request: Bridge.ActionRequest): ActionResponse {
        println("Received ${request.actionType} request from agent ${request.agentId}")

        // 1. Persist the initial action in the database
        val response = actionService.handleAction(request)

        // 2. Publish the action to Kafka for downstream consumers
        actionProducer.sendActionToKafka(request)

        // 3. Prepare the authorization request for the Vault
        val amount = request.parametersMap["amount"] ?: "0.0"
        val currency = request.parametersMap["currency"] ?: "Unknown"
        val requestId = response.requestId

        val vaultRequest = """
            {
                "type": "payment_request",
                "request_id": "$requestId",
                "amount": "$amount", 
                "currency": "$currency"
            }
        """.trimIndent()

        // 4. Forward the request to the Python Vault via WebSocket
        vaultHandler.requestVaultSignature(vaultRequest)

        // 5. Polling Mechanism: Wait up to 30 seconds for the Vault's response.
        // Checks the static 'pendingResponses' map in VaultWebSocketHandler.
        var attempts = 0
        var vaultStatus = "PENDING"

        while (attempts < 30 && vaultStatus == "PENDING") {
            if (VaultWebSocketHandler.pendingResponses.containsKey(requestId)) {
                // Response found; retrieve and remove it from memory
                vaultStatus = VaultWebSocketHandler.pendingResponses[requestId]!!
                VaultWebSocketHandler.pendingResponses.remove(requestId)
                println("--- [DEBUG] Success! Found response for: $requestId ---")
            } else {
                // Wait 1 second before next poll (Coroutine-friendly delay)
                delay(1000)
                attempts++
            }
        }

        // 6. Finalize response for the gRPC client (Claude)
        val finalResponse = ActionResponse.newBuilder()
            .setRequestId(requestId)
            // Determine success based on the explicit 'APPROVED' status
            .setStatus(if (vaultStatus == "APPROVED") Bridge.StatusType.COMPLETED else Bridge.StatusType.REJECTED)
            .setDescription(when (vaultStatus) {
                "APPROVED" -> "The user manually authorized the transaction via the Vault."
                "REJECTED" -> "The user explicitly REJECTED this request in the Vault."
                else -> "The request timed out because the Vault did not respond in time."
            })
            .build()

        println("--- [BRIDGE] Final status: ${finalResponse.status} | Reason: ${finalResponse.description} ---")
        return finalResponse
    }

    /**
     * getActionStatus
     * Retrieves the status of a specific action from the database using its ID.
     */
    override suspend fun getActionStatus(request: Bridge.StatusRequest):StatusResponse {
        val action = actionService.getActionById(request.requestId)

        return StatusResponse.newBuilder()
            .setRequestId(action.requestId)
            .setStatus(action.status)
            .build()
    }
}