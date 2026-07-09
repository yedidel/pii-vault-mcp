package bridge

import bridge.Bridge.ActionResponse
import bridge.Bridge.StatusResponse
import bridge.Bridge.StatusType
import org.springframework.stereotype.Service
import bridge.workflow.WorkflowInitializationService
import bridge.repository.UserVaultLinkRepository
import bridge.service.PairingService
import com.fasterxml.jackson.databind.ObjectMapper
import org.springframework.boot.autoconfigure.transaction.TransactionManagerCustomizers

/**
 * BridgeServiceImpl
 * * This class serves as the central orchestrator for the PII Vault Ecosystem.
 * It manages the communication between gRPC clients (Agents), the Database,
 * the Guardian (Reputation Service), and the Vault (User Authorization Service).
 */
@Service
class BridgeServiceImpl(
    private val actionService: ActionService,
    private val workflowInitializationService: WorkflowInitializationService,
    private val objectMapper: ObjectMapper,
    // Injecting the new pairing infrastructure components
    private val userVaultLinkRepository: UserVaultLinkRepository,
    private val pairingService: PairingService,
    private val platform: TransactionManagerCustomizers
) : BridgeServiceGrpcKt.BridgeServiceCoroutineImplBase() {


    /**
     * Orchestrates the initial action intake.
     * The workflow engine (event-driven) orchestrates the rest.
     *
     * Steps:
     * 0. Identity Routing: Check if the user has a paired vault. If not, trigger pairing flow.
     * 1. Validate agent with Guardian
     * 2. Persist action
     * 3. Initialize workflow and publish ActionCreatedEvent
     * 4. Return immediately (workflow engine handles the rest)
     */
    override suspend fun sendAction(request: Bridge.ActionRequest): ActionResponse {
        println("--- [BRIDGE] Processing ${request.actionType} for agent ${request.agentId} ---")

        // STEP 0: Identity Routing & Vault Pairing Check
        // Using userInstallId from the Proto request to identify the specific user/device setup
        val userId = request.userInstallId
        val existingLink = userVaultLinkRepository.findByUserId(userId)

        if (existingLink.isEmpty) {
            println("--- [BRIDGE] No vault paired for user: $userId. Initiating pairing flow. ---")

            // Generate temporary pairing token and dynamic QR code URL
            val pairingData = pairingService.initiatePairing(userId)

            // Return FAILED_APP_NOT_INSTALLED as defined in Proto, packing QR data inside the description
            return ActionResponse.newBuilder()
                .setStatus(StatusType.FAILED_APP_NOT_INSTALLED)
                .setDescription("PAIRING_REQUIRED|${pairingData.qrCodeUrl}|${pairingData.pairingToken}")
                .build()
        }

        // Fetch the permanent vault DID for routing down the line
        val vaultDid = existingLink.get().vaultDid
        println("--- [BRIDGE] User $userId is paired with Vault DID: $vaultDid. Proceeding to safety layer. ---")


        // ==========================================
        // EXISTING UNTOUCHED CORE WORKFLOW LOGIC
        // ==========================================

        // STEP 1: Guardian Reputation Check & Action Persistence
        val responseEntity = try {
            actionService.handleAction(request)
        } catch (e: Exception) {
            println("--- [BRIDGE] Action rejected by safety protocols: ${e.message} ---")
            return ActionResponse.newBuilder()
                .setStatus(StatusType.FAILED)
                .setDescription("Action rejected by bridge safety layer: ${e.message}")
                .build()
        }

        val requestId = responseEntity.requestId

        // STEP 2: Initialize Workflow
        val parameters = objectMapper.convertValue(request.parametersMap, Map::class.java) as Map<String, String>

        workflowInitializationService.initializeWorkflow(
            requestId = requestId,
            agentId = request.agentId,
            userInstallId = request.userInstallId,
            actionType = request.actionType,
            platform = request.platform,
            sessionId = request.sessionId,
            parameters = parameters
        )

        // STEP 3: Return initial response to agent
        return ActionResponse.newBuilder()
            .setRequestId(requestId)
            .setStatus(StatusType.RECEIVED)
            .setDescription("Action received and workflow initiated. Use GetActionStatus to poll for completion.")
            .build()
    }


    /**
     * Queries the database for the current status of a specific action.
     */
    override suspend fun getActionStatus(request: Bridge.StatusRequest): StatusResponse {
        val action = actionService.getActionById(request.requestId)
        return StatusResponse.newBuilder()
            .setRequestId(action.requestId)
            .setStatus(action.status)
            .build()
    }
}