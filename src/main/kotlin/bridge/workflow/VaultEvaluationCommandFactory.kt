package bridge.workflow

import bridge.workflow.events.ActionContext

object VaultEvaluationCommandFactory {

    private const val DEFAULT_DEMO_FORM_URL = "http://127.0.0.1:9000/register"

    fun fromContext(
        workflowId: String,
        requestId: String,
        context: ActionContext,
    ): RequestVaultEvaluationCommand {
        val actionType = context.actionType.uppercase()
        val parameters = context.parameters

        return when (actionType) {
            "FILL_FORM" -> {
                val formUrl = parameters["formUrl"]?.trim().takeUnless { it.isNullOrEmpty() }
                    ?: DEFAULT_DEMO_FORM_URL
                val fields = parameters.filterKeys { key ->
                    key != "formUrl"
                }

                RequestVaultEvaluationCommand(
                    workflowId = workflowId,
                    requestId = requestId,
                    actionType = actionType,
                    formUrl = formUrl,
                    fields = fields,
                )
            }

            else -> RequestVaultEvaluationCommand(
                workflowId = workflowId,
                requestId = requestId,
                actionType = actionType,
                amount = parameters["amount"] ?: "",
                currency = parameters["currency"] ?: "",
            )
        }
    }
}
