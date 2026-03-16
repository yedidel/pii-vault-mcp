package bridge
import io.grpc.ServerBuilder
import org.springframework.boot.autoconfigure.SpringBootApplication
import org.springframework.boot.runApplication

@SpringBootApplication
class BridgeServerApplication

fun main() {
    // Starts Spring Boot and initializes DB connection to PostgreSQL (Docker)
    // context contains all Spring beans, including DB connection and repositories
    val context = runApplication<BridgeServerApplication>()
    // Get the BridgeServiceImpl bean created and managed by Spring
    val bridgeService = context.getBean(BridgeServiceImpl::class.java)
    val server =
        ServerBuilder
            .forPort(50051)
            .addService(bridgeService)
            .build()

    server.start()
    println("gRPC server started on port 50051")
    server.awaitTermination()
}