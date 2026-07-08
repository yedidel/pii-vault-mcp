package bridge.workflow

import bridge.repository.WorkflowRepository
import org.springframework.stereotype.Service

@Service
class WorkflowRecoveryService(

    private val workflowRepository: WorkflowRepository,

    private val workflowEngine: WorkflowEngine

) {

    fun recoverUnfinishedWorkflows() {

        println("----- [WORKFLOW RECOVERY] Recovery started -----")

        val workflows =
            workflowRepository.findByCurrentStateIn(
                listOf(
                    WorkflowState.RECEIVED,
                    WorkflowState.WAITING_FOR_GUARDIAN,
                    WorkflowState.WAITING_FOR_VAULT_RESPONSE,
                    WorkflowState.IN_PROGRESS
                )
            )

        println(
            "----- [WORKFLOW RECOVERY] Found ${workflows.size} unfinished workflows -----"
        )

        workflows.forEach { workflow ->

            try {
                workflowEngine.resume(workflow.workflowId)
            } catch (e: Exception) {
                println(
                    """
                    ----- [WORKFLOW RECOVERY ERROR] Failed to recover workflow -----
                    Workflow : ${workflow.workflowId}
                    Request  : ${workflow.requestId}
                    State    : ${workflow.currentState}
                    Error    : ${e.message}
                    """.trimIndent()
                )
                e.printStackTrace()
            }
        }

        println("----- [WORKFLOW RECOVERY] Recovery finished -----")
    }
}