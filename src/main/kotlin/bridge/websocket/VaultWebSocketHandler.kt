package bridge.websocket

import bridge.repository.ActionRepository
import bridge.repository.WorkflowRepository
import bridge.workflow.events.ActionContext
import bridge.workflow.events.ActionResponseReceivedEvent
import bridge.workflow.publisher.WorkflowEventPublisher
import com.fasterxml.jackson.databind.ObjectMapper
import org.json.JSONObject
import org.springframework.stereotype.Component
import org.springframework.web.socket.TextMessage
import org.springframework.web.socket.WebSocketSession
import org.springframework.web.socket.handler.TextWebSocketHandler
import java.util.Base64

@Component
class VaultWebSocketHandler(

    private val workflowRepository: WorkflowRepository,

    private val actionRepository: ActionRepository,

    private val objectMapper: ObjectMapper,

    private val workflowEventPublisher: WorkflowEventPublisher

) : TextWebSocketHandler() {

    private var vaultSession: WebSocketSession? = null

    override fun handleTextMessage(
        session: WebSocketSession,
        message: TextMessage
    ) {
        val payload = JSONObject(message.payload)
        val type = payload.optString("type")
        val requestId = payload.optString("request_id")

        when (type) {

            "connection_init" -> {
                println("--- [BRIDGE] Handshake from Vault: ${payload.optString("did")} ---")
                vaultSession = session
                session.sendMessage(TextMessage("""{"type": "connection_ack"}"""))
            }

            "action_approved" -> {
                println("--- [BRIDGE] Vault approved request: $requestId ---")

                publishVaultResponseEvent(
                    requestId = requestId,
                    responseStatus = "APPROVED",
                    resultData = payload.optString(
                        "result_data",
                        "Vault approved action"
                    )
                )
            }

            "action_rejected" -> {
                println("--- [BRIDGE] Vault rejected request: $requestId ---")

                publishVaultResponseEvent(
                    requestId = requestId,
                    responseStatus = "REJECTED",
                    resultData = payload.optString(
                        "reason",
                        "Vault rejected action"
                    )
                )
            }
        }
    }

    fun sendRequestToVault(
        amount: String,
        currency: String,
        requestId: String
    ) {
        if (vaultSession == null || !vaultSession!!.isOpen) {

            println("--- [ERROR] No active Vault connection ---")

            publishVaultResponseEvent(
                requestId = requestId,
                responseStatus = "FAILED",
                resultData = "No active Vault connection"
            )

            return
        }

        val rawMessage =
            "amount=$amount;currency=$currency;timestamp=${System.currentTimeMillis()}"

        val encodedData =
            Base64.getEncoder().encodeToString(rawMessage.toByteArray())

        val request = JSONObject()
        request.put("type", "payment_request")
        request.put("request_id", requestId)
        request.put("data", encodedData)

        vaultSession?.sendMessage(TextMessage(request.toString()))

        println("--- [BRIDGE] Sent encrypted payload to Vault for ID: $requestId ---")
    }

    fun sendFormFillRequestToVault(
        requestId: String,
        formUrl: String,
        fields: Map<String, String>,
    ) {
        if (vaultSession == null || !vaultSession!!.isOpen) {

            println("--- [ERROR] No active Vault connection ---")

            publishVaultResponseEvent(
                requestId = requestId,
                responseStatus = "FAILED",
                resultData = "No active Vault connection"
            )

            return
        }

        val request = JSONObject()
        request.put("type", "form_fill_request")
        request.put("request_id", requestId)
        request.put("form_url", formUrl)

        val fieldsJson = JSONObject()
        fields.forEach { (key, value) -> fieldsJson.put(key, value) }
        request.put("fields", fieldsJson)

        vaultSession?.sendMessage(TextMessage(request.toString()))

        println(
            "--- [BRIDGE] Sent form_fill_request to Vault for ID: $requestId " +
                "formUrl=$formUrl ---"
        )
    }

    private fun publishVaultResponseEvent(
        requestId: String,
        responseStatus: String,
        resultData: String?
    ) {

        val workflow = workflowRepository.findByRequestId(requestId)

        if (workflow == null) {
            println("--- [WORKFLOW ERROR] No workflow found for requestId: $requestId ---")
            return
        }

        val action = actionRepository.findById(requestId).orElse(null)

        if (action == null) {
            println("--- [WORKFLOW ERROR] No action found for requestId: $requestId ---")
            return
        }

        val parameters =
            if (action.parametersJson == null) {
                emptyMap()
            } else {
                objectMapper.readValue(
                    action.parametersJson,
                    Map::class.java
                ) as Map<String, String>
            }

        val context = ActionContext(
            agentId = action.agentId,
            userInstallId = action.userInstallId,
            actionType = action.actionType,
            connectorType = workflow.connectorType,
            connectorContext = workflow.connectorContext,
            parameters = parameters,
        )

        workflowEventPublisher.publish(
            ActionResponseReceivedEvent(
                workflowId = workflow.workflowId,
                requestId = requestId,
                responseStatus = responseStatus,
                resultData = resultData,
                context = context,
            )
        )
    }
}