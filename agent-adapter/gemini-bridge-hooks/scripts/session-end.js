#!/usr/bin/env node
/**
 * SessionEnd: drop this CLI session's mapping.
 */
import {
  deleteMapping,
  logError,
  pruneStore,
  readStdinJson,
  readStore,
  writeHookOutput,
  writeStore,
} from "./lib/interaction-store.js";

const input = readStdinJson();

try {
  const store = pruneStore(readStore());
  if (input.session_id) {
    deleteMapping(store, input.session_id);
  }
  writeStore(store);
  writeHookOutput({ suppressOutput: true });
} catch (error) {
  const message = error instanceof Error ? error.message : String(error);
  logError(`SessionEnd cleanup failed: ${message}`);
  writeHookOutput({});
}
