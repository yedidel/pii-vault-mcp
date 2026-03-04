package bridge

import bridge.model.ActionEntity
import bridge.repository.ActionRepository
import java.util.UUID
import org.springframework.stereotype.Service

@Service
class BridgeServiceImpl(
    private val actionRepository: ActionRepository,
    private val actionProducer: ActionProducer
) : BridgeServiceGrpcKt.BridgeServiceCoroutineImplBase() {

    override suspend fun sendAction(request: Bridge.ActionRequest): Bridge.ActionResponse {
        // יצירת מזהה ייחודי לבקשה
        val requestId = UUID.randomUUID().toString()

        try {
            // 1. שמירה בבסיס הנתונים (PostgreSQL)
            val entity = ActionEntity(
                requestId = requestId,
                agentId = request.agentId,
                userInstallId = request.userInstallId,
                targetDomain = request.targetDomain,
                status = "RECEIVED"
            )
            actionRepository.save(entity)
            println("✅ DB: Action saved for Agent ${request.userInstallId}")

            // 2. שליחה למערכת הכריזה (Kafka)
            // שולחים את המזהה ואת הדומיין אליו הסוכן פנה
            actionProducer.sendActionToKafka(request.userInstallId, request.targetDomain)

            // 3. החזרת תשובה חיובית לסוכן
            return Bridge.ActionResponse.newBuilder()
                .setRequestId(requestId)
                .setStatus(Bridge.StatusType.RECEIVED)
                .build()

        } catch (e: Exception) {
            // טיפול בשגיאות - הדפסה למסך והחזרת תשובה בסיסית כדי לא לשבור את הסוכן
            println("❌ Error in BridgeService: ${e.message}")

            return Bridge.ActionResponse.newBuilder()
                .setRequestId(requestId)
                .setStatus(Bridge.StatusType.RECEIVED)
                .build()
        }
    }
}