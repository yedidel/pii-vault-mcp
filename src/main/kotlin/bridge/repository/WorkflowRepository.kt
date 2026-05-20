package bridge.repository

import bridge.model.WorkflowEntity
import org.springframework.data.jpa.repository.JpaRepository
import org.springframework.stereotype.Repository

@Repository
interface WorkflowRepository : JpaRepository<WorkflowEntity, String>
