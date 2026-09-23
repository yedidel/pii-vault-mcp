package bridge

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertNotNull
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.Test
import java.time.LocalDateTime

class StatusAndFillFormPolicyTest {

    @Test
    fun updatedAtMapsToProtobufTimestamp() {
        val source = LocalDateTime.of(2026, 9, 18, 6, 0, 0)
        val ts = StatusTimestamps.fromLocalDateTime(source)
        assertEquals(source.atZone(java.time.ZoneOffset.UTC).toEpochSecond(), ts.seconds)
    }

    @Test
    fun fillFormRejectsPlaintextSecrets() {
        val error = FillFormParameterPolicy.validate(
            "FILL_FORM",
            mapOf("email" to "a@b.com", "password" to "secret"),
        )
        assertNotNull(error)
    }

    @Test
    fun fillFormAcceptsVaultReferences() {
        val error = FillFormParameterPolicy.validate(
            "FILL_FORM",
            mapOf(
                "email" to "vault://pii/email/token",
                "password" to "vault://pii/password/token",
            ),
        )
        assertNull(error)
    }

    @Test
    fun fillFormAcceptsVaultOwnedFieldHandles() {
        val error = FillFormParameterPolicy.validate(
            "FILL_FORM",
            mapOf(
                "email" to "vault://field/email",
                "password" to "vault://field/password",
            ),
        )
        assertNull(error)
    }

    @Test
    fun grpcPortReadsSystemProperty() {
        val previous = System.getProperty("GRPC_PORT")
        System.setProperty("GRPC_PORT", "51111")
        try {
            if (System.getenv("GRPC_PORT").isNullOrBlank()) {
                assertEquals(51111, grpcListenPort())
            }
        } finally {
            if (previous == null) {
                System.clearProperty("GRPC_PORT")
            } else {
                System.setProperty("GRPC_PORT", previous)
            }
        }
    }
}
