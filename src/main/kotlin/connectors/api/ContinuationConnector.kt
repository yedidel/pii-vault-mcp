package connectors.api

import continuation.ConnectorType
import continuation.ContinuationRequest

/**
 * connector responsible for continuing an agent workflow.
 */
interface ContinuationConnector {

    /**
     * connector implementation type.
     */
    val type: ConnectorType

    /**
     * continue a workflow.
     */
    fun continueWorkflow(
        request: ContinuationRequest,
    )
}