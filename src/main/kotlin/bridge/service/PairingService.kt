package bridge.service

import bridge.model.PairingSessionEntity
import bridge.model.PairingStatus
import bridge.repository.PairingSessionRepository
import bridge.repository.UserVaultLinkRepository
import bridge.model.UserVaultLinkEntity
import org.springframework.stereotype.Service
import java.net.URLEncoder
import java.nio.charset.StandardCharsets
import java.time.LocalDateTime
import java.time.Duration
import java.util.UUID

@Service
class PairingService(
    private val pairingSessionRepository: PairingSessionRepository,
    private val userVaultLinkRepository: UserVaultLinkRepository
) {

    /**
     * Initiates a new pairing process for a user.
     * Generates a temporary secure token, saves it to the database,
     * and generates a dynamic QR code URL accessible via local network IP.
     */
    fun initiatePairing(userId: String): PairingResponse {
        // 1. Generate a secure, random temporary pairing token
        val token = UUID.randomUUID().toString()

        // 2. Persist the temporary pairing session as PENDING
        val session = PairingSessionEntity(pairingToken = token, userId = userId)
        pairingSessionRepository.save(session)

        // 3. Define local computer IP so the mobile device can resolve the URL within the same Wi-Fi network
        // TODO: Replace with your actual local IPv4 address (e.g., "192.168.1.15")
        val computerIp = "10.0.0.1"
        val appLink = "http://localhost:8081/mock-vault.html?token=$token"

        // 4. Encode URL parameters and build the dynamic QR code rendering API link
        val encodedLink = URLEncoder.encode(appLink, StandardCharsets.UTF_8.toString())
        val qrCodeUrl = "https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=$encodedLink"

        return PairingResponse(
            pairingToken = token,
            qrCodeUrl = qrCodeUrl,
            appLink = appLink
        )
    }

    /**
     * Completes and validates the pairing flow.
     * Enforces single-use token constraints and a strict 5-minute expiration window.
     */
    fun completePairing(token: String, vaultDid: String) {
        // A. Fetch the session from the temporary database layer
        val session = pairingSessionRepository.findByPairingToken(token)
            .orElseThrow { IllegalArgumentException("Pairing token not found in the system!") }

        // B. Enforce single-use constraint (Idempotency / Anti-replay attack safety)
        if (session.status != PairingStatus.PENDING) {
            throw IllegalStateException("This token has already been consumed or invalidated!")
        }

        // C. Enforce strict 5-minute security lifetime window
        val minutesElapsed = Duration.between(session.createdAt, LocalDateTime.now()).toMinutes()
        if (minutesElapsed >= 5) {
            session.status = PairingStatus.EXPIRED
            pairingSessionRepository.save(session)
            throw IllegalStateException("Token expired! Pairings must be completed within a 5-minute window.")
        }

        // D. Update temporary session state to COMPLETED
        session.status = PairingStatus.COMPLETED
        pairingSessionRepository.save(session)

        // E. Commit permanent link binding the user identity to the secure cryptographic vault identity
        val permanentLink = UserVaultLinkEntity(userId = session.userId, vaultDid = vaultDid)
        userVaultLinkRepository.save(permanentLink)

        println("--- [BRIDGE] Successfully paired user ${session.userId} with Vault DID: $vaultDid ---")
    }
}

/**
 * Data class representing the pairing response context.
 */
data class PairingResponse(
    val pairingToken: String,
    val qrCodeUrl: String,
    val appLink: String
)