package bridge.integration

import bridge.workflow.RequestVaultEvaluationCommand

/**
 * Gateway responsible for communicating with the Vault.
 *
 * The workflow engine depends only on this contract.
 * The implementation may currently use WebSocket, and in the future
 * can be replaced without changing the workflow layer.
 */
interface VaultGateway {

    /**
     * Sends the action to the Vault for evaluation/execution.
     *
     * The Vault will eventually respond with an ActionResponse,
     * which will be translated into a workflow event.
     */
    fun requestEvaluation(command: RequestVaultEvaluationCommand)
}
