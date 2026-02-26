package bridge
import bridge.repository.ActionRepository
import org.springframework.boot.autoconfigure.SpringBootApplication
import org.springframework.boot.runApplication
import org.springframework.context.ConfigurableApplicationContext
import io.grpc.ServerBuilder

@SpringBootApplication
class BridgeServerApplication

fun main() {
    // Starts Spring Boot and initializes DB connection to PostgreSQL (Docker)
    // context contains all Spring beans, including DB connection and repositories
    val context = runApplication<BridgeServerApplication>()
    //object that connect to db
    val actionRepository = context.getBean(ActionRepository::class.java)
    val server = ServerBuilder
        .forPort(50051)
        .addService(BridgeServiceImpl(actionRepository))
        .build()

    server.start()
    println("gRPC server started on port 50051")
    server.awaitTermination()
}