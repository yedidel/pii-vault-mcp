package bridge.websocket

import org.springframework.stereotype.Component
import org.springframework.web.socket.TextMessage
import org.springframework.web.socket.WebSocketSession
import org.springframework.web.socket.handler.TextWebSocketHandler
import org.json.JSONObject
import java.util.Base64
import java.util.concurrent.ConcurrentHashMap

/**
 * Bridge Handler: Secure Protocol Simulation.
 * Manages WebSocket sessions and stores responses for the Bridge Service to poll.
 */
@Component
class VaultWebSocketHandler : TextWebSocketHandler() {

    // Global storage for responses so the Service can find them by RequestID
    companion object {
        val pendingResponses = ConcurrentHashMap<String, String>()
    }

    private var vaultSession: WebSocketSession? = null

    override fun handleTextMessage(session: WebSocketSession, message: TextMessage) {
        val payload = JSONObject(message.payload)
        val type = payload.optString("type")
        val requestId = payload.optString("request_id")

        when (type) {
            "connection_init" -> {
                println("--- [BRIDGE] Handshake from Vault: ${payload.optString("did")} ---")
                this.vaultSession = session
                session.sendMessage(TextMessage("""{"type": "connection_ack"}"""))
            }
            "action_approved" -> {
                println("--- [BRIDGE] Success for ID: $requestId ---")
                pendingResponses[requestId] = "APPROVED"
            }
            "action_rejected" -> {
                println("--- [BRIDGE] Rejected for ID: $requestId ---")
                pendingResponses[requestId] = "REJECTED"
            }
        }
    }

    /**
     * Sends a simulated encrypted payload to the Vault.
     */
    fun sendRequestToVault(amount: String, currency: String, requestId: String) {
        if (vaultSession == null || !vaultSession!!.isOpen) {
            println("--- [ERROR] No active Vault connection ---")
            pendingResponses[requestId] = "ERROR_NO_CONNECTION"
            return
        }

        val rawMessage = "amount=$amount;currency=$currency;timestamp=${System.currentTimeMillis()}"
        val encodedData = Base64.getEncoder().encodeToString(rawMessage.toByteArray())

        val request = JSONObject()
        request.put("type", "payment_request")
        request.put("request_id", requestId)
        request.put("data", encodedData)

        vaultSession?.sendMessage(TextMessage(request.toString()))
        println("--- [BRIDGE] Sent encrypted payload to Vault for ID: $requestId ---")
    }
}