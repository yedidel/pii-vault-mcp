package bridge.model

import bridge.workflow.WorkflowState
import bridge.workflow.WorkflowStep
import jakarta.persistence.Column
import jakarta.persistence.Entity
import jakarta.persistence.EnumType
import jakarta.persistence.Enumerated
import jakarta.persistence.Id
import jakarta.persistence.PrePersist
import jakarta.persistence.PreUpdate
import jakarta.persistence.Table
import org.hibernate.annotations.JdbcTypeCode
import org.hibernate.type.SqlTypes
import java.time.LocalDateTime
import bridge.transport.TransportType

/**
 * Represents the internal execution state of a workflow.
 *
 * ActionEntity represents the public action visible to the agent.
 * WorkflowEntity represents the internal workflow managed by the Bridge.
 */
@Entity
@Table(name = "workflows")
class WorkflowEntity(

    @Id
    @Column(name = "workflow_id", nullable = false)
    val workflowId: String,

    @Column(name = "request_id", nullable = false, unique = true)
    val requestId: String,

    @Column(name = "platform", nullable = false)
    val platform: String,

    @Column(name = "agent_session_id", nullable = false)
    var agentSessionId: String,

    @Enumerated(EnumType.STRING)
    @Column(name = "current_state", nullable = false)
    var currentState: WorkflowState = WorkflowState.RECEIVED,

    @Enumerated(EnumType.STRING)
    @Column(name = "current_step", nullable = false)
    var currentStep: WorkflowStep = WorkflowStep.ACTION_RECEIVED,

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "context_json", columnDefinition = "jsonb")
    var contextJson: String? = null,

    @Column(name = "created_at", nullable = false)
    var createdAt: LocalDateTime = LocalDateTime.now(),

    @Column(name = "updated_at", nullable = false)
    var updatedAt: LocalDateTime = LocalDateTime.now(),

    @Column(name = "completed_at")
    var completedAt: LocalDateTime? = null,

    @Column(name = "last_executed_command")
    var lastExecutedCommand: String? = null,

    @Enumerated(EnumType.STRING)
    var continuationTransport: TransportType

) {

    @PrePersist
    fun onCreate() {
        createdAt = LocalDateTime.now()
        updatedAt = createdAt
    }

    @PreUpdate
    fun onUpdate() {
        updatedAt = LocalDateTime.now()
    }
}