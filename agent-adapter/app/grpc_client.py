import grpc
import bridge_pb2
import bridge_pb2_grpc

#simple check
def send_action():
    #insecure_channel - jast for now local
    channel = grpc.insecure_channel("localhost:50051")
    stub = bridge_pb2_grpc.BridgeServiceStub(channel)
    request = bridge_pb2.ActionRequest(
        agent_id="agent-001",
        user_id="user-123",
        action=bridge_pb2.ActionType.LOGIN,
        target_domain="example.com"
    )
    response = stub.SendAction(request)

    print("Response:")
    print("request_id:", response.request_id)
    print("status:", bridge_pb2.StatusType.Name(response.status))


if __name__ == "__main__":
    send_action()

