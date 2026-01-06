import grpc
import bridge_pb2
import bridge_pb2_grpc
from bridge_client import BridgeClient
from openai import OpenAI
import os
from dotenv import load_dotenv
load_dotenv()

client=OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def connect_to_gpt(prompt:str)->str:
    response=client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role":"user","content":prompt}])
    return response.choices[0].message.content


def run_agent():
    agent_prompt = "agent wants to login to their wallet"
    message = connect_to_gpt(agent_prompt)
    print("gpt:")
    print(message)
    with BridgeClient() as bridge:
        response = bridge.send_action(
            agent_id="gpt-agent",
            target_domain="wallet",
            action=bridge_pb2.ActionType.LOGIN
        )
    print("Bridge response:")
    print("request_id:", response.request_id)
    print("status:", response.status)

if __name__ == "__main__":
    run_agent()



#--------basic grpc client example (commented out)--------
# #simple check
# def send_action():
#     #insecure_channel - jast for now local
#     channel = grpc.insecure_channel("localhost:50051")
#     stub = bridge_pb2_grpc.BridgeServiceStub(channel)
#     request = bridge_pb2.ActionRequest(
#         agent_id="agent-001",
#         user_id="user-123",
#         action=bridge_pb2.ActionType.LOGIN,
#         target_domain="example.com"
#     )
#     response = stub.SendAction(request)
#
#     print("Response:")
#     print("request_id:", response.request_id)
#     print("status:", bridge_pb2.StatusType.Name(response.status))
#
#
# if __name__ == "__main__":
#     send_action()
#
