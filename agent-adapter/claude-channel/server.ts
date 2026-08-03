import http from "node:http";
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

type BridgeWakePayload = {
  requestId: string;
  workflowId: string;
  status: string;
  message: string;
};

type RegistrationResponse = {
  sessionId: string;
  continuationUrl: string;
  ingressUrl: string;
};

const HOST = "127.0.0.1";
const ADAPTER_BASE_URL = (
  process.env.ADAPTER_BASE_URL ?? "http://127.0.0.1:8000"
).replace(/\/$/, "");

let boundPort = 0;
let sessionId: string | null = null;
let continuationUrl: string | null = null;
let ingressUrl: string | null = null;

function resolvePreferredPort(): number | null {
  const rawPort = process.env.CHANNEL_PORT;
  if (rawPort === undefined || rawPort.trim() === "") {
    return null;
  }

  const port = Number.parseInt(rawPort, 10);
  if (!Number.isInteger(port) || port < 1 || port > 65535) {
    throw new Error(
      `Invalid CHANNEL_PORT '${rawPort}'. Expected a number between 1 and 65535.`,
    );
  }

  return port;
}

function isBridgeWakePayload(value: unknown): value is BridgeWakePayload {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  const payload = value as Record<string, unknown>;

  return (
    typeof payload.requestId === "string" &&
    typeof payload.workflowId === "string" &&
    typeof payload.status === "string" &&
    typeof payload.message === "string"
  );
}

function buildContent(payload: BridgeWakePayload): string {
  return [
    "Bridge workflow update.",
    `requestId: ${payload.requestId}`,
    `workflowId: ${payload.workflowId}`,
    `status: ${payload.status}`,
    `message: ${payload.message}`,
    "",
    "Handle this update in the current conversation and continue the workflow.",
  ].join("\n");
}

function readJsonBody(request: http.IncomingMessage): Promise<unknown> {
  return new Promise((resolve, reject) => {
    const chunks: Buffer[] = [];

    request.on("data", (chunk: Buffer) => {
      chunks.push(chunk);
    });

    request.on("end", () => {
      const raw = Buffer.concat(chunks).toString("utf8").trim();

      if (!raw) {
        reject(new Error("Empty request body"));
        return;
      }

      try {
        resolve(JSON.parse(raw));
      } catch {
        reject(new Error("Invalid JSON body"));
      }
    });

    request.on("error", reject);
  });
}

function sendJson(
  response: http.ServerResponse,
  statusCode: number,
  body: Record<string, unknown>,
): void {
  const payload = JSON.stringify(body);
  response.writeHead(statusCode, {
    "Content-Type": "application/json; charset=utf-8",
    "Content-Length": Buffer.byteLength(payload),
  });
  response.end(payload);
}

