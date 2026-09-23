package bridge.integration

import bridge.websocket.VaultWebSocketHandler
import bridge.workflow.RequestVaultEvaluationCommand
import org.slf4j.LoggerFactory
import org.springframework.stereotype.Component

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

    override fun requestEvaluation(command: RequestVaultEvaluationCommand) {
        try {
            logger.info(
                "Requesting Vault evaluation for request ${command.requestId} " +
                    "(workflow: ${command.workflowId}, action: ${command.actionType})"
            )

            when (command.actionType.uppercase()) {
                "FILL_FORM" -> vaultHandler.sendFormFillRequestToVault(
                    requestId = command.requestId,
                    formUrl = command.formUrl,
                    fields = command.fields,
                )

                else -> vaultHandler.sendRequestToVault(
                    amount = command.amount,
                    currency = command.currency,
                    requestId = command.requestId,
                )
            }

            logger.debug("Vault evaluation request sent for ${command.requestId}")
        } catch (e: Exception) {
            logger.error("Failed to send request to Vault: ${e.message}", e)
        }
    }
}
