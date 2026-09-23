package bridge.websocket

import bridge.policy.PolicyErrorCode
import bridge.policy.PolicyEvaluationService
import bridge.policy.PolicyPendingRegistry
import bridge.policy.PolicyQueryError
import bridge.policy.VaultPolicyReply
import bridge.repository.ActionRepository
import bridge.repository.WorkflowRepository
import bridge.workflow.events.ActionContext
import bridge.workflow.events.ActionResponseReceivedEvent
import bridge.workflow.publisher.WorkflowEventPublisher
import com.fasterxml.jackson.databind.ObjectMapper
import org.json.JSONArray
import org.json.JSONObject
import org.springframework.stereotype.Component
import org.springframework.web.socket.CloseStatus
import org.springframework.web.socket.TextMessage
import org.springframework.web.socket.WebSocketSession
import org.springframework.web.socket.handler.TextWebSocketHandler
import java.util.Base64

@Component
class VaultWebSocketHandler(

    private val workflowRepository: WorkflowRepository,

    private val actionRepository: ActionRepository,

    private val objectMapper: ObjectMapper,

    private val workflowEventPublisher: WorkflowEventPublisher,

    private val policyPendingRegistry: PolicyPendingRegistry,

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

            "policy_evaluation_response" -> {
                handlePolicyEvaluationResponse(payload)
            }
        }
    }

    override fun afterConnectionClosed(
        session: WebSocketSession,
        status: CloseStatus,
    ) {
        if (session === vaultSession) {
            vaultSession = null
            policyPendingRegistry.failAll(
                PolicyQueryError(
                    PolicyErrorCode.VAULT_DISCONNECTED,
                    "Vault disconnected",
                ),
            )
            println("--- [BRIDGE] Vault WebSocket closed ---")
        }
    }

    fun hasActiveVaultSession(): Boolean {
        val session = vaultSession
        return session != null && session.isOpen
    }

    fun sendPolicyEvaluationRequest(
        policyRequestId: String,
        userInstallId: String,
        agentId: String,
        actionType: String,
        fieldNames: List<String>,
    ): Boolean {
        if (!hasActiveVaultSession()) {
            println("--- [ERROR] No active Vault connection for policy query ---")
            return false
        }

        val request = JSONObject()
        request.put("type", "policy_evaluation_request")
        request.put("policy_request_id", policyRequestId)
        request.put("user_install_id", userInstallId)
        request.put("agent_id", agentId)
        request.put("action_type", actionType)
        val fields = JSONArray()
        fieldNames.forEach { fields.put(it) }
        request.put("field_names", fields)

        vaultSession?.sendMessage(TextMessage(request.toString()))
        println(
            "--- [BRIDGE] Sent policy_evaluation_request " +
                "id=$policyRequestId action=$actionType ---"
        )
        return true
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

        println("--- [BRIDGE] Sent Base64-encoded payload to Vault for ID: $requestId ---")
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

    private fun handlePolicyEvaluationResponse(payload: JSONObject) {
        val policyRequestId = payload.optString("policy_request_id").trim()
        if (policyRequestId.isEmpty()) {
            println("--- [BRIDGE] Ignoring policy response without policy_request_id ---")
            return
        }

        val ok = payload.optBoolean("ok", payload.has("decision"))
        if (!ok) {
            val code = parsePolicyErrorCode(payload.optString("error_code"))
            val message = payload.optString("error").ifBlank {
                "Vault policy evaluation failed"
            }
            val accepted = policyPendingRegistry.complete(
                policyRequestId,
                VaultPolicyReply.Failure(PolicyQueryError(code, message)),
            )
            if (!accepted) {
                println(
                    "--- [BRIDGE] Ignoring late/duplicate policy failure " +
                        "id=$policyRequestId ---"
                )
            }
            return
        }

        val decision = payload.optString("decision").trim().uppercase()
        if (!PolicyEvaluationService.ALLOWED_DECISIONS.contains(decision)) {
            policyPendingRegistry.complete(
                policyRequestId,
                VaultPolicyReply.Failure(
                    PolicyQueryError(
                        PolicyErrorCode.MALFORMED_POLICY,
                        "Vault returned invalid policy decision",
                    ),
                ),
            )
            return
        }

        val accepted = policyPendingRegistry.complete(
            policyRequestId,
            VaultPolicyReply.Success(
                policyRequestId = policyRequestId,
                actionType = payload.optString("action_type").trim(),
                decision = decision,
                agentAllowed = stringList(payload.optJSONArray("agent_allowed")),
                vaultRequired = stringList(payload.optJSONArray("vault_required")),
                userApprovalRequired = payload.optBoolean("user_approval_required", false),
            ),
        )
        if (!accepted) {
            println(
                "--- [BRIDGE] Ignoring late/duplicate policy response " +
                    "id=$policyRequestId ---"
            )
        }
    }

    private fun parsePolicyErrorCode(raw: String): PolicyErrorCode {
        return when (raw.trim().uppercase()) {
            "VAULT_DISCONNECTED" -> PolicyErrorCode.VAULT_DISCONNECTED
            "TIMEOUT" -> PolicyErrorCode.TIMEOUT
            "MALFORMED_POLICY" -> PolicyErrorCode.MALFORMED_POLICY
            "INVALID_USER_INSTALL" -> PolicyErrorCode.INVALID_USER_INSTALL
            "INVALID_REQUEST" -> PolicyErrorCode.INVALID_REQUEST
            "UNKNOWN_ACTION" -> PolicyErrorCode.UNKNOWN_ACTION
            else -> PolicyErrorCode.INTERNAL
        }
    }

    private fun stringList(array: JSONArray?): List<String> {
        if (array == null) return emptyList()
        return (0 until array.length())
            .map { array.optString(it).trim() }
            .filter { it.isNotEmpty() }
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
