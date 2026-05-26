package bridge.config

import bridge.websocket.VaultWebSocketHandler
import org.springframework.context.annotation.Configuration
import org.springframework.web.socket.config.annotation.EnableWebSocket
import org.springframework.web.socket.config.annotation.WebSocketConfigurer
import org.springframework.web.socket.config.annotation.WebSocketHandlerRegistry

/**
 * WebSocket Configuration
 * Registers the /vault-websocket endpoint and links it to the VaultWebSocketHandler.
 */
@Configuration
@EnableWebSocket
class WebSocketConfig(private val vaultHandler: VaultWebSocketHandler) : WebSocketConfigurer {
    override fun registerWebSocketHandlers(registry: WebSocketHandlerRegistry) {
        // Map the specific handler to the /vault-websocket path and allow cross-origin requests
        registry.addHandler(vaultHandler, "/vault-websocket")
            .setAllowedOrigins("*")
    }
}