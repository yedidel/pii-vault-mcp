import assert from "node:assert/strict";
import test from "node:test";
import {
  continuationToolText,
  registerWithAdapter,
  unregisterFromAdapter,
} from "./adapter_http.js";

const TOKEN = "claude-channel-test-token";
const BASE_URL = "http://127.0.0.1:8000";
const INGRESS = "http://127.0.0.1:55604/wake";
const SESSION_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee";
const CONTINUATION_URL = `${BASE_URL}/continuation/${SESSION_ID}`;

type Captured = {
  url: string;
  init?: RequestInit;
};

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function textResponse(status: number, body: string): Response {
  return new Response(body, { status });
}

test("registration sends bearer and stores both continuation fields", async () => {
  const calls: Captured[] = [];
  const registered = await registerWithAdapter(INGRESS, {
    baseUrl: BASE_URL,
    env: { ADAPTER_AUTH_TOKEN: TOKEN },
    fetchImpl: async (input, init) => {
      calls.push({ url: String(input), init });
      return jsonResponse(200, {
        sessionId: SESSION_ID,
        continuationUrl: CONTINUATION_URL,
        ingressUrl: INGRESS,
      });
    },
  });

  assert.equal(calls.length, 1);
  assert.equal(calls[0]?.url, `${BASE_URL}/continuation/register`);
  assert.equal(calls[0]?.init?.method, "POST");
  assert.equal(calls[0]?.init?.body, JSON.stringify({ ingressUrl: INGRESS }));
  const headers = new Headers(calls[0]?.init?.headers);
  assert.equal(headers.get("authorization"), `Bearer ${TOKEN}`);
  assert.equal(headers.get("content-type"), "application/json");

  assert.ok(registered.sessionId);
  assert.ok(registered.continuationUrl);
  const text = continuationToolText({
    sessionId: registered.sessionId,
    continuationUrl: registered.continuationUrl,
    ingressUrl: registered.ingressUrl,
  });
  assert.match(text, new RegExp(SESSION_ID));
  assert.match(text, /http:\/\/127\.0\.0\.1:8000\/continuation\//);
});

test("unregister sends bearer on DELETE", async () => {
  const calls: Captured[] = [];
  const logs: string[] = [];
  await unregisterFromAdapter(SESSION_ID, {
    baseUrl: BASE_URL,
    env: { ADAPTER_AUTH_TOKEN: TOKEN },
    log: (message) => logs.push(message),
    fetchImpl: async (input, init) => {
      calls.push({ url: String(input), init });
      return textResponse(200, "");
    },
  });

  assert.equal(calls.length, 1);
  assert.equal(calls[0]?.url, `${BASE_URL}/continuation/${SESSION_ID}`);
  assert.equal(calls[0]?.init?.method, "DELETE");
  const headers = new Headers(calls[0]?.init?.headers);
  assert.equal(headers.get("authorization"), `Bearer ${TOKEN}`);
  assert.equal(logs.some((line) => line.includes(TOKEN)), false);
});

test("registration failure redacts the token from the error", async () => {
  const logs: string[] = [];
  await assert.rejects(
    () =>
      registerWithAdapter(INGRESS, {
        baseUrl: BASE_URL,
        env: { ADAPTER_AUTH_TOKEN: TOKEN },
        fetchImpl: async () =>
          textResponse(401, `{"detail":"bad ${TOKEN}"}`),
      }),
    (error: unknown) => {
      assert.ok(error instanceof Error);
      logs.push(
        `[bridge-wake] Adapter registration failed: ${error.message}`,
      );
      assert.match(error.message, /Adapter registration failed \(401\)/);
      assert.match(error.message, /bad \[redacted\]/);
      assert.equal(error.message.includes(TOKEN), false);
      assert.equal(error.message.includes("Authorization"), false);
      return true;
    },
  );

  assert.equal(logs.some((line) => line.includes(TOKEN)), false);
  assert.match(logs[0] ?? "", /401/);
});

test("unregister failure redacts the token from logs", async () => {
  const logs: string[] = [];
  await unregisterFromAdapter(SESSION_ID, {
    baseUrl: BASE_URL,
    env: { ADAPTER_AUTH_TOKEN: TOKEN },
    log: (message) => logs.push(message),
    fetchImpl: async () => {
      throw new Error(`connect failed ${TOKEN}`);
    },
  });

  assert.equal(logs.length, 1);
  assert.match(logs[0] ?? "", /Unregister failed/);
  assert.match(logs[0] ?? "", /\[redacted\]/);
  assert.equal((logs[0] ?? "").includes(TOKEN), false);
});

test("fallback URL without sessionId is not a ready continuation context", () => {
  assert.throws(
    () =>
      continuationToolText({
        sessionId: null,
        continuationUrl: INGRESS,
        ingressUrl: INGRESS,
      }),
    /Continuation context is not ready yet/,
  );
});
