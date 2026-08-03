package connectors.registry

import continuation.ConnectorType
import continuation.WorkflowContinuationService
import connectors.api.ContinuationConnector
import continuation.ContinuationRequest
import org.springframework.stereotype.Component

/**
 * finds the connector for the requested continuation type.
 */
@Component
class ContinuationRegistry(

    connectors: List<ContinuationConnector>,

    ) : WorkflowContinuationService {

    private val connectorsByType =
        connectors.associateBy { it.type }

    /**
     * continue a workflow using the selected connector.
     */
    override fun continueWorkflow(
        connectorType: ConnectorType,
        request: ContinuationRequest,
    ) {

        val connector =
            connectorsByType[connectorType]
                ?: error("No connector registered for $connectorType")

        connector.continueWorkflow(request)
    }
}