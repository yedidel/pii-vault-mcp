package bridge.repository

import bridge.model.WorkflowEntity
import org.springframework.data.jpa.repository.JpaRepository

interface WorkflowRepository : JpaRepository<WorkflowEntity, String> {

    fun findByRequestId(requestId: String): WorkflowEntity?
}