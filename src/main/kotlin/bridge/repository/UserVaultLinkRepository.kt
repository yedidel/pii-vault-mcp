package bridge.repository

import bridge.model.UserVaultLinkEntity
import org.springframework.data.jpa.repository.JpaRepository
import org.springframework.stereotype.Repository
import java.util.Optional

@Repository
interface UserVaultLinkRepository : JpaRepository<UserVaultLinkEntity, String> {

    // Find permanent pairing by the unique userId
    fun findByUserId(userId: String): Optional<UserVaultLinkEntity>
}