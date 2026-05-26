package bridge

import bridge.Bridge.ActionResponse
import bridge.Bridge.StatusResponse
import bridge.websocket.VaultWebSocketHandler
import org.springframework.stereotype.Service
import kotlinx.coroutines.delay
import org.springframework.web.client.RestTemplate

/**
 * BridgeServiceImpl
 * * This class serves as the central orchestrator for the PII Vault Ecosystem.
 * It manages the communication between gRPC clients (Agents), the Database,
 * the Guardian (Reputation Service), and the Vault (User Authorization Service).
 */
@Service
class BridgeServiceImpl(
    private val actionService: ActionService,
    private val vaultHandler: VaultWebSocketHandler,
    private val actionProducer: ActionProducer
) : BridgeServiceGrpcKt.BridgeServiceCoroutineImplBase() {

    private val restTemplate = RestTemplate()

    /**
     * Orchestrates the complete action lifecycle:
     * 1. Reputation Check & Authorization (Project C)
     * 2. Persistence & Audit (Database & Kafka)
     * 3. User Authorization (Project A - Vault via WebSocket)
     * 4. State Synchronization & Feedback (Project C Reporting)
     */
    override suspend fun sendAction(request: Bridge.ActionRequest): ActionResponse {
        println("--- [BRIDGE] Processing ${request.actionType} for agent ${request.agentId} ---")

        // STEP 1: Guardian Reputation Check & Initial Persistence
        // We consult the Guardian service before proceeding. If the domain is malicious
        // or the agent is unauthorized, handleAction will throw an exception or block the flow.
        val responseEntity = try {
            actionService.handleAction(request)
        } catch (e: Exception) {
            println("--- [BRIDGE] Action rejected by safety protocols: ${e.message} ---")
            return ActionResponse.newBuilder()
                .setStatus(Bridge.StatusType.FAILED)
                .setDescription("Action rejected by bridge safety layer: ${e.message}")
                .build()
        }

        val requestId = responseEntity.requestId

        // STEP 2: Kafka Integration (Audit Trail)
        // Record the request for downstream processing and persistent auditing.
        actionProducer.sendActionToKafka(request)

        // STEP 3: Vault Authorization Preparation
        val amount = request.parametersMap["amount"] ?: "0.0"
        val currency = request.parametersMap["currency"] ?: "Unknown"

        // STEP 4: Secure Request Forwarding (Project A)
        // Sends the transaction request to the Vault via WebSocket for user approval.
        vaultHandler.sendRequestToVault(amount, currency, requestId)

        // STEP 5: Polling Mechanism
        // Wait for the human user to Approve or Reject the transaction in the Vault.
        var attempts = 0
        var vaultStatus = "PENDING"

        while (attempts < 30 && vaultStatus == "PENDING") {
            if (VaultWebSocketHandler.pendingResponses.containsKey(requestId)) {
                vaultStatus = VaultWebSocketHandler.pendingResponses[requestId]!!
                VaultWebSocketHandler.pendingResponses.remove(requestId)
                println("--- [DEBUG] Vault response received: $vaultStatus ---")
            } else {
                delay(1000)
                attempts++
            }
        }

        // STEP 6: Final State Synchronization
        // Transition the database record to a terminal state (COMPLETED or REJECTED).
        val finalStatusType = if (vaultStatus == "APPROVED") {
            Bridge.StatusType.COMPLETED
        } else {
            Bridge.StatusType.REJECTED
        }

        actionService.updateActionStatus(
            requestId,
            finalStatusType,
            "Vault session finished with status: $vaultStatus"
        )

        // STEP 7: Project C Integration - Outcome Reporting
        // Provide feedback to the Guardian so it can update domain reputation scores.
        reportToGuardian(request, vaultStatus, requestId)

        // STEP 8: Final gRPC Response Construction
        return ActionResponse.newBuilder()
            .setRequestId(requestId)
            .setStatus(finalStatusType)
            .setDescription(when (vaultStatus) {
                "APPROVED" -> "Transaction successfully authorized by the Vault."
                "REJECTED" -> "Transaction was rejected by the user."
                else -> "Transaction timed out after 30 seconds."
            })
            .build()
    }

    /**
     * Reports the transaction outcome to the Guardian (Project C).
     * This feedback loop is essential for the community-driven reputation system.
     */
    private fun reportToGuardian(request: Bridge.ActionRequest, result: String, requestId: String) {
        try {
            val domain = request.parametersMap["target"] ?: request.parametersMap["domain"] ?: "unknown.com"
            val reportPayload = mapOf(
                "domain" to domain,
                "result" to result,
                "requestId" to requestId
            )
            val GUARDIAN_REPORT_URL = "http://localhost:8001/v1/report"
            restTemplate.postForObject(GUARDIAN_REPORT_URL, reportPayload, Map::class.java)
            println("--- [BRIDGE] Feedback reported to Guardian for domain: $domain ---")
        } catch (e: Exception) {
            println("--- [ERROR] Failed to report feedback to Guardian: ${e.message} ---")
        }
    }

    /**
     * Queries the database for the current status of a specific action.
     */
    override suspend fun getActionStatus(request: Bridge.StatusRequest): StatusResponse {
        val action = actionService.getActionById(request.requestId)
        return StatusResponse.newBuilder()
            .setRequestId(action.requestId)
            .setStatus(action.status)
            .build()
    }
}