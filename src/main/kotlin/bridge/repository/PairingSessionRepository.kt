package bridge.repository

import bridge.model.PairingSessionEntity
import org.springframework.data.jpa.repository.JpaRepository
import org.springframework.stereotype.Repository
import java.util.Optional

@Repository
interface PairingSessionRepository : JpaRepository<PairingSessionEntity, String> {

    // Helper method to find an active session by its temporary token
    fun findByPairingToken(pairingToken: String): Optional<PairingSessionEntity>
}