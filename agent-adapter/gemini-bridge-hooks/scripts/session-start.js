#!/usr/bin/env node
/**
 * SessionStart: create Interaction for this Gemini CLI session (if needed)
 * and persist session_id -> interaction.id.
 */
import {
  ensureInteractionId,
  logError,
  readStdinJson,
  writeHookOutput,
} from "./lib/interaction-store.js";

const input = readStdinJson();

try {
  const interactionId = await ensureInteractionId(input.session_id);

  writeHookOutput({
    suppressOutput: true,
    systemMessage:
      `Bridge continuation ready (interaction ${interactionId}). ` +
      "For platform=gemini send_action, leave sessionId empty — " +
      "the BeforeTool hook injects it.",
    hookSpecificOutput: {
      hookEventName: "SessionStart",
      additionalContext:
        "When calling send_action with platform=gemini, leave sessionId " +
        "empty or omit a fabricated id. The Gemini CLI bridge-interaction " +
        "hook injects the real interaction.id automatically.",
    },
  });
} catch (error) {
  const message = error instanceof Error ? error.message : String(error);
  logError(`SessionStart failed: ${message}`);
  // Do not block session startup; BeforeTool can still try later.
  writeHookOutput({
    systemMessage: `Bridge interaction bootstrap failed: ${message}`,
  });
}
