package bridge

import com.google.protobuf.Timestamp
import java.time.LocalDateTime
import java.time.ZoneOffset

object StatusTimestamps {

    fun fromLocalDateTime(value: LocalDateTime): Timestamp {
        val instant = value.atZone(ZoneOffset.UTC).toInstant()
        return Timestamp.newBuilder()
            .setSeconds(instant.epochSecond)
            .setNanos(instant.nano)
            .build()
    }
}
