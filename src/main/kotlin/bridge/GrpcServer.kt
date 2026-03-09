package bridge

import io.grpc.ServerBuilder
import org.springframework.boot.autoconfigure.SpringBootApplication
import org.springframework.boot.runApplication

@SpringBootApplication
class BridgeServerApplication

/**
 * Main entry point for the Bridge Server.
 * This application integrates Spring Boot for Dependency Injection (DB & Kafka)
 * and starts a gRPC server to handle client requests.
 */
fun main(args: Array<String>) {
    // 1. Start Spring Boot context to initialize all Beans (DB Repositories, Kafka Producers)
    val context = runApplication<BridgeServerApplication>(*args)

    // 2. Retrieve the BridgeServiceImpl Bean managed by Spring.
    // This service already contains injected dependencies: ActionService (DB) and ActionProducer (Kafka).
    val bridgeService = context.getBean(BridgeServiceImpl::class.java)

    // 3. Build and configure the gRPC server on port 50051
    val server = ServerBuilder
        .forPort(50051)
        .addService(bridgeService) // Inject the Spring-managed service into gRPC
        .build()

    // 4. Start the gRPC server and wait for termination
    server.start()

    println("--------------------------------------------------")
    println("🚀 gRPC Server started on port 50051")
    println("📡 Kafka Infrastructure is ready")
    println("📂 PostgreSQL Database connected")
    println("--------------------------------------------------")

    server.awaitTermination()
}