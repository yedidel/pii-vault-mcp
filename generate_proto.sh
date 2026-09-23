#generate the gRPC files for Python every time we build the proto files.
#run in terminal ./generate_proto.sh
#!/bin/bash
set -euo pipefail

echo "Generating Python gRPC files"

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

./agent-adapter/.venv/bin/python -m grpc_tools.protoc \
  -I./src/main/proto \
  --python_out=./agent-adapter/app \
  --grpc_python_out=./agent-adapter/app \
  ./src/main/proto/bridge.proto

mv -f ./agent-adapter/app/bridge_pb2.py ./agent-adapter/app/bridge/bridge_pb2.py
mv -f ./agent-adapter/app/bridge_pb2_grpc.py ./agent-adapter/app/bridge/bridge_pb2_grpc.py
python3 - <<'PY'
from pathlib import Path
path = Path("agent-adapter/app/bridge/bridge_pb2_grpc.py")
text = path.read_text(encoding="utf-8")
text = text.replace("import bridge_pb2 as bridge__pb2", "import bridge.bridge_pb2 as bridge__pb2")
path.write_text(text, encoding="utf-8")
PY

echo "Done"