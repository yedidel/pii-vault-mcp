package bridge
import com.fasterxml.jackson.databind.ObjectMapper
import org.springframework.stereotype.Service
import bridge.model.WorkflowEntity
import bridge.repository.WorkflowRepository
import java.util.UUID
@Service
class WorkflowService(private val workflowRepository: WorkflowRepository,private val objectMapper: ObjectMapper) {
    fun createWorkflow(requestId: String, platform: String,sessionId: String): WorkflowEntity{
             val workflow=WorkflowEntity(
                 workflowId=UUID.randomUUID().toString(),
                 requestId=requestId,
                 platform=platform,
                 agentSessionId=sessionId
            )
        return workflowRepository.save(workflow)
    }



}