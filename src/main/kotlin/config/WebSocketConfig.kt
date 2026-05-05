package bridge.config
import org.springframework.context.annotation.Configuration
import org.springframework.web.socket.config.annotation.EnableWebSocket
import org.springframework.web.socket.config.annotation.WebSocketConfigurer
import org.springframework.web.socket.config.annotation.WebSocketHandlerRegistry
import bridge.websocket.VaultWebSocketHandler

@Configuration
@EnableWebSocket
class WebSocketConfig(private val vaultHandler: VaultWebSocketHandler) : WebSocketConfigurer {
    override fun registerWebSocketHandlers(registry: WebSocketHandlerRegistry) {
        // הכתובת להתחברות תהיה: ws://localhost:8080/vault-websocket
        registry.addHandler(vaultHandler, "/vault-websocket")
            .setAllowedOrigins("*") // מאפשר חיבור מכל מקור (חשוב לפיתוח מקומי)
    }
}