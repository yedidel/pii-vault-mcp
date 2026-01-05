# Bridge Server
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

git clone <need change>  
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
