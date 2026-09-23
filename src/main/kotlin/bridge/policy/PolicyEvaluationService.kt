package bridge.policy

import bridge.websocket.VaultWebSocketHandler
import org.springframework.stereotype.Service
import java.util.UUID
import java.util.concurrent.TimeUnit
import java.util.concurrent.TimeoutException

@Service
class PolicyEvaluationService(
    private val vaultHandler: VaultWebSocketHandler,
    private val registry: PolicyPendingRegistry,
) {

    fun evaluate(
        agentId: String,
        userInstallId: String,
        actionType: String,
        fieldNames: List<String>,
    ): VaultPolicyReply {
        val trimmedAction = actionType.trim()
        val trimmedInstall = userInstallId.trim()
        if (trimmedAction.isEmpty()) {
            return VaultPolicyReply.Failure(
                PolicyQueryError(
                    PolicyErrorCode.INVALID_REQUEST,
                    "action_type is required",
                ),
            )
        }
        if (trimmedInstall.isEmpty()) {
            return VaultPolicyReply.Failure(
                PolicyQueryError(
                    PolicyErrorCode.INVALID_REQUEST,
                    "user_install_id is required",
                ),
            )
        }

        val names = fieldNames.map { it.trim() }.filter { it.isNotEmpty() }

        if (!vaultHandler.hasActiveVaultSession()) {
            return VaultPolicyReply.Failure(
                PolicyQueryError(
                    PolicyErrorCode.VAULT_DISCONNECTED,
                    "No active Vault connection",
                ),
            )
        }

        val policyRequestId = UUID.randomUUID().toString()
        val future = registry.register(policyRequestId)
        val sent = vaultHandler.sendPolicyEvaluationRequest(
            policyRequestId = policyRequestId,
            userInstallId = trimmedInstall,
            agentId = agentId.trim(),
            actionType = trimmedAction.uppercase(),
            fieldNames = names,
        )
        if (!sent) {
            registry.fail(
                policyRequestId,
                PolicyQueryError(
                    PolicyErrorCode.VAULT_DISCONNECTED,
                    "No active Vault connection",
                ),
            )
            return VaultPolicyReply.Failure(
                PolicyQueryError(
                    PolicyErrorCode.VAULT_DISCONNECTED,
                    "No active Vault connection",
                ),
            )
        }

        return try {
            future.get(timeoutSeconds(), TimeUnit.SECONDS)
        } catch (_: TimeoutException) {
            registry.fail(
                policyRequestId,
                PolicyQueryError(
                    PolicyErrorCode.TIMEOUT,
                    "Vault policy evaluation timed out",
                ),
            )
            VaultPolicyReply.Failure(
                PolicyQueryError(
                    PolicyErrorCode.TIMEOUT,
                    "Vault policy evaluation timed out",
                ),
            )
        } catch (error: Exception) {
            registry.remove(policyRequestId)
            VaultPolicyReply.Failure(
                PolicyQueryError(
                    PolicyErrorCode.INTERNAL,
                    error.message ?: "Policy evaluation failed",
                ),
            )
        }
    }

    companion object {
        val ALLOWED_DECISIONS = setOf(
            "AGENT_ALLOWED",
            "VAULT_ONLY",
            "USER_APPROVAL",
            "PARTIAL",
        )

        internal fun timeoutSeconds(): Long {
            val raw = System.getenv("POLICY_EVALUATION_TIMEOUT_SECONDS")
                ?: System.getProperty("POLICY_EVALUATION_TIMEOUT_SECONDS")
            return raw?.toLongOrNull()?.coerceAtLeast(1L) ?: 5L
        }
    }
}
