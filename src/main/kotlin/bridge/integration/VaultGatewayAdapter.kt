package bridge.integration

import bridge.websocket.VaultWebSocketHandler
import org.springframework.stereotype.Component
import org.slf4j.LoggerFactory

/**
 * Adapter that implements VaultGateway by delegating to the Vault WebSocket handler.
 *
 * The Vault is a black box responsible for all security decisions.
 * This adapter translates workflow commands into Vault protocol requests.
 */
@Component
class VaultGatewayAdapter(
    private val vaultHandler: VaultWebSocketHandler
) : VaultGateway {

    private val logger = LoggerFactory.getLogger(javaClass)

    /**
     * Request the Vault to evaluate an action.
     *
     * The Vault will internally decide:
     * - Whether biometric authentication is required
     * - Whether user approval is required
     * - Whether the action can be executed outside the Vault
     * - How to execute the sensitive parts of the action
     *
     * The Vault responds with a single ActionResponseReceivedEvent (via protocol response).
     *
     * @param workflowId The workflow ID (for tracing)
     * @param requestId The request ID (for correlation)
     * @param amount The amount (if applicable)
     * @param currency The currency (if applicable)
     */
    override fun requestApproval(
        workflowId: String,
        requestId: String,
        amount: String,
        currency: String
    ) {
        try {
            logger.info("Requesting Vault evaluation for request $requestId (workflow: $workflowId)")
            vaultHandler.sendRequestToVault(amount, currency, requestId)
            logger.debug("Vault evaluation request sent for $requestId")
        } catch (e: Exception) {
            logger.error("Failed to send request to Vault: ${e.message}", e)
        }
    }
}

