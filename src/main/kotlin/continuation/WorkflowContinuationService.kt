package continuation

/**
 * continues an external agent after a workflow event.
 */
interface WorkflowContinuationService {

    /**
     * continue a workflow using the selected connector.
     */
    fun continueWorkflow(
        connectorType: ConnectorType,
        request: ContinuationRequest,
    )
}