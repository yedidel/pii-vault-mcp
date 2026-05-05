package bridge.websocket

import org.springframework.stereotype.Component
import org.springframework.web.socket.CloseStatus
import org.springframework.web.socket.TextMessage
import org.springframework.web.socket.WebSocketSession
import org.springframework.web.socket.handler.TextWebSocketHandler
import java.util.concurrent.ConcurrentHashMap

@Component
class VaultWebSocketHandler : TextWebSocketHandler() {

    // משתמשים במפה כדי לשמור את החיבור (במידה ויהיו כמה כספות בעתיד)
    private val sessions = ConcurrentHashMap<String, WebSocketSession>()

    override fun afterConnectionEstablished(session: WebSocketSession) {
        println("New connection established from Vault: ${session.id}")
        sessions[session.id] = session
    }

    override fun handleTextMessage(session: WebSocketSession, message: TextMessage) {
        val payload = message.payload
        println("Received from Vault: $payload")
        // כאן תוכלי להוסיף לוגיקה לפענוח ה-Handshake שקיבלת מהפייתון
    }

    override fun afterConnectionClosed(session: WebSocketSession, status: CloseStatus) {
        println("Vault connection closed: ${session.id}")
        sessions.remove(session.id)
    }

    // פונקציה לשליחת הודעה לכספת (תקראי לה מהקוד שלך כשיש בקשת תשלום)
    fun sendActionRequest(jsonPayload: String) {
        sessions.values.forEach { session ->
            if (session.isOpen) {
                session.sendMessage(TextMessage(jsonPayload))
            }
        }
    }
}