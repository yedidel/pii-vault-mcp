package bridge.policy

import org.springframework.stereotype.Component
import java.util.concurrent.CompletableFuture
import java.util.concurrent.ConcurrentHashMap

/**
 * Correlates Vault WebSocket policy responses to in-flight gRPC queries.
 * Not an action/workflow store.
 */
@Component
class PolicyPendingRegistry {

    private val pending =
        ConcurrentHashMap<String, CompletableFuture<VaultPolicyReply>>()

    fun register(policyRequestId: String): CompletableFuture<VaultPolicyReply> {
        val future = CompletableFuture<VaultPolicyReply>()
        val existing = pending.putIfAbsent(policyRequestId, future)
        if (existing != null) {
            throw IllegalStateException("Duplicate policyRequestId $policyRequestId")
        }
        return future
    }

    fun complete(policyRequestId: String, reply: VaultPolicyReply): Boolean {
        val future = pending.remove(policyRequestId) ?: return false
        return future.complete(reply)
    }

    fun fail(policyRequestId: String, error: PolicyQueryError): Boolean {
        val future = pending.remove(policyRequestId) ?: return false
        return future.complete(VaultPolicyReply.Failure(error))
    }

    fun failAll(error: PolicyQueryError) {
        val ids = pending.keys.toList()
        for (id in ids) {
            fail(id, error)
        }
    }

    fun remove(policyRequestId: String) {
        pending.remove(policyRequestId)
    }

    fun size(): Int = pending.size
}

data class PolicyQueryError(
    val code: PolicyErrorCode,
    val message: String,
)

enum class PolicyErrorCode {
    VAULT_DISCONNECTED,
    TIMEOUT,
    MALFORMED_POLICY,
    INVALID_USER_INSTALL,
    INVALID_REQUEST,
    UNKNOWN_ACTION,
    INTERNAL,
}

sealed class VaultPolicyReply {
    data class Success(
        val policyRequestId: String,
        val actionType: String,
        val decision: String,
        val agentAllowed: List<String>,
        val vaultRequired: List<String>,
        val userApprovalRequired: Boolean,
    ) : VaultPolicyReply()

    data class Failure(
        val error: PolicyQueryError,
    ) : VaultPolicyReply()
}
