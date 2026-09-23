package bridge
import io.grpc.ServerBuilder
import org.springframework.boot.autoconfigure.SpringBootApplication
import org.springframework.boot.runApplication
import org.springframework.scheduling.annotation.EnableScheduling

@SpringBootApplication(
scanBasePackages = [
"bridge",
"connectors",
"continuation"
]
)
@EnableScheduling
class BridgeServerApplication

fun grpcListenPort(): Int {
    val raw = System.getenv("GRPC_PORT") ?: System.getProperty("GRPC_PORT")
    return raw?.toIntOrNull() ?: 50051
}

fun main() {
    EnvLoader.loadFromRepoEnvFile()

    // Starts Spring Boot and initializes DB connection to PostgreSQL (Docker)
    // context contains all Spring beans, including DB connection and repositories
    val context = runApplication<BridgeServerApplication>()
    // Get the BridgeServiceImpl bean created and managed by Spring
    val bridgeService = context.getBean(BridgeServiceImpl::class.java)
    val port = grpcListenPort()
    val server =
        ServerBuilder
            .forPort(port)
            .addService(bridgeService)
            .build()

    server.start()
    println("gRPC server started on port $port")
    server.awaitTermination()
}