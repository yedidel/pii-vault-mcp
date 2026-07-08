package bridge.config

import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Configuration
import org.springframework.kafka.listener.DefaultErrorHandler
import org.springframework.util.backoff.FixedBackOff

@Configuration
class KafkaRetryConfig {

    @Bean
    fun kafkaErrorHandler(): DefaultErrorHandler {

        return DefaultErrorHandler(

            // Wait 2 seconds between retries.
            // Retry twice after the initial failure
            // (3 processing attempts in total).
            FixedBackOff(
                2000L,
                2L
            )
        )
    }
}