import grpc
from bridge import bridge_pb2, bridge_pb2_grpc
from workflow.models import ActionRequestModel
from mapper import map_to_proto

# create a gRPC channel to communicate with the Bridge server.
# currently the channel is insecure and connects to localhost:50051.
# in production this should be replaced with a secure channel
# and the actual address of the Bridge server.
channel = grpc.insecure_channel('localhost:50051')
# The stub is a client object that allows us to call the RPC methods
# defined in BridgeService (generated from the protobuf definition).
stub = bridge_pb2_grpc.BridgeServiceStub(channel)

def send_action(action_request: ActionRequestModel):
    # map the ActionRequestModel to a protobuf message
    proto_request = map_to_proto(action_request)

    # Send the action request to the Bridge server and get the response
    try:
        response = stub.SendAction(proto_request)
    except grpc.RpcError as e:
        raise Exception(f"gRPC error: ",e)

    return {
        "requestId": response.request_id,
        "workflowId": response.workflow_id,
        "status": bridge_pb2.StatusType.Name(response.status),
        "description": response.description
    }

def get_status(request_id: str):

    status_request= bridge_pb2.StatusRequest(request_id=request_id)
    # Send the get status request to the Bridge server and get the response
    try:
        response = stub.GetActionStatus(status_request)
    except grpc.RpcError as e:
        raise Exception(f"gRPC error: {e.details()}")

    # convert protobuf enum to readable string
    status_name= bridge_pb2.StatusType.Name(response.status)
    return {
        "requestId": response.request_id,
        "status": status_name,
        "resultData": response.result_data
    }