package bridge.repository

import bridge.model.WorkflowEntity
import bridge.workflow.WorkflowState
import org.springframework.data.jpa.repository.JpaRepository

interface WorkflowRepository : JpaRepository<WorkflowEntity, String> {

    fun findByRequestId(requestId: String): WorkflowEntity?

    fun findByCurrentStateIn(
        states: Collection<WorkflowState>
    ): List<WorkflowEntity>
}