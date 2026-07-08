package bridge.integration

import org.springframework.stereotype.Component
import org.slf4j.LoggerFactory

/**
 * Adapter that implements AgentGateway for notifying external agents.
 *
 * This adapter is designed to be transport-agnostic and extensible.
 * Future implementations can support:
 * - Polling (current behavior)
 * - Realtime channels (WebSocket, gRPC Server Push)
 * - Thread-based continuations (async resumption)
 * - Webhooks (outbound notifications)
 *
 * Currently, agents poll via gRPC GetActionStatus RPC.
 * This adapter logs the notification intent for future extensibility.
 */
@Component
class AgentGatewayAdapter : AgentGateway {

    private val logger = LoggerFactory.getLogger(javaClass)

    /**
     * Notify an external agent of an action status change.
     *
     * Today this is a no-op because agents poll via gRPC.
     * In the future, this will:
     * - Push notifications via realtime channels
     * - Resume agent threads with continuation events
     * - Trigger webhooks
     * - Send platform-specific messages (Claude Channel, OpenAI Thread)
     *
     * @param requestId The action request ID
     * @param message A human-readable status message
     */
    override fun notify(requestId: String, message: String) {
        logger.info("Agent notification for request $requestId: $message")
        
        // Transport is pluggable here:
        // In the future, could dispatch to different notification handlers based on platform/channel.
        // Example:
        // - resumeViaThreadContinuation(requestId, message)
        // - sendViaRealtimeChannel(requestId, message)
        // - publishWebhook(requestId, message)
        
        // For now: agents poll via gRPC, so we just log.
        // The action status is available via GetActionStatus RPC.
    }
}

