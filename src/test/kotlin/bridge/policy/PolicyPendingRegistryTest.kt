package bridge.policy

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test
import java.util.concurrent.CountDownLatch
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit

class PolicyPendingRegistryTest {

    private val success = VaultPolicyReply.Success(
        policyRequestId = "p1",
        actionType = "FILL_FORM",
        decision = "PARTIAL",
        agentAllowed = listOf("name"),
        vaultRequired = listOf("ssn"),
        userApprovalRequired = false,
    )

    @Test
    fun completeMatchesRequestId() {
        val registry = PolicyPendingRegistry()
        val future = registry.register("p1")
        assertTrue(registry.complete("p1", success))
        assertEquals(success, future.get(1, TimeUnit.SECONDS))
        assertEquals(0, registry.size())
    }

    @Test
    fun lateResponseIsIgnored() {
        val registry = PolicyPendingRegistry()
        val future = registry.register("p1")
        assertTrue(registry.complete("p1", success))
        assertFalse(registry.complete("p1", success))
        assertTrue(future.isDone)
        assertEquals(0, registry.size())
    }

    @Test
    fun duplicateResponseIsIgnored() {
        val registry = PolicyPendingRegistry()
        registry.register("p1")
        assertTrue(
            registry.fail(
                "p1",
                PolicyQueryError(PolicyErrorCode.TIMEOUT, "timeout"),
            ),
        )
        assertFalse(
            registry.fail(
                "p1",
                PolicyQueryError(PolicyErrorCode.TIMEOUT, "timeout-2"),
            ),
        )
    }

    @Test
    fun failAllCompletesPending() {
        val registry = PolicyPendingRegistry()
        val first = registry.register("a")
        val second = registry.register("b")
        registry.failAll(
            PolicyQueryError(PolicyErrorCode.VAULT_DISCONNECTED, "gone"),
        )
        assertTrue(first.isDone)
        assertTrue(second.isDone)
        assertEquals(0, registry.size())
        val reply = first.get(1, TimeUnit.SECONDS) as VaultPolicyReply.Failure
        assertEquals(PolicyErrorCode.VAULT_DISCONNECTED, reply.error.code)
    }

    @Test
    fun concurrentRequestsStayCorrelated() {
        val registry = PolicyPendingRegistry()
        val n = 20
        val executor = Executors.newFixedThreadPool(n)
        val start = CountDownLatch(1)
        val done = CountDownLatch(n)
        val futures = (0 until n).map { index ->
            val id = "p-$index"
            val future = registry.register(id)
            executor.submit {
                start.await()
                registry.complete(
                    id,
                    success.copy(
                        policyRequestId = id,
                        agentAllowed = listOf("f$index"),
                    ),
                )
                done.countDown()
            }
            id to future
        }
        start.countDown()
        assertTrue(done.await(3, TimeUnit.SECONDS))
        futures.forEach { (id, future) ->
            val reply = future.get(1, TimeUnit.SECONDS) as VaultPolicyReply.Success
            assertEquals(id, reply.policyRequestId)
            assertEquals(listOf("f${id.removePrefix("p-")}"), reply.agentAllowed)
        }
        assertEquals(0, registry.size())
        executor.shutdownNow()
    }

    @Test
    fun allowedDecisionsDoNotIncludeFailed() {
        assertFalse(PolicyEvaluationService.ALLOWED_DECISIONS.contains("FAILED"))
    }
}
