package bridge.mapper

import continuation.ConnectorType

/**
 * Maps the proto connector_type string to the domain ConnectorType.
 */
fun String.toConnectorType(): ConnectorType =
    when (this.trim().uppercase()) {
        "POLLING" -> ConnectorType.POLLING
        "CHANNEL" -> ConnectorType.CHANNEL
        "THREAD" -> ConnectorType.THREAD
        "WEBHOOK" -> ConnectorType.WEBHOOK
        "", "CONNECTOR_TYPE_UNSPECIFIED" ->
            error("Connector type is unspecified")
        else ->
            error("Unknown connector type: $this")
    }
