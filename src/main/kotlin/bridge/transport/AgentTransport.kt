package bridge.transport

/**
 * Transport abstraction used to resume or notify AI agents.
 *
 * Each implementation encapsulates a different continuation mechanism
 * (Polling, Channel, Thread or Webhook).
 *
 * The workflow engine is completely unaware of the underlying transport.
 */
interface AgentTransport {

    /**
     * Type of continuation mechanism implemented by this transport.
     */
    val type: TransportType

    /**
     * Deliver a workflow event to an agent.
     *
     * The actual implementation depends on the transport mechanism.
     */
    fun send(
        requestId: String,
        message: String
    )
}