package bridge.transport

import org.springframework.stereotype.Component

@Component
class AgentTransportRegistry(

    transports: List<AgentTransport>

) {

    private val transportsByType =
        transports.associateBy { it.type }

    fun send(
        transport: TransportType,
        requestId: String,
        message: String
    ) {

        val selectedTransport =
            transportsByType[transport]
                ?: error("No transport registered for $transport")

        selectedTransport.send(
            requestId = requestId,
            message = message
        )
    }
}