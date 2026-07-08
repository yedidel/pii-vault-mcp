package bridge.workflow.state
import bridge.model.WorkflowEntity
import bridge.repository.WorkflowRepository
import bridge.workflow.WorkflowState
import bridge.workflow.WorkflowStep
import org.springframework.stereotype.Service
import java.time.LocalDateTime

/**
 * Performs workflow state transitions.
 *
 * This is the only component allowed to modify WorkflowEntity state.
 */
@Service
class WorkflowTransitionService(

    private val workflowRepository: WorkflowRepository,

    private val transitionValidator: WorkflowTransitionValidator

) {

    /**
     * Transitions the workflow to the next state.
     *
     * @throws IllegalStateException if the requested transition is illegal.
     */
    fun transition(

        workflowId: String,

        nextState: WorkflowState,

        nextStep: WorkflowStep

    ): WorkflowEntity {

        val workflow = workflowRepository.findById(workflowId)
            .orElseThrow {
                IllegalArgumentException("Workflow $workflowId was not found.")
            }

        if (!transitionValidator.isValidTransition(workflow.currentState, nextState)) {
            throw IllegalStateException(
                "Illegal workflow transition: ${workflow.currentState} -> $nextState"
            )
        }

        workflow.currentState = nextState
        workflow.currentStep = nextStep

        if (nextState == WorkflowState.COMPLETED ||
            nextState == WorkflowState.FAILED) {

            workflow.completedAt = LocalDateTime.now()
            workflow.currentStep = WorkflowStep.FINISHED
        }

        return workflowRepository.save(workflow)
    }
}