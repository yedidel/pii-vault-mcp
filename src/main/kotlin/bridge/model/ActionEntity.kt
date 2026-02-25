package bridge.model

import jakarta.persistence.*
import java.time.LocalDateTime

@Entity
@Table(name = "actions")
class ActionEntity(
    @Id
    val requestId: String,
    val agentId: String,
    val userInstallId: String,
    val targetDomain: String,
    var status: String,
    val createdAt: LocalDateTime = LocalDateTime.now()
)