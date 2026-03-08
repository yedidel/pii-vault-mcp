import bridge_pb2
from models import ActionRequestModel

# Mapper function to convert ActionRequestModel to ActionRequest protobuf message
def map_to_proto(model: ActionRequestModel):

    proto = bridge_pb2.ActionRequest()

    proto.agent_id = model.agentId
    proto.user_install_id = model.userInstallId
    proto.action_type = model.actionType

    for key, value in model.parameters.items():
        proto.parameters[key] = value

    return proto