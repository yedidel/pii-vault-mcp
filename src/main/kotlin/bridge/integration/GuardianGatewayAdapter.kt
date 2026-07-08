package bridge.integration

import bridge.workflow.events.ActionContext
import bridge.workflow.events.GuardianApprovedEvent
import bridge.workflow.events.GuardianRejectedEvent
import bridge.workflow.publisher.WorkflowEventPublisher
import org.slf4j.LoggerFactory
import org.springframework.stereotype.Component
import org.springframework.web.client.RestTemplate

@Component
class GuardianGatewayAdapter(

    private val restTemplate: RestTemplate,

    private val workflowEventPublisher: WorkflowEventPublisher

) : GuardianGateway {

    private val logger = LoggerFactory.getLogger(javaClass)

    private val guardianAuthUrl =
        "http://localhost:8001/v1/authenticate/agent?did="

    private val guardianReportUrl =
        "http://localhost:8001/v1/report"

    override fun verifyAgent(
        workflowId: String,
        requestId: String,
        context: ActionContext
    ) {
        val agentId = context.agentId

        try {
            logger.debug("Verifying agent $agentId with Guardian")

            val auth = restTemplate.getForObject(
                "$guardianAuthUrl$agentId",
                AuthResponse::class.java
            )

            if (auth?.status == "verified") {
                logger.info("Agent $agentId verified by Guardian")

                workflowEventPublisher.publish(
                    GuardianApprovedEvent(
                        workflowId = workflowId,
                        requestId = requestId,
                        context = context,
                        trustLevel = auth.trust_level
                    )
                )
            } else {
                logger.warn("Agent $agentId rejected by Guardian")

                workflowEventPublisher.publish(
                    GuardianRejectedEvent(
                        workflowId = workflowId,
                        requestId = requestId,
                        context = context,
                        reason = "Agent not verified"
                    )
                )
            }

        } catch (e: Exception) {
            logger.error("Failed to verify agent $agentId with Guardian", e)

            workflowEventPublisher.publish(
                GuardianRejectedEvent(
                    workflowId = workflowId,
                    requestId = requestId,
                    context = context,
                    reason = e.message ?: "Guardian unavailable"
                )
            )
        }
    }

    fun verifyAgentSync(agentId: String): Boolean {
        return try {
            val auth = restTemplate.getForObject(
                "$guardianAuthUrl$agentId",
                AuthResponse::class.java
            )

            auth?.status == "verified"
        } catch (_: Exception) {
            false
        }
    }

    fun reportOutcome(
        requestId: String,
        domain: String,
        result: String
    ) {
        val payload = mapOf(
            "domain" to domain,
            "result" to result,
            "requestId" to requestId
        )

        restTemplate.postForObject(
            guardianReportUrl,
            payload,
            Map::class.java
        )
    }
}

data class AuthResponse(
    val status: String = "unauthorized",
    val trust_level: String = "none"
)