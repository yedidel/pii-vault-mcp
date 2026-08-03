/**
 * Local persistence for:
 *   Gemini CLI session_id -> Interactions API interaction.id
 *
 * Stored under ~/.gemini/bridge-interaction-map.json
 */
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const STORE_PATH =
  process.env.BRIDGE_INTERACTION_STORE_PATH ||
  path.join(os.homedir(), ".gemini", "bridge-interaction-map.json");

const DEFAULT_TTL_DAYS = Number.parseInt(
  process.env.BRIDGE_INTERACTION_TTL_DAYS ?? "7",
  10,
);

function nowIso() {
  return new Date().toISOString();
}

function emptyStore() {
  return { version: 1, sessions: {} };
}

export function readStore() {
  try {
    const raw = fs.readFileSync(STORE_PATH, "utf8");
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object" || !parsed.sessions) {
      return emptyStore();
    }
    return parsed;
  } catch {
    return emptyStore();
  }
}

export function writeStore(store) {
  const dir = path.dirname(STORE_PATH);
  fs.mkdirSync(dir, { recursive: true });
  const tempPath = `${STORE_PATH}.${process.pid}.tmp`;
  fs.writeFileSync(tempPath, `${JSON.stringify(store, null, 2)}\n`, "utf8");
  fs.renameSync(tempPath, STORE_PATH);
}

export function pruneStore(store, ttlDays = DEFAULT_TTL_DAYS) {
  if (!Number.isFinite(ttlDays) || ttlDays <= 0) {
    return store;
  }

  const cutoffMs = Date.now() - ttlDays * 24 * 60 * 60 * 1000;
  for (const [sessionId, entry] of Object.entries(store.sessions)) {
    const stamp = entry.lastUsedAt || entry.createdAt;
    const ms = Date.parse(stamp ?? "");
    if (!Number.isFinite(ms) || ms < cutoffMs) {
      delete store.sessions[sessionId];
    }
  }
  return store;
}

export function getMapping(store, sessionId) {
  return store.sessions[sessionId] ?? null;
}

export function putMapping(store, sessionId, interactionId) {
  const existing = store.sessions[sessionId];
  store.sessions[sessionId] = {
    interactionId,
    createdAt: existing?.createdAt ?? nowIso(),
    lastUsedAt: nowIso(),
  };
  return store.sessions[sessionId];
}

export function touchMapping(store, sessionId) {
  const entry = store.sessions[sessionId];
  if (entry) {
    entry.lastUsedAt = nowIso();
  }
  return entry;
}

export function deleteMapping(store, sessionId) {
  const existed = Object.prototype.hasOwnProperty.call(
    store.sessions,
    sessionId,
  );
  delete store.sessions[sessionId];
  return existed;
}

export function withStore(mutator) {
  const store = pruneStore(readStore());
  const result = mutator(store);
  writeStore(store);
  return result;
}

export function resolveApiKey() {
  return (
    process.env.GEMINI_API_KEY ||
    process.env.GOOGLE_API_KEY ||
    process.env.GOOGLE_GENAI_API_KEY ||
    ""
  ).trim();
}

export function resolveModel() {
  return (process.env.GEMINI_MODEL || "gemini-3.6-flash").trim();
}

/**
 * Create a new Interaction owned by this Gemini CLI session.
 * Uses the official Interactions REST API (same resource GeminiProvider wakes).
 */
export async function createInteraction() {
  const apiKey = resolveApiKey();
  if (!apiKey) {
    throw new Error(
      "Missing GEMINI_API_KEY or GOOGLE_API_KEY. " +
        "The bridge-interaction hook needs an API key to create the initial Interaction.",
    );
  }

  const model = resolveModel();
  const response = await fetch(
    "https://generativelanguage.googleapis.com/v1beta/interactions",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-goog-api-key": apiKey,
      },
      body: JSON.stringify({
        model,
        input:
          "Bridge continuation bootstrap for this Gemini CLI session. " +
          "Acknowledge briefly that you are ready.",
      }),
    },
  );

  const bodyText = await response.text();
  if (!response.ok) {
    throw new Error(
      `Interactions create failed (${response.status}): ${bodyText}`,
    );
  }

  let payload;
  try {
    payload = JSON.parse(bodyText);
  } catch {
    throw new Error(`Interactions create returned non-JSON: ${bodyText}`);
  }

  const interactionId = payload.id;
  if (typeof interactionId !== "string" || !interactionId.trim()) {
    throw new Error(`Interactions create response missing id: ${bodyText}`);
  }

  return interactionId.trim();
}

/**
 * Return the interaction.id for this CLI session, creating one if needed.
 */
export async function ensureInteractionId(sessionId) {
  if (!sessionId || typeof sessionId !== "string") {
    throw new Error("Missing Gemini CLI session_id in hook input");
  }

  const existingId = withStore((store) => {
    const existing = getMapping(store, sessionId);
    if (existing?.interactionId) {
      touchMapping(store, sessionId);
      return existing.interactionId;
    }
    return null;
  });
  if (existingId) {
    return existingId;
  }

  const interactionId = await createInteraction();

  // Another concurrent hook may have won the race while we were creating.
  return withStore((store) => {
    const existing = getMapping(store, sessionId);
    if (existing?.interactionId) {
      touchMapping(store, sessionId);
      return existing.interactionId;
    }
    putMapping(store, sessionId, interactionId);
    return interactionId;
  });
}

export function readStdinJson() {
  const raw = fs.readFileSync(0, "utf8");
  if (!raw.trim()) {
    return {};
  }
  return JSON.parse(raw);
}

export function writeHookOutput(payload) {
  process.stdout.write(`${JSON.stringify(payload)}\n`);
}

export function logError(message) {
  process.stderr.write(`[bridge-interaction] ${message}\n`);
}
