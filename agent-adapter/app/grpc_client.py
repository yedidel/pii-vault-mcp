import grpc
import bridge_pb2
import bridge_pb2_grpc

def send_action():
    # Initialize the gRPC channel to the Kotlin server
    with grpc.insecure_channel("localhost:50051") as channel:
        # Create a stub (client) for the BridgeService
        stub = bridge_pb2_grpc.BridgeServiceStub(channel)

        # Prepare the request payload with relevant metadata
        request = bridge_pb2.ActionRequest(
            agent_id="some_agent",
            user_install_id="device_123",
            action_type="PAYMENT",
            parameters={
                "amount": "100",
                "currency": "USD"
            }

        )

        try:
            # Execute the remote procedure call (RPC)
            response = stub.SendAction(request)

            # Print server response details
            print(f"Server Response: {response.description}")
            print(f"Generated Request ID: {response.request_id}")
            print(f"Status: {bridge_pb2.StatusType.Name(response.status)}")

        except grpc.RpcError as e:
            # Handle potential communication errors (e.g., server offline)
            print(f"RPC failed: {e.code()} - {e.details()}")

if __name__ == "__main__":
    send_action()