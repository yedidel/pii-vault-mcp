package bridge.integration

/**
 * Gateway responsible for notifying the external agent.
 */
interface AgentGateway {

    /**
     * Sends a notification to the agent.
     */
    fun notify(
        requestId: String,
        message: String
    )
}