package bridge.model
import bridge.Bridge.StatusType
import jakarta.persistence.*
import java.time.LocalDateTime
import org.hibernate.annotations.JdbcTypeCode
import org.hibernate.type.SqlTypes

@Entity
@Table(name = "actions")
class ActionEntity(
    @Id
    @Column(name = "request_id", nullable = false)
    val requestId: String,
    @Column(name = "agent_id", nullable = false)
    val agentId: String,
    @Column(name = "user_install_id", nullable = false)
    val userInstallId: String,
    // not an enum we check ligal in server
    @Column(name = "action_type", nullable = false)
    val actionType: String,
    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "parameters_json", columnDefinition = "jsonb")
    val parametersJson: String? = null,

    // Unused by the live workflow. Kept for schema compatibility.
    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "context_json", columnDefinition = "jsonb")
    val contextJson: String? = null,

    // Enumerated-to save enum as string not number
    @Enumerated(EnumType.STRING)
    @Column(name = "status", nullable = false)
    var status: StatusType,
    @Column(name = "result_data", columnDefinition = "text")
    var resultData: String? = null,
    @Column(name = "created_at", nullable = false)
    var createdAt: LocalDateTime = LocalDateTime.now(),
    @Column(name = "updated_at", nullable = false)
    var updatedAt: LocalDateTime = LocalDateTime.now(),
) {
    @PreUpdate
    fun onUpdate() {
        updatedAt = LocalDateTime.now()
    }

    @PrePersist
    fun onCreate() {
        createdAt = LocalDateTime.now()
        updatedAt = LocalDateTime.now()
    }
}
