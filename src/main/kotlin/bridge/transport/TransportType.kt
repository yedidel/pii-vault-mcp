package bridge.transport

/**
 * Supported transport mechanisms for resuming AI agents.
 *
 * The Bridge routes workflow events through one of these mechanisms,
 * depending on the capabilities of the target AI platform.
 */
enum class TransportType {

    /**
     * Agent periodically polls the Bridge for updates.
     */
    POLLING,

    /**
     * Bridge pushes events through a live channel or session.
     */
    CHANNEL,

    /**
     * Bridge resumes an existing conversation or thread.
     */
    THREAD,

    /**
     * Bridge sends an HTTP callback to an external endpoint.
     */
    WEBHOOK
}