package bridge.workflow.events

import bridge.workflow.WorkflowEventType
import java.time.Instant
import java.util.UUID

/**
 * Published when the Bridge receives the Vault's final ActionResponse.
 *
 * The Vault is treated as a black box; the event carries the protocol-level
 * response fields only. Bridge does not interpret Vault internals.
 */
data class ActionResponseReceivedEvent(

    override val eventId: UUID = UUID.randomUUID(),

    override val workflowId: String,

    override val requestId: String,

    override val timestamp: Instant = Instant.now(),

    override val eventType: WorkflowEventType = WorkflowEventType.ACTION_RESPONSE_RECEIVED,

    /**
     * The status value returned by the Vault protocol (e.g. "APPROVED", "REJECTED").
     * Keep it as String to allow future extension (PARTIAL, RETRY_REQUIRED, ...).
     */
    val responseStatus: String,

    /**
     * Opaque result data returned by the Vault. Bridge treats it opaquely.
     */
    val resultData: String? = null,

    /**
     * Immutable context snapshot for convenience (agentId, parameters, etc.)
     */
    val context: ActionContext

) : WorkflowEvent

