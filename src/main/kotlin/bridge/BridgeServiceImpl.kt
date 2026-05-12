package bridge

import bridge.Bridge.ActionResponse
import bridge.Bridge.StatusResponse
import bridge.websocket.VaultWebSocketHandler
import org.springframework.stereotype.Service
import kotlinx.coroutines.delay

/**
 * BridgeServiceImpl
 * Acts as the orchestrator between gRPC clients and the Vault.
 * This service manages the end-to-end flow: from persistence and Kafka messaging
 * to secure communication with the Vault and final state synchronization.
 */
@Service
class BridgeServiceImpl(
    private val actionService: ActionService,
    private val vaultHandler: VaultWebSocketHandler,
    private val actionProducer: ActionProducer
) : BridgeServiceGrpcKt.BridgeServiceCoroutineImplBase() {

    override suspend fun sendAction(request: Bridge.ActionRequest): ActionResponse {
        println("--- [BRIDGE] Processing ${request.actionType} for agent ${request.agentId} ---")

        // 1. Business Logic & Initial Persistence
        // This call performs idempotency checks and saves the action with 'RECEIVED' status.
        val response = actionService.handleAction(request)

        // 2. Kafka Integration
        // Audit trail: sending the request to Kafka for downstream processing or logging.
        actionProducer.sendActionToKafka(request)

        // 3. Vault Authorization Preparation
        val amount = request.parametersMap["amount"] ?: "0.0"
        val currency = request.parametersMap["currency"] ?: "Unknown"
        val requestId = response.requestId

        // 4. Secure Request Forwarding
        // Forwards the simulated encrypted payload to the Vault via WebSocket.
        vaultHandler.sendRequestToVault(amount, currency, requestId)

        // 5. Polling Mechanism: Wait for the Vault's response (Max 30s)
        var attempts = 0
        var vaultStatus = "PENDING"

        while (attempts < 30 && vaultStatus == "PENDING") {
            if (VaultWebSocketHandler.pendingResponses.containsKey(requestId)) {
                vaultStatus = VaultWebSocketHandler.pendingResponses[requestId]!!
                VaultWebSocketHandler.pendingResponses.remove(requestId)
                println("--- [DEBUG] Vault response received for: $requestId ---")
            } else {
                delay(1000)
                attempts++
            }
        }

        /**
         * 6. Persistence Update (Final State Synchronization)
         * CRITICAL: Transitions the database record from RECEIVED to its final terminal state.
         * This ensures the Postgres table reflects the actual outcome of the Vault's decision.
         */
        val finalStatusType = if (vaultStatus == "APPROVED") {
            Bridge.StatusType.COMPLETED
        } else {
            Bridge.StatusType.REJECTED
        }

        // Updating the Database via ActionService
        actionService.updateActionStatus(
            requestId,
            finalStatusType,
            "Vault result: $vaultStatus"
        )

        // 7. Final gRPC Response Construction
        val finalResponse = ActionResponse.newBuilder()
            .setRequestId(requestId)
            .setStatus(finalStatusType)
            .setDescription(when (vaultStatus) {
                "APPROVED" -> "Success: The transaction was securely authorized by the Vault."
                "REJECTED" -> "Failure: The user manually rejected the request."
                else -> "Timeout: The Vault did not respond within the 30-second window."
            })
            .build()

        println("--- [BRIDGE] Final Result: ${finalResponse.status} ---")
        return finalResponse
    }

    /**
     * Retrieves the current status of an action from the database.
     */
    override suspend fun getActionStatus(request: Bridge.StatusRequest): StatusResponse {
        val action = actionService.getActionById(request.requestId)
        return StatusResponse.newBuilder()
            .setRequestId(action.requestId)
            .setStatus(action.status)
            .build()
    }
}