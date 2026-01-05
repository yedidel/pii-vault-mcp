# Bridge Server

A gRPC-based adapter service implemented in Kotlin.  
The Bridge Server acts as an intermediary layer between external agents and internal system components, exposing a well-defined gRPC interface without embedding business logic.

---

## Prerequisites

The following tools must be installed:

- JDK 17 (or a compatible JVM version)
- Git

Verification:

java -version  
git --version

---
## Setup

### Clone the Repository

git clone <BRIDGE_SERVER_REPO_URL>  
cd bridge-server

---

### Build the Project

Gradle automatically downloads dependencies, generates gRPC source files from the `.proto` definitions, and compiles the project.

./gradlew build

Windows:  
gradlew.bat build

---

## Running the Server

### Using Gradle

./gradlew run

### Using IntelliJ IDEA

Run the main entry point:

GrpcServerKt.main()

On successful startup, the following log is printed:

gRPC server started on port 50051

---

## Protocol Buffers and gRPC

- `.proto` files are located under `src/main/proto`
- gRPC source files are generated automatically during the Gradle build phase
- Generated sources are not committed to the repository

---

## Configuration

- Server port and gRPC configuration are defined directly in the Kotlin source code
- No external configuration files are required for local execution
