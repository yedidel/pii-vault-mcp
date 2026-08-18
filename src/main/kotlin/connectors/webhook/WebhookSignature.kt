package connectors.webhook

import javax.crypto.Mac
import javax.crypto.spec.SecretKeySpec

object WebhookSignature {

    const val HEADER_NAME = "X-Webhook-Signature"
    private const val PREFIX = "sha256="

    fun secretFromEnv(): String =
        System.getenv("WEBHOOK_SECRET")?.trim()?.takeIf { it.isNotEmpty() }
            ?: "my-secret-key-12345"

    fun sign(body: String, secret: String): String {
        val mac = Mac.getInstance("HmacSHA256")
        mac.init(SecretKeySpec(secret.toByteArray(Charsets.UTF_8), "HmacSHA256"))
        val hex = mac.doFinal(body.toByteArray(Charsets.UTF_8))
            .joinToString("") { "%02x".format(it) }
        return "$PREFIX$hex"
    }
}