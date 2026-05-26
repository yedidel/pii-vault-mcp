package bridge.service
import bridge.service.ActionStatusChangedEvent
import org.springframework.stereotype.Service

@Service
class ActionEventPublisherService {
    fun publish(event:ActionStatusChangedEvent) {
        println(event)
    }
}
