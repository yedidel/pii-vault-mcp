import grpc
from bridge import bridge_pb2, bridge_pb2_grpc


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
        request= bridge_pb2.ActionRequest(
            agent_id=agent_id,
            target_domain=target_domain,
            action=action
        )
        #call the server method and return its response
        return self.stub.SendAction(request)

    #close the connection to the server
    def close(self):
        if self.channel is not None:
            self.channel.close()
            #to prevent using closed channel
            self.channel = None
            self.stub = None


    #context manager methods

    #enter method to open connection
    def __enter__(self):
        self.connect()
        return self

    #exit method to close connection without return value to pass the error as usual for now
    def __exit__(self,exc_type, exc_value, traceback):
        self.close()
