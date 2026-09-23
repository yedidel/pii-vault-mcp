from bridge import bridge_pb2
from workflow.models import ActionRequestModel

# Mapper function to convert ActionRequestModel to ActionRequest protobuf message
def map_to_proto(model: ActionRequestModel):

    proto = bridge_pb2.ActionRequest()

    proto.agent_id = model.agentId
    proto.user_install_id = model.userInstallId
    proto.action_type = model.actionType
    proto.connector_type = model.connectorType
    proto.connector_context = model.connectorContext

    for key, value in model.parameters.items():
        proto.parameters[key] = value

    return proto