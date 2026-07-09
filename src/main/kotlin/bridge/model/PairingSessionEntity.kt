package bridge.model

import jakarta.persistence.*
import java.time.LocalDateTime

@Entity
@Table(name = "pairing_sessions")
class PairingSessionEntity(

    @Id
    @Column(name = "pairing_token", nullable = false, unique = true)
    val pairingToken: String, // The unique temporary UUID used as the primary key

    @Column(name = "user_id", nullable = false)
    val userId: String, // The user identifier coming from the AI agent session

    @Enumerated(EnumType.STRING)
    @Column(name = "status", nullable = false)
    var status: PairingStatus = PairingStatus.PENDING,

    @Column(name = "created_at", nullable = false)
    val createdAt: LocalDateTime = LocalDateTime.now()
)

enum class PairingStatus {
    PENDING,
    COMPLETED,
    EXPIRED
}
