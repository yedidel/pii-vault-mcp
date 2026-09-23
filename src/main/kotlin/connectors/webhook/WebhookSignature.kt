package connectors.webhook

import java.util.UUID
import javax.crypto.Mac
import javax.crypto.spec.SecretKeySpec

object WebhookSignature {

    const val HEADER_NAME = "X-Webhook-Signature"
    const val HEADER_TIMESTAMP = "X-Webhook-Timestamp"
    const val HEADER_NONCE = "X-Webhook-Nonce"
    private const val PREFIX = "sha256="

    fun secretFromEnv(): String =
        readSecret("WEBHOOK_SECRET")
            ?: error("WEBHOOK_SECRET environment variable is required")

    private fun readSecret(name: String): String? =
        System.getenv(name)?.trim()?.takeIf { it.isNotEmpty() }
            ?: System.getProperty(name)?.trim()?.takeIf { it.isNotEmpty() }

    fun newNonce(): String = UUID.randomUUID().toString()

    fun signaturePayload(timestamp: String, nonce: String, body: String): String =
        "$timestamp.$nonce.$body"

    fun sign(timestamp: String, nonce: String, body: String, secret: String): String {
        val mac = Mac.getInstance("HmacSHA256")
        mac.init(SecretKeySpec(secret.toByteArray(Charsets.UTF_8), "HmacSHA256"))
        val hex = mac.doFinal(signaturePayload(timestamp, nonce, body).toByteArray(Charsets.UTF_8))
            .joinToString("") { "%02x".format(it) }
        return "$PREFIX$hex"
    }
}
