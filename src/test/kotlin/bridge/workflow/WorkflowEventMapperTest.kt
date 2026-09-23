package bridge.workflow

import com.fasterxml.jackson.module.kotlin.jacksonObjectMapper
import org.junit.jupiter.api.Assertions.assertDoesNotThrow
import org.junit.jupiter.api.Assertions.assertThrows
import org.junit.jupiter.api.Test

class WorkflowEventMapperTest {

    private val mapper = WorkflowEventMapper(jacksonObjectMapper().findAndRegisterModules())

    @Test
    fun unknownEventTypeIsRejectedAtDecode() {
        assertThrows(IllegalArgumentException::class.java) {
            mapper.fromJson("""{"eventType":"NOT_A_REAL_EVENT"}""")
        }
    }

    @Test
    fun malformedJsonIsRejectedAtDecode() {
        assertThrows(Exception::class.java) {
            mapper.fromJson("{not-json")
        }
    }

    @Test
    fun leftoverCompletedTypeCanBeDecodedWithoutHandler() {
        val json = """
            {
              "eventType": "WORKFLOW_COMPLETED",
              "eventId": "00000000-0000-0000-0000-000000000001",
              "workflowId": "wf-1",
              "requestId": "req-1",
              "timestamp": "2026-09-18T00:00:00Z",
              "context": {
                "agentId": "agent-123",
                "userInstallId": "install-1",
                "actionType": "PAYMENT",
                "connectorType": "WEBHOOK",
                "connectorContext": "http://127.0.0.1:8000/webhook/bridge",
                "parameters": {}
              }
            }
        """.trimIndent()
        assertDoesNotThrow { mapper.fromJson(json) }
    }
}
