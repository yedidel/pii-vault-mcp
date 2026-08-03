#!/usr/bin/env node
/**
 * POC ONLY — prove BeforeTool can rewrite MCP send_action arguments.
 * Always injects sessionId = "HOOK_TEST". No Interactions logic.
 */
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const LOG_CANDIDATES = [
  process.env.HOOK_POC_LOG,
  path.join(os.homedir(), ".gemini", "hook-poc.log"),
  path.join(
    process.env.GEMINI_PROJECT_DIR || process.cwd(),
    "agent-adapter/gemini-bridge-hooks/.poc-hook.log",
  ),
].filter(Boolean);

function log(line) {
  const msg = `[hook-poc] ${line}\n`;
  process.stderr.write(msg);
  for (const logPath of LOG_CANDIDATES) {
    try {
      fs.mkdirSync(path.dirname(logPath), { recursive: true });
      fs.appendFileSync(logPath, msg, "utf8");
    } catch {
      // try next path
    }
  }
}

const raw = fs.readFileSync(0, "utf8");
const input = raw.trim() ? JSON.parse(raw) : {};

const toolInput =
  input.tool_input && typeof input.tool_input === "object"
    ? { ...input.tool_input }
    : {};

const before = toolInput.sessionId;
toolInput.sessionId = "HOOK_TEST";

log(
  `rewriting sessionId before=${JSON.stringify(before)} after="HOOK_TEST" ` +
    `tool_name=${JSON.stringify(input.tool_name)}`,
);

process.stdout.write(
  `${JSON.stringify({
    suppressOutput: true,
    hookSpecificOutput: {
      hookEventName: "BeforeTool",
      tool_input: toolInput,
    },
  })}\n`,
);
