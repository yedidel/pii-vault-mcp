#!/usr/bin/env node
/**
 * BeforeTool (mcp_bridge-adapter_send_action):
 * If sessionId is missing/blank, inject the Interaction id owned by this CLI session.
 * If sessionId is already present, leave tool_input unchanged.
 */
import {
  ensureInteractionId,
  logError,
  readStdinJson,
  writeHookOutput,
} from "./lib/interaction-store.js";

const input = readStdinJson();
const toolInput =
  input.tool_input && typeof input.tool_input === "object"
    ? { ...input.tool_input }
    : {};

const existingSessionId =
  typeof toolInput.sessionId === "string" ? toolInput.sessionId.trim() : "";

if (existingSessionId) {
  // Explicit sessionId from the model/user wins.
  writeHookOutput({});
  process.exit(0);
}

try {
  const interactionId = await ensureInteractionId(input.session_id);
  toolInput.sessionId = interactionId;

  writeHookOutput({
    suppressOutput: true,
    hookSpecificOutput: {
      hookEventName: "BeforeTool",
      tool_input: toolInput,
    },
  });
} catch (error) {
  const message = error instanceof Error ? error.message : String(error);
  logError(`BeforeTool failed: ${message}`);
  writeHookOutput({
    decision: "deny",
    reason:
      `Bridge continuation bootstrap failed: ${message}. ` +
      "Set GEMINI_API_KEY (or GOOGLE_API_KEY), or pass sessionId explicitly.",
  });
}
