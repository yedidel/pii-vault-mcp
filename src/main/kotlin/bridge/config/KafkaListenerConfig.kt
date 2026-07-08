package bridge.config

import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Configuration
import org.springframework.kafka.config.ConcurrentKafkaListenerContainerFactory
import org.springframework.kafka.core.ConsumerFactory
import org.springframework.kafka.listener.DefaultErrorHandler

@Configuration
class KafkaListenerConfig {

    @Bean
    fun kafkaListenerContainerFactory(
        consumerFactory: ConsumerFactory<String, String>,
        errorHandler: DefaultErrorHandler
    ): ConcurrentKafkaListenerContainerFactory<String, String> {

        val factory =
            ConcurrentKafkaListenerContainerFactory<String, String>()

        factory.consumerFactory = consumerFactory

        // Retry failed Kafka messages using our configured policy.
        factory.setCommonErrorHandler(errorHandler)

        return factory
    }
}