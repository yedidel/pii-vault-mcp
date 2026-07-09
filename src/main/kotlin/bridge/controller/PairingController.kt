package bridge.controller

import bridge.service.PairingService
import org.springframework.http.ResponseEntity
import org.springframework.web.bind.annotation.*

@RestController
@RequestMapping("/api/pairing")
class PairingController(private val pairingService: PairingService) {

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
}