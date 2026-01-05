import grpc
import bridge_pb2_grpc
import bridge_pb2
class BridgeClient:
    def __init__(self,host="localhost",port=50051):
        self.host=host
        self.port = port
        # its none until connected
        self.channel = None
        # its none until connected because he needs channel
        self.stub = None

    #open connection to the server
    def connect(self):
        #open channel between client and server that all messages will go through
        self.channel=grpc.insecure_channel(f"{self.host}:{self.port}")
        #representation of the server we can use to call its methods
        self.stub = bridge_pb2_grpc.BridgeServiceStub(self.channel)

    #send action to the server
    def send_action(self,agent_id,target_domain,action):
        request=bridge_pb2.ActionRequest(
            agent_id=agent_id,
            target_domain=target_domain,
            action=action
        )
        #call the server method and return its response
        return self.stub.SendAction(request)