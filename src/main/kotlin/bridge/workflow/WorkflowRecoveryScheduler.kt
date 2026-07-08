package bridge.workflow

import org.springframework.boot.context.event.ApplicationReadyEvent
import org.springframework.context.event.EventListener
import org.springframework.stereotype.Component

@Component
class WorkflowRecoveryScheduler(

    private val workflowRecoveryService: WorkflowRecoveryService

) {

    /**
     * Runs once after Spring finishes starting.
     */
    @EventListener(ApplicationReadyEvent::class)
    fun recoverOnStartup() {
        workflowRecoveryService.recoverUnfinishedWorkflows()
    }
}