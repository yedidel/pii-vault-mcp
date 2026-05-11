package bridge.websocket

import org.springframework.stereotype.Component
import org.springframework.web.socket.CloseStatus
import org.springframework.web.socket.TextMessage
import org.springframework.web.socket.WebSocketSession
import org.springframework.web.socket.handler.TextWebSocketHandler
import java.util.concurrent.ConcurrentHashMap
import org.springframework.scheduling.annotation.Scheduled
import org.web3j.crypto.Keys
import org.web3j.crypto.Sign
import org.web3j.utils.Numeric
import org.json.JSONObject

/**
 * VaultWebSocketHandler
 * Manages WebSocket communication between the Bridge and the Vault simulator.
 */
@Component
class VaultWebSocketHandler : TextWebSocketHandler() {

    /**
     * Heartbeat Mechanism (Keep-Alive)
     * * This function runs periodically to ensure the WebSocket connection remains active.
     * Many network intermediaries (like proxies or load balancers) may close idle
     * connections if no data is transmitted within a specific timeframe.
     */
    @Scheduled(fixedRate = 20000) // Executes every 20 seconds
    fun sendHeartbeat() {
        // Create a lightweight JSON payload to signal that the Bridge is still online
        val heartbeatMessage = TextMessage(
            """{"type": "heartbeat", "timestamp": "${System.currentTimeMillis()}"}"""
        )
        println("--- [BRIDGE] Sending heartbeat to 1 active sessions ---")

        // Iterate through all active Vault sessions
        sessions.values.forEach { session ->
            if (session.isOpen) {
                try {
                    // Send the heartbeat signal to the connected Vault
                    session.sendMessage(heartbeatMessage)
                } catch (e: Exception) {
                    // Log failure if a message cannot be delivered to a specific session
                    println("--- [BRIDGE] Failed to send heartbeat to ${session.id}: ${e.message} ---")
                }
            }
        }
    }

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
        val json = JSONObject(message.payload)
        val type = json.optString("type")

        if (type == "connection_init") {
            val did = json.getString("did")
            val timestamp = json.getString("timestamp")
            val signature = json.getString("signature")

            // --- English Documentation ---
            // Security Check: Verify that the Vault actually owns the DID it claims to have.
            // If the signature is invalid, we close the session immediately.
            if (isSignatureValid(did, timestamp, signature)) {
                println("--- [BRIDGE] Vault verified successfully: $did ---")
                session.sendMessage(TextMessage("""{"type": "connection_ack"}"""))
            } else {
                println("--- [BRIDGE] SECURITY ALERT: Invalid signature from $did. Closing connection. ---")
                session.close()
            }
        }
    }

    /**
     * Recovers the Ethereum address from the provided signature and compares it with the DID.
     */
    private fun isSignatureValid(did: String, timestamp: String, signature: String): Boolean {
        return try {
            val message = "vault_auth_$timestamp"
            val msgBytes = message.toByteArray()

            // Ethereum specific prefix requirement
            val prefix = "\u0019Ethereum Signed Message:\n${msgBytes.size}".toByteArray()
            val totalMsg = prefix + msgBytes

            val signatureBytes = Numeric.hexStringToByteArray(signature)
            val v = signatureBytes[64]
            val r = signatureBytes.copyOfRange(0, 32)
            val s = signatureBytes.copyOfRange(32, 64)

            val sd = Sign.SignatureData(v, r, s)
            val ecKey = Sign.signedMessageToKey(totalMsg, sd)
            val recoveredAddress = "0x" + Keys.getAddress(ecKey)

            // Check if the address in the DID matches the recovered address from the signature
            did.contains(recoveredAddress, ignoreCase = true)
        } catch (e: Exception) {
            false
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