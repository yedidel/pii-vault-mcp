import grpc
from models import ActionRequestModel
from mapper import map_to_proto
import bridge_pb2_grpc

def send_action(action_request: ActionRequestModel):
    # map the ActionRequestModel to a protobuf message
    proto_request = map_to_proto(action_request)

    # create a gRPC channel to communicate with the Bridge server.
    # currently the channel is insecure and connects to localhost:50051.
    # in production this should be replaced with a secure channel
    # and the actual address of the Bridge server.
    channel = grpc.insecure_channel('localhost:50051')
    # The stub is a client object that allows us to call the RPC methods
    # defined in BridgeService (generated from the protobuf definition).
    stub = bridge_pb2_grpc.BridgeServiceStub(channel)

    # Send the action request to the Bridge server and get the response
    response = stub.SendAction(proto_request)

    print("received response from Bridge server:")
    print(response)
    return response