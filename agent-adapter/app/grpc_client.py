import grpc
import bridge_pb2
import bridge_pb2_grpc

#simple check
def send_action():
    #insecure_channel - jast for now local
    channel = grpc.insecure_channel("localhost:50051")
    stub = bridge_pb2_grpc.BridgeServiceStub(channel)
    # חפשי את השורה הזו ושני את user_id ל-user_install_id
    request = bridge_pb2.ActionRequest(
        agent_id="some_agent",
        user_install_id="some_user_id",  # <--- זה השינוי!
        action=bridge_pb2.LOGIN,
        target_domain="example.com"
    )
    response = stub.SendAction(request)

    print("Response:")
    print("request_id:", response.request_id)
    print("status:", bridge_pb2.StatusType.Name(response.status))


if __name__ == "__main__":
    send_action()

