import com.google.protobuf.gradle.id
import org.jlleitschuh.gradle.ktlint.tasks.KtLintCheckTask
import org.jlleitschuh.gradle.ktlint.tasks.KtLintFormatTask

plugins {
    kotlin("jvm") version "1.9.22"
    kotlin("plugin.jpa") version "1.9.22"
    kotlin("plugin.spring") version "1.9.22"
    //for spring server build
    id("org.springframework.boot") version "3.2.2"
    id("io.spring.dependency-management") version "1.1.4"

    application
    id("com.google.protobuf") version "0.9.4"
    id("org.jlleitschuh.gradle.ktlint") version "12.1.0"
}

repositories {
    mavenCentral()
}

dependencies {
    implementation("io.grpc:grpc-netty-shaded:1.62.2")
    implementation("io.grpc:grpc-protobuf:1.62.2")
    implementation("io.grpc:grpc-stub:1.62.2")
    implementation("io.grpc:grpc-kotlin-stub:1.4.1")
    implementation("com.google.protobuf:protobuf-kotlin:3.25.1")
    implementation("org.springframework.boot:spring-boot-starter-data-jpa")
    implementation("org.postgresql:postgresql")
    implementation("org.jetbrains.kotlin:kotlin-reflect")
}

protobuf {
    protoc {
        artifact = "com.google.protobuf:protoc:3.25.1"
    }
    plugins {
        id("grpc") {
            artifact = "io.grpc:protoc-gen-grpc-java:1.62.2"
        }
        id("grpckt") {
            artifact = "io.grpc:protoc-gen-grpc-kotlin:1.4.1:jdk8@jar"
        }
    }
    generateProtoTasks {
        all().forEach {
            it.builtins {
                id("kotlin")
            }
            it.plugins {
                id("grpc")
                id("grpckt")
            }
        }
    }
}

ktlint {
    filter {
        exclude("**/build/generated/**")
    }
}
tasks.withType<KtLintCheckTask>().configureEach {
    exclude("**/build/generated/**")
}

tasks.withType<KtLintFormatTask>().configureEach {
    exclude("**/build/generated/**")
}
tasks.named("ktlintMainSourceSetCheck") {
    enabled = false
}
application {
    mainClass.set("bridge.GrpcServerKt")
}
