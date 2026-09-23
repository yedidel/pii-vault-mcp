# Regenerates the Python gRPC stubs committed under agent-adapter/app/bridge/.
# Prefer the repository virtual environment when it exists.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$VenvPython = Join-Path $Root "agent-adapter\.venv\Scripts\python.exe"
if (Test-Path $VenvPython) {
    $Python = $VenvPython
} else {
    $Python = "python"
}

Write-Host "Generating Python gRPC files"
& $Python -m grpc_tools.protoc `
    -I.\src\main\proto `
    --python_out=.\agent-adapter\app `
    --grpc_python_out=.\agent-adapter\app `
    .\src\main\proto\bridge.proto

New-Item -ItemType Directory -Force -Path ".\agent-adapter\app\bridge" | Out-Null
Move-Item -Force ".\agent-adapter\app\bridge_pb2.py" ".\agent-adapter\app\bridge\bridge_pb2.py"
Move-Item -Force ".\agent-adapter\app\bridge_pb2_grpc.py" ".\agent-adapter\app\bridge\bridge_pb2_grpc.py"

$GrpcFile = ".\agent-adapter\app\bridge\bridge_pb2_grpc.py"
$Text = Get-Content -Raw $GrpcFile
$Text = $Text.Replace("import bridge_pb2 as bridge__pb2", "import bridge.bridge_pb2 as bridge__pb2")
Set-Content -Path $GrpcFile -Value $Text -NoNewline

Write-Host "Done"
