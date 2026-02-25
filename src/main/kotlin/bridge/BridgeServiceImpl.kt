package bridge

import bridge.model.ActionEntity
import bridge.repository.ActionRepository
import java.util.UUID

// הזרקת ה-Repository דרך הקונסטרקטור
class BridgeServiceImpl(private val actionRepository: ActionRepository) : BridgeServiceGrpcKt.BridgeServiceCoroutineImplBase() {

    override suspend fun sendAction(request: Bridge.ActionRequest): Bridge.ActionResponse {
        val requestId = UUID.randomUUID().toString()

        // יצירת האובייקט ושמירה בבסיס הנתונים
        val entity = ActionEntity(
            requestId = requestId,
            agentId = request.agentId,
            userInstallId = request.userInstallId, // הנתון החדש מהפייתון!
            targetDomain = request.targetDomain,
            status = "RECEIVED"
        )

        actionRepository.save(entity) // השמירה בפועל ב-PostgreSQL

        return actionResponse {
            this.requestId = requestId
            this.status = Bridge.StatusType.RECEIVED
        }
    }
}