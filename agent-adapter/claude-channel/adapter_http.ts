export type RegistrationResponse = {
  sessionId: string;
  continuationUrl: string;
  ingressUrl: string;
};

export type ContinuationFields = {
  sessionId: string | null;
  continuationUrl: string | null;
  ingressUrl: string | null;
};

type AdapterHttpOptions = {
  fetchImpl?: typeof fetch;
  baseUrl: string;
  env: NodeJS.ProcessEnv;
  log?: (message: string) => void;
};

export function adapterAuthToken(env: NodeJS.ProcessEnv): string {
  return (env.ADAPTER_AUTH_TOKEN ?? "").trim();
}

export function adapterAuthHeaders(
  env: NodeJS.ProcessEnv,
): Record<string, string> {
  const token = adapterAuthToken(env);
  if (!token) {
    return {};
  }
  return { Authorization: `Bearer ${token}` };
}

export function redactSecret(text: string, secret: string): string {
  const token = secret.trim();
  if (!token) {
    return text;
  }
  return text.split(token).join("[redacted]");
}

export function formatAdapterFailure(
  status: number,
  body: string,
  token: string,
): string {
  return `Adapter registration failed (${status}): ${redactSecret(body, token)}`;
}

export function continuationToolText(state: ContinuationFields): string {
  if (!state.continuationUrl || !state.sessionId) {
    throw new Error(
      "Continuation context is not ready yet. " +
        "Wait for Adapter registration to finish.",
    );
  }

  return JSON.stringify(
    {
      sessionId: state.sessionId,
      continuationUrl: state.continuationUrl,
      ingressUrl: state.ingressUrl,
    },
    null,
    2,
  );
}

function adapterBaseUrl(baseUrl: string): string {
  return baseUrl.replace(/\/$/, "");
}

export async function registerWithAdapter(
  localIngress: string,
  options: AdapterHttpOptions,
): Promise<RegistrationResponse> {
  const token = adapterAuthToken(options.env);
  const fetchImpl = options.fetchImpl ?? fetch;
  const response = await fetchImpl(
    `${adapterBaseUrl(options.baseUrl)}/continuation/register`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...adapterAuthHeaders(options.env),
      },
      body: JSON.stringify({ ingressUrl: localIngress }),
    },
  );

  if (!response.ok) {
    const body = await response.text();
    throw new Error(formatAdapterFailure(response.status, body, token));
  }

  return (await response.json()) as RegistrationResponse;
}

export async function unregisterFromAdapter(
  sessionId: string,
  options: AdapterHttpOptions,
): Promise<void> {
  const log = options.log ?? ((message: string) => console.error(message));
  const token = adapterAuthToken(options.env);
  const headers = adapterAuthHeaders(options.env);
  const init: RequestInit = { method: "DELETE" };
  if (Object.keys(headers).length > 0) {
    init.headers = headers;
  }

  try {
    await (options.fetchImpl ?? fetch)(
      `${adapterBaseUrl(options.baseUrl)}/continuation/${sessionId}`,
      init,
    );
    log(`[bridge-wake] Unregistered from Adapter sessionId=${sessionId}`);
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : String(error);
    log(
      `[bridge-wake] Unregister failed: ${redactSecret(message, token)}`,
    );
  }
}
