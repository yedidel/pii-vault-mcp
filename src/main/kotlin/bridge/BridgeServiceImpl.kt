package bridge

import bridge.Bridge.ActionResponse
import bridge.Bridge.StatusResponse
import bridge.websocket.VaultWebSocketHandler
import org.springframework.stereotype.Service
import kotlinx.coroutines.delay

/**
 * BridgeServiceImpl
 * Acts as the orchestrator between gRPC clients (like Claude) and the Vault.
 * This version uses simulated encryption (Base64) to communicate with the Vault.
 */
@Service
class BridgeServiceImpl(
    private val actionService: ActionService,
    private val vaultHandler: VaultWebSocketHandler,
    private val actionProducer: ActionProducer
) : BridgeServiceGrpcKt.BridgeServiceCoroutineImplBase() {

    override suspend fun sendAction(request: Bridge.ActionRequest): ActionResponse {
        println("--- [BRIDGE] Processing ${request.actionType} for agent ${request.agentId} ---")

        // 1. Business Logic & Persistence
        val response = actionService.handleAction(request)

        // 2. Kafka Integration
        actionProducer.sendActionToKafka(request)

        // 3. Vault Authorization Flow
        val amount = request.parametersMap["amount"] ?: "0.0"
        val currency = request.parametersMap["currency"] ?: "Unknown"
        val requestId = response.requestId

        // --- UPDATED STEP 4: Secure Request Forwarding ---
        // Instead of building a raw JSON string here, we call the secure method
        // in the handler that simulates the encryption protocol.
        vaultHandler.sendRequestToVault(amount, currency, requestId)

        // 5. Polling Mechanism: Wait for the Vault's response (Max 30s)
        var attempts = 0
        var vaultStatus = "PENDING"

        while (attempts < 30 && vaultStatus == "PENDING") {
            // Accessing the static response map managed by the VaultWebSocketHandler
            if (VaultWebSocketHandler.pendingResponses.containsKey(requestId)) {
                vaultStatus = VaultWebSocketHandler.pendingResponses[requestId]!!
                VaultWebSocketHandler.pendingResponses.remove(requestId)
                println("--- [DEBUG] Vault response received for: $requestId ---")
            } else {
                delay(1000) // Non-blocking wait
                attempts++
            }
        }

        // 6. Final gRPC Response Construction
        val finalResponse = ActionResponse.newBuilder()
            .setRequestId(requestId)
            .setStatus(if (vaultStatus == "APPROVED") Bridge.StatusType.COMPLETED else Bridge.StatusType.REJECTED)
            .setDescription(when (vaultStatus) {
                "APPROVED" -> "Success: The transaction was securely authorized by the Vault."
                "REJECTED" -> "Failure: The user manually rejected the request."
                else -> "Timeout: The Vault did not respond within the 30-second window."
            })
            .build()

        println("--- [BRIDGE] Final Result: ${finalResponse.status} ---")
        return finalResponse
    }

    override suspend fun getActionStatus(request: Bridge.StatusRequest): StatusResponse {
        val action = actionService.getActionById(request.requestId)
        return StatusResponse.newBuilder()
            .setRequestId(action.requestId)
            .setStatus(action.status)
            .build()
    }
}