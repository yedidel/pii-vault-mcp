import grpc
import bridge_pb2
import bridge_pb2_grpc

def send_action():
    channel = grpc.insecure_channel("localhost:50051")
    stub = bridge_pb2_grpc.BridgeServiceStub(channel)

    request = bridge_pb2.ActionRequest(
        agent_id="some_agent",
        user_id="some_user_id",
        action_metadata="test payment metadata"
    )

    response = stub.SendAction(request)

    print("Response:")
    print("request_id:", response.request_id)
    print("status:", bridge_pb2.StatusType.Name(response.status))


if __name__ == "__main__":
    send_action()