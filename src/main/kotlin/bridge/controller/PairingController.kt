package bridge.controller

import bridge.service.PairingService
import org.springframework.http.ResponseEntity
import org.springframework.web.bind.annotation.*

@RestController
@RequestMapping("/api/pairing")
class PairingController(private val pairingService: PairingService) {

    /**
     * Original POST implementation retained for future production use
     * when the actual physical Vault application performs a secure POST request.
     */
    @PostMapping("/complete")
    fun completePairing(
        @RequestParam token: String,
        @RequestParam did: String
    ): ResponseEntity<String> {
        return try {
            pairingService.completePairing(token, did)
            ResponseEntity.ok("Pairing completed successfully!")
        } catch (e: Exception) {
            ResponseEntity.badRequest().body(e.message)
        }
    }

    /**
     * Development GET endpoint enabling direct browser interaction via link clicks.
     * Renders a clean plain-text response upon successful handshake validation.
     */
    @GetMapping("/complete")
    fun completePairingGet(
        @RequestParam token: String,
        @RequestParam vaultDid: String // Matches the parameter name used in the updated PairingService
    ): ResponseEntity<String> {
        return try {
            pairingService.completePairing(token, vaultDid)
            ResponseEntity.ok("Pairing completed successfully! You can now return to the terminal and start mock_vault.py.")
        } catch (e: Exception) {
            ResponseEntity.badRequest().body("Pairing failed: ${e.message}")
        }
    }
}