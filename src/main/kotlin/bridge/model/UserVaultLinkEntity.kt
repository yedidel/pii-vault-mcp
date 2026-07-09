package bridge.model

import jakarta.persistence.*
import java.time.LocalDateTime

@Entity
@Table(name = "user_vault_links")
class UserVaultLinkEntity(

    @Id
    @Column(name = "user_id", nullable = false, unique = true)
    val userId: String, // The user identifier from the AI agent session

    @Column(name = "vault_did", nullable = false)
    val vaultDid: String, // The permanent DID of the user's paired vault

    @Column(name = "linked_at", nullable = false)
    val linkedAt: LocalDateTime = LocalDateTime.now()
)