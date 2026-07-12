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
     * and generates a direct completion link that bypasses the UI.
     */
    fun initiatePairing(userId: String): PairingResponse {
        // 1. Generate a secure, random temporary pairing token
        val token = UUID.randomUUID().toString()

        // 2. Persist the temporary pairing session as PENDING
        val session = PairingSessionEntity(pairingToken = token, userId = userId)
        pairingSessionRepository.save(session)

        // 3. Direct completion link performing the pairing in one invocation (contains the token and hardcoded DID)
        val appLink = "http://localhost:8081/api/pairing/complete?token=$token&vaultDid=did:ethr:0x19E7E376E7C213B7E7e7e46cc70A5dD086DAff2A"

        // 4. Generate the QR code endpoint via secure Google Charts API to bypass client safety restrictions
        val encodedLink = URLEncoder.encode(appLink, StandardCharsets.UTF_8.toString())
        val qrCodeUrl = "https://chart.googleapis.com/chart?chs=150x150&cht=qr&chl=$encodedLink"

        println("--- [BRIDGE] Safe pairing initiated for user $userId. Token: $token ---")

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