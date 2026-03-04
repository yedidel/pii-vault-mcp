package bridge

import bridge.repository.ActionRepository
import org.springframework.boot.autoconfigure.SpringBootApplication
import org.springframework.boot.runApplication
import org.springframework.context.ConfigurableApplicationContext
import io.grpc.ServerBuilder

@SpringBootApplication
class BridgeServerApplication

fun main(args: Array<String>) {
    val context = runApplication<BridgeServerApplication>(*args)
    val actionRepository = context.getBean(ActionRepository::class.java)
    val actionProducer = context.getBean(ActionProducer::class.java)

    val server = ServerBuilder
        .forPort(50051)
        .addService(BridgeServiceImpl(actionRepository,actionProducer)) // עכשיו אנחנו מעבירים לו את ה-Bean
        .build()

    server.start()
    println("gRPC server started on port 50051")
    server.awaitTermination()
}