package bridge.repository

import bridge.model.ActionEntity
import org.springframework.data.jpa.repository.JpaRepository
import org.springframework.stereotype.Repository
import org.springframework.data.jpa.repository.Query

/**
 * Repository interface for accessing ActionEntity data in the PostgreSQL database.
 */
@Repository
interface ActionRepository : JpaRepository<ActionEntity, String> {

    @Query("""
        SELECT a FROM ActionEntity a 
        WHERE a.agentId = :agentId 
        AND a.actionType = :actionType 
        AND a.parametersJson = :parametersJson 
        AND a.createdAt > :since
    """)
    fun findRecentIdenticalAction(
        agentId: String,
        actionType: String,
        parametersJson: String,
        since: java.time.LocalDateTime
    ): ActionEntity?
}