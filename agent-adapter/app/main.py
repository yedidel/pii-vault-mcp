import os

import grpc
from bridge import bridge_pb2, bridge_pb2_grpc
from workflow.models import ActionRequestModel
from mapper import map_to_proto

# Insecure localhost gRPC is a prototype limitation, not production TLS.
_GRPC_TARGET = os.getenv("BRIDGE_GRPC_TARGET", "localhost:50051").strip() or "localhost:50051"
channel = grpc.insecure_channel(_GRPC_TARGET)
stub = bridge_pb2_grpc.BridgeServiceStub(channel)

def send_action(action_request: ActionRequestModel):
    proto_request = map_to_proto(action_request)

    try:
        response = stub.SendAction(proto_request)
    except grpc.RpcError as error:
        details = error.details() or ""
        raise RuntimeError(
            f"gRPC error code={error.code().name} details={details!r}"
        ) from error

    return {
        "requestId": response.request_id,
        "workflowId": response.workflow_id,
        "status": bridge_pb2.StatusType.Name(response.status),
        "description": response.description
    }

def get_status(request_id: str):

    status_request= bridge_pb2.StatusRequest(request_id=request_id)
    try:
        response = stub.GetActionStatus(status_request)
    except grpc.RpcError as e:
        raise Exception(f"gRPC error: {e.details()}")

    status_name= bridge_pb2.StatusType.Name(response.status)
    payload = {
        "requestId": response.request_id,
        "status": status_name,
        "resultData": response.result_data
    }
    if response.HasField("updated_at"):
        payload["updatedAt"] = response.updated_at.ToJsonString()
    return payload


def evaluate_policy(
        *,
        agent_id: str,
        user_install_id: str,
        action_type: str,
        field_names: list[str],
):
    request = bridge_pb2.PolicyEvaluationRequest(
        agent_id=agent_id,
        user_install_id=user_install_id,
        action_type=action_type,
        field_names=list(field_names),
    )
    try:
        response = stub.EvaluatePolicy(request)
    except grpc.RpcError as error:
        details = error.details() or ""
        raise RuntimeError(
            f"POLICY_ERROR code={error.code().name} details={details!r}"
        ) from error

    return {
        "policyRequestId": response.policy_request_id,
        "actionType": response.action_type,
        "decision": response.decision,
        "agentAllowed": list(response.agent_allowed),
        "vaultRequired": list(response.vault_required),
        "userApprovalRequired": bool(response.user_approval_required),
    }
