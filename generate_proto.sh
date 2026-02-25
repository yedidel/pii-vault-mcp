#generate the gRPC files for Python every time we build the proto files.
#run in terminal ./generate_proto.sh
echo "Generating Python gRPC files"

python -m grpc_tools.protoc \
  -I./src/main/proto \
  --python_out=./agent-adapter/app \
  --grpc_python_out=./agent-adapter/app \
  ./src/main/proto/bridge.proto

echo "Done😊"