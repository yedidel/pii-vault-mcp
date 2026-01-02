package bridge

import io.grpc.ServerBuilder

fun main() {
    val server = ServerBuilder
        .forPort(50051)
        .addService(BridgeServiceImpl())
        .build()

    server.start()
    println("gRPC server started on port 50051")

    server.awaitTermination()
}
