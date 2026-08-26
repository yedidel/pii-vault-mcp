package bridge

import java.nio.file.Files
import java.nio.file.Path

object EnvLoader {

    /**
     * Loads KEY=VALUE pairs from agent-adapter/.env into system properties
     * when not already set in the process environment.
     *
     * Run Bridge from the repo root so the relative path resolves.
     */
    fun loadFromRepoEnvFile(relativePath: String = "agent-adapter/.env") {
        val path = Path.of(relativePath)
        if (!Files.exists(path)) {
            println("WARN: env file not found: ${path.toAbsolutePath()}")
            return
        }

        Files.readAllLines(path).forEach { line ->
            val trimmed = line.trim()
            if (trimmed.isEmpty() || trimmed.startsWith("#")) {
                return@forEach
            }

            val separator = trimmed.indexOf('=')
            if (separator <= 0) {
                return@forEach
            }

            val key = trimmed.substring(0, separator).trim()
            val value = trimmed.substring(separator + 1).trim()
            if (key.isEmpty()) {
                return@forEach
            }

            if (System.getenv(key).isNullOrBlank() && System.getProperty(key).isNullOrBlank()) {
                System.setProperty(key, value)
            }
        }
    }
}