async function registerWithAdapter(localIngress: string): Promise<void> {
  const response = await fetch(`${ADAPTER_BASE_URL}/continuation/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ingressUrl: localIngress }),
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(
      `Adapter registration failed (${response.status}): ${body}`,
    );
  }

  const registration = (await response.json()) as RegistrationResponse;
  sessionId = registration.sessionId;
  continuationUrl = registration.continuationUrl;
  ingressUrl = registration.ingressUrl;

  console.error(
    `[bridge-wake] Registered with Adapter sessionId=${sessionId} ` +
      `continuation=${continuationUrl}`,
  );
}

async function unregisterFromAdapter(): Promise<void> {
  if (!sessionId) {
    return;
  }

  try {
    await fetch(`${ADAPTER_BASE_URL}/continuation/${sessionId}`, {
      method: "DELETE",
    });
    console.error(
      `[bridge-wake] Unregistered from Adapter sessionId=${sessionId}`,
    );
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : String(error);
    console.error(`[bridge-wake] Unregister failed: ${message}`);
  }
}

function listenOnPort(server: http.Server, port: number): Promise<number> {
  return new Promise((resolve, reject) => {
    const onError = (error: NodeJS.ErrnoException) => {
      server.off("listening", onListening);
      reject(error);
    };

    const onListening = () => {
      server.off("error", onError);
      const address = server.address();
      if (address === null || typeof address === "string") {
        reject(new Error("Failed to resolve bound Channel port"));
        return;
      }
      resolve(address.port);
    };

    server.once("error", onError);
    server.once("listening", onListening);
    server.listen(port, HOST);
  });
}

const channelServer = new Server(
  {
    name: "bridge-wake",
    version: "0.1.0",
  },
  {
    capabilities: {
      experimental: {
        "claude/channel": {},
      },
      tools: {},
    },
    instructions: [
      "Bridge workflow updates arrive inside <channel> tags.",
      "Treat them as asynchronous results for actions started in this session.",
      "Continue the current workflow using the request_id, workflow_id, status, and message attributes.",
      "Before calling send_action with platform=claude, call get_continuation_context",
      "and pass the returned continuationUrl as sessionId.",
      "This is a one-way channel, so do not attempt to reply through the channel.",
    ].join(" "),
  },
);

channelServer.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "get_continuation_context",
      description:
        "Return this Claude session's Adapter continuation URL. " +
        "Pass the continuationUrl as sessionId when calling send_action " +
        "with platform=claude.",
      inputSchema: {
        type: "object",
        properties: {},
        additionalProperties: false,
      },
    },
  ],
}));

channelServer.setRequestHandler(CallToolRequestSchema, async (request) => {
  if (request.params.name !== "get_continuation_context") {
    throw new Error(`Unknown tool: ${request.params.name}`);
  }

  if (!continuationUrl || !sessionId) {
    throw new Error(
      "Continuation context is not ready yet. " +
        "Wait for Adapter registration to finish.",
    );
  }

  return {
    content: [
      {
        type: "text",
        text: JSON.stringify(
          {
            sessionId,
            continuationUrl,
            ingressUrl,
          },
          null,
          2,
        ),
      },
    ],
  };
});

// Claude Code communicates with this process through stdin/stdout.
// Never write application logs to stdout because stdout belongs to MCP.
await channelServer.connect(new StdioServerTransport());

const httpServer = http.createServer(
  (request: http.IncomingMessage, response: http.ServerResponse) => {
    void (async () => {
      const method = request.method ?? "GET";
      const url = new URL(
        request.url ?? "/",
        `http://${HOST}:${boundPort || 0}`,
      );

      if (method === "GET" && url.pathname === "/health") {
        sendJson(response, 200, {
          status: "ok",
          channel: "bridge-wake",
          sessionId,
          continuationUrl,
          ingress: ingressUrl ?? `http://${HOST}:${boundPort}/wake`,
        });
        return;
      }

      if (method !== "POST" || url.pathname !== "/wake") {
        sendJson(response, 404, {
          error: "Not found",
          expected: "POST /wake",
        });
        return;
      }

      try {
        const body = await readJsonBody(request);

        if (!isBridgeWakePayload(body)) {
          sendJson(response, 400, {
            error: "Invalid Bridge wake payload",
            requiredFields: [
              "requestId",
              "workflowId",
              "status",
              "message",
            ],
          });
          return;
        }

        await channelServer.notification({
          method: "notifications/claude/channel",
          params: {
            content: buildContent(body),
            meta: {
              request_id: body.requestId,
              workflow_id: body.workflowId,
              status: body.status,
            },
          },
        });

        console.error(
          `[bridge-wake] Delivered request ${body.requestId} to Claude channel`,
        );

        sendJson(response, 200, {
          status: "ok",
          requestId: body.requestId,
        });
      } catch (error: unknown) {
        const message =
          error instanceof Error ? error.message : "Unknown channel error";

        console.error(`[bridge-wake] Failed to deliver event: ${message}`);

        sendJson(response, 500, {
          error: message,
        });
      }
    })();
  },
);

const preferredPort = resolvePreferredPort();
const listenPort = preferredPort ?? 0;

try {
  boundPort = await listenOnPort(httpServer, listenPort);
} catch (error: unknown) {
  const err = error as NodeJS.ErrnoException;
  if (err.code === "EADDRINUSE") {
    console.error(
      `[bridge-wake] Port ${listenPort} is already in use. ` +
        "Omit CHANNEL_PORT to auto-bind an ephemeral port.",
    );
  } else {
    console.error(
      `[bridge-wake] HTTP server error: ${
        error instanceof Error ? error.message : String(error)
      }`,
    );
  }
  process.exit(1);
}

ingressUrl = `http://${HOST}:${boundPort}/wake`;
console.error(
  `[bridge-wake] Channel ingress listening on ${ingressUrl}`,
);

try {
  await registerWithAdapter(ingressUrl);
} catch (error: unknown) {
  console.error(
    `[bridge-wake] Adapter registration failed: ${
      error instanceof Error ? error.message : String(error)
    }`,
  );
  console.error(
    `[bridge-wake] Falling back to direct ingress URL as continuation context: ${ingressUrl}`,
  );
  continuationUrl = ingressUrl;
}

async function shutdown(signal: string): Promise<void> {
  console.error(`[bridge-wake] Shutting down on ${signal}`);
  await unregisterFromAdapter();
  httpServer.close();
  process.exit(0);
}

process.on("SIGINT", () => {
  void shutdown("SIGINT");
});
process.on("SIGTERM", () => {
  void shutdown("SIGTERM");
});
process.on("exit", () => {
  // Best-effort sync cleanup is not available for HTTP DELETE here;
  // SIGINT/SIGTERM handlers cover normal Claude session exit.
});
