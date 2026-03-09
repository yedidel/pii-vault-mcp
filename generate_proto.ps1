Write-Host "Generating Python gRPC files..."

python -m grpc_tools.protoc `
  -I.\src\main\proto `
  --python_out=.\agent-adapter\app `
  --grpc_python_out=.\agent-adapter\app `
  .\src\main\proto\bridge.proto

Write-Host "Done😊"