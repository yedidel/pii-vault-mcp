package bridge
import bridge.Bridge.StatusType
import org.springframework.stereotype.Service
import bridge.service.ActionStatusChangedEvent

@Service
class ActionEventService {

    private val agentReportale=setOf(
        StatusType.REJECTED,
        StatusType.COMPLETED,
        StatusType.FAILED,
        StatusType.FAILED_APP_NOT_INSTALLED
    )

    fun checkIfChange(requestId: String,old_satatus:StatusType,new_satatus:StatusType): ActionStatusChangedEvent? {
        if(old_satatus == new_satatus){
            return null
        }
        if(new_satatus in agentReportale) {
            return ActionStatusChangedEvent(
                requestId,
                old_satatus,
                new_satatus
            )
        }
        return null
    }



}