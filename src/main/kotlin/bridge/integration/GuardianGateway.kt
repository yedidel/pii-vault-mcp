package bridge.integration

import bridge.workflow.events.ActionContext

/**
 * Gateway responsible for communicating with the Guardian.
 *
 * The workflow engine depends only on this contract.
 */
interface GuardianGateway {

    /**
     * Starts agent verification.
     *
     * The result will eventually be returned as a workflow event.
     */
    fun verifyAgent(
        workflowId: String,
        requestId: String,
        context: ActionContext
    )
}