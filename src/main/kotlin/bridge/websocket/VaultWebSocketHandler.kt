package bridge.websocket

import org.springframework.stereotype.Component
import org.springframework.web.socket.CloseStatus
import org.springframework.web.socket.TextMessage
import org.springframework.web.socket.WebSocketSession
import org.springframework.web.socket.handler.TextWebSocketHandler
import java.util.concurrent.ConcurrentHashMap

/**
 * VaultWebSocketHandler
 * Manages WebSocket communication between the Bridge and the Vault simulator.
 */
@Component
class VaultWebSocketHandler : TextWebSocketHandler() {

    /**
     * Companion object to hold shared state across the application.
     * sessions: Stores active WebSocket connections.
     * pendingResponses: Stores authorization results (APPROVED/REJECTED) indexed by requestId.
     */
    companion object {
        val sessions = ConcurrentHashMap<String, WebSocketSession>()
        val pendingResponses = ConcurrentHashMap<String, String>()
    }

    /**
     * Triggered when a new Vault connection is established.
     * Saves the session to the shared sessions map.
     */
    override fun afterConnectionEstablished(session: WebSocketSession) {
        sessions[session.id] = session
        println("--- [BRIDGE] Vault connected and saved: ${session.id} ---")
    }

    /**
     * Handles incoming messages from the Vault.
     * Extracts the requestId and updates the pendingResponses map based on the payload.
     */
    override fun handleTextMessage(session: WebSocketSession, message: TextMessage) {
        val payload = message.payload
        println("--- [BRIDGE] RAW PAYLOAD RECEIVED: $payload ---")

        // Regex to extract 'request_id' or 'requestId' regardless of spacing or quotes
        val idPattern = """"(?:request_id|requestId)"\s*:\s*"([^"]+)"""".toRegex()
        val match = idPattern.find(payload)
        val extractedId = match?.groups?.get(1)?.value

        if (extractedId != null) {
            println("--- [BRIDGE] Found ID: $extractedId ---")

            // Logic to determine if the user approved or rejected the action
            if (payload.contains("action_approved")) {
                pendingResponses[extractedId] = "APPROVED"
                println("--- [BRIDGE] Marked as APPROVED ---")
            } else if (payload.contains("action_rejected")) {
                pendingResponses[extractedId] = "REJECTED"
                println("--- [BRIDGE] Marked as REJECTED ---")
            }
        }
    }

    /**
     * Triggered when a Vault connection is closed.
     * Removes the session from the sessions map to prevent memory leaks.
     */
    override fun afterConnectionClosed(session: WebSocketSession, status: CloseStatus) {
        sessions.remove(session.id)
        println("--- [BRIDGE] Vault disconnected: ${session.id} ---")
    }

    /**
     * Sends a request payload to the currently connected Vault.
     * Used by the service layer to initiate the authorization flow.
     */
    fun requestVaultSignature(jsonAction: String) {
        // Finding any open session from the static sessions map
        val activeSession = sessions.values.find { it.isOpen }

        if (activeSession != null) {
            activeSession.sendMessage(TextMessage(jsonAction))
            println("--- [BRIDGE] Successfully sent request to Vault ---")
        } else {
            println("--- [BRIDGE] ERROR: No active vault session found. Size: ${sessions.size} ---")
        }
    }
}