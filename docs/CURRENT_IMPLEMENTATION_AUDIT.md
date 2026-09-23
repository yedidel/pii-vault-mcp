# CURRENT IMPLEMENTATION AUDIT — The Bridge

**Source of truth:** executable code in the current working tree of `/Users/yhd/pii-vault-mcp`.  
**Rule:** comments, README, older docs, and diagrams are secondary. If they conflict with code, code wins.  
**Date of audit:** 2026-09-16.  
**Posture:** local engineering prototype / academic demonstration, not a production-hardened deployment.

Classification used below:

- **Implemented** — exists, has real logic, and is wired into a runtime path.
- **Partial** — exists and is invoked, but incomplete, transport-dependent, or missing failure/recovery coverage.
- **Stub** — class/module exists but the body is TODO / no-op.
- **Not Present** — no corresponding runtime component.
- **Demo / Mock** — in-repo stand-in for an external system.
- **Not verified from current code** — cannot be proven from the repository alone.

---

## 1. Project overview

**The Bridge** is a mediation and workflow-orchestration layer between AI agents and sensitive operations.

As implemented:

1. An **Agent Adapter** (Python) exposes MCP tools to agents.
2. The Adapter calls **Bridge** (Kotlin / Spring Boot) over **plaintext gRPC** on port **50051**.
3. Bridge persists an `Action` and a `Workflow` in **PostgreSQL**, publishes events to **Kafka** topic `workflow-events`, and drives a state machine (`WorkflowEngine`).
4. Bridge verifies the agent via **Guardian HTTP** (`localhost:8001`) and requests evaluation from a **Vault WebSocket client** connected to `/vault-websocket` on Spring port **8081**.
5. On a terminal workflow outcome, Bridge notifies the Adapter using a **continuation connector**. The default Adapter path is **WEBHOOK** (`POST http://127.0.0.1:8000/webhook/bridge`).
6. The Adapter wakes the original platform (**Claude Channel**, **OpenAI Responses**, **Gemini Interactions**, or **SDK no-op**) and may push **SSE** to a local client.

The system is **asynchronous after `SendAction`**: gRPC returns immediately with `RECEIVED` (or reuses an existing action/workflow). Completion is later.

This is **not** a cloud product. Ports, Guardian URL, demo form URL, and gRPC target are largely hardcoded to localhost. Docker Compose starts **PostgreSQL + Kafka + Zookeeper + Kafka UI only**.

---

## 2. Repository / module structure

```
pii-vault-mcp/
  src/main/kotlin/          Bridge (Kotlin)
  src/main/proto/bridge.proto
  src/main/resources/application.properties
  build.gradle.kts          Gradle / Spring Boot 3.2.2 / gRPC / Kafka / JPA
  docker-compose.yml        db, zookeeper, kafka, kafka-ui
  agent-adapter/            Adapter + clients + Claude Channel
  bridge-sdk/               Python client of Adapter MCP+SSE (not imported by Adapter)
  install-directory/        Mock pairing directory
  guardian-mock/            Mock Guardian HTTP service
  mock-vault/               Mock Vault WebSocket client
  demo-forms/               Demo FILL_FORM HTML/HTTP target
  .mcp.json                 Cursor MCP entries
  .gemini/settings.json     Gemini CLI local MCP/hooks config
  docs/                     Documentation (secondary)
```

**Kotlin tests:** none.  
**Repo-root tests:** none.  
**Adapter tests:** manual e2e scripts only (`test_e2e_sse.py`, `test_polling_e2e.py`, `test_fill_form.py`).  
**SDK tests:** `bridge-sdk/tests/run_tests.py`.

---

## 3. High-level architecture

```
AI agent (Claude Code / openai-client / gemini-client / bridge-sdk)
        | MCP (stdio or HTTP /mcp)
        v
Agent Adapter :8000  (FastMCP + HTTP routes; stdio mode uses a second FastAPI app)
        | gRPC insecure localhost:50051
        v
Bridge Spring Boot :8081 HTTP/WS  +  gRPC :50051
        |-- PostgreSQL :5432  (actions, workflows)
        |-- Kafka :9092 topic workflow-events
        |-- HTTP GET Guardian :8001/v1/authenticate/agent
        |-- WebSocket /vault-websocket  <-- mock-vault (or real Vault client)
        |-- HTTP POST continuation (WEBHOOK or CHANNEL)
        v
Adapter webhook / polling worker / wake providers / SSE
```

**Agent Notification Service:** **Not Present.** Continuation is `NotifyAgentCommand` → `ContinuationRegistry` on Bridge, then Adapter `ContinuationService` / `WakeDispatcher`.

---

## 4. Complete end-to-end flow (happy path, WEBHOOK)

Proven from `mcp_server.send_action` → `main.send_action` → `BridgeServiceImpl.sendAction` → Kafka → handlers → `WebhookContinuation` → Adapter webhook → `WakeDispatcher`.

1. Agent calls MCP `send_action` with `agentId`, `actionType`, `parameters`, `platform`, `sessionId`.
2. Adapter may require **pairing** (`PairingService.resolve`). If unpaired and Install Directory is configured, returns a pairing-required payload instead of calling Bridge.
3. For `FILL_FORM`, Adapter `PiiVaultStore.sanitize_fill_form_parameters` replaces email/password with `vault://pii/...` refs (Fernet ciphertext stored locally).
4. Adapter stores a **pending workflow in memory** (`WorkflowService`) keyed by Bridge `requestId`, including platform + continuation context (`sessionId`).
5. Adapter gRPC `SendAction` with `connector_type` / `connector_context` from `DefaultContinuationProvider` (default WEBHOOK URL).
6. `ActionService.handleAction` validates action type (`PAYMENT` / `TRANSACTION` / `FILL_FORM`); FILL_FORM email/password must be empty or `vault://pii/...`.
7. Idempotency: identical `(agentId, actionType, parametersJson)` within **2 minutes** reuses the existing `ActionEntity`.
8. If a `WorkflowEntity` already exists for that `request_id`, gRPC returns the existing workflow (no second init).
9. Else `WorkflowInitializationService` persists workflow `RECEIVED` / `ACTION_RECEIVED` and publishes `ActionCreatedEvent` to Kafka.
10. gRPC returns `request_id`, `workflow_id`, status `RECEIVED`. Description still tells the caller to poll `GetActionStatus`.
11. `WorkflowEventConsumer` (`groupId=workflow-engine`) deserializes JSON and calls `WorkflowEngine.process`.
12. `ActionCreatedEventHandler`: transition `WAITING_FOR_GUARDIAN` + `VerifyAgentCommand`.
13. `GuardianGatewayAdapter.verifyAgent`: HTTP GET `http://localhost:8001/v1/authenticate/agent?did={agentId}`. `status=="verified"` → `GuardianApprovedEvent`; else / exception → `GuardianRejectedEvent`.
14. Approved: transition `WAITING_FOR_VAULT_RESPONSE` + `RequestVaultEvaluationCommand`.
15. `VaultGatewayAdapter` → `VaultWebSocketHandler.sendRequestToVault` (`payment_request`, payload **Base64**, not encryption) or `form_fill_request`.
16. Vault client sends `action_approved` or `action_rejected` over WS.
17. Handler publishes `ActionResponseReceivedEvent`.
18. `ActionResponseReceivedEventHandler`:
    - APPROVED/COMPLETED/SUCCESS → action `COMPLETED`, workflow `COMPLETED`, publish `WORKFLOW_COMPLETED`, `NotifyAgentCommand`.
    - REJECTED → action `REJECTED`, workflow `FAILED`, publish `WORKFLOW_FAILED`, notify.
    - else → action `FAILED`, workflow `FAILED`, notify.
19. `NotifyAgentCommand` → `WorkflowContinuationService` (`ContinuationRegistry`) → connector.
20. WEBHOOK: POST JSON `{workflowId, requestId, status, message}` with HMAC headers if `WEBHOOK_SECRET` is set (**required** on Bridge; missing secret throws).
21. Adapter HTTP MCP path verifies HMAC then `ContinuationService.handle` → `WakeDispatcher.wake` → provider + `SseClientNotifier` event `workflow.updated`.
22. Pending in-memory workflow is removed on final statuses.

**Failure path (Guardian reject):** `GuardianRejectedEventHandler` sets workflow `FAILED`, action `REJECTED`, publishes `WORKFLOW_FAILED`, notifies agent.

---

## 5. Bridge architecture

**Entry:** `bridge.GrpcServerKt` / `BridgeServerApplication` (`GrpcServer.kt`).

- Loads `agent-adapter/.env` via `EnvLoader.loadFromRepoEnvFile()` (relative path; must run from repo root).
- Starts Spring Boot (`server.port` default **8081**).
- Starts gRPC server **hardcoded 50051**, insecure.
- `@EnableScheduling` is present; **no `@Scheduled` methods exist**. Recovery is `ApplicationReadyEvent` only.

**Packages (runtime):**

| Package | Role | Evidence |
|---|---|---|
| `bridge` | gRPC impl, ActionService, EnvLoader | `BridgeServiceImpl.kt`, `ActionService.kt` |
| `bridge.config` | Kafka listener/retry, RestTemplate, WebSocket | `KafkaListenerConfig.kt`, `KafkaRetryConfig.kt`, `WebSocketConfig.kt` |
| `bridge.integration` | Guardian + Vault gateways | `GuardianGatewayAdapter.kt`, `VaultGatewayAdapter.kt` |
| `bridge.model` | JPA entities | `ActionEntity.kt`, `WorkflowEntity.kt` |
| `bridge.repository` | Spring Data | `ActionRepository.kt`, `WorkflowRepository.kt` |
| `bridge.workflow*` | engine, handlers, events, recovery | `WorkflowEngine.kt` |
| `bridge.websocket` | Vault WS | `VaultWebSocketHandler.kt` |
| `connectors.*` | continuation connectors | `WebhookContinuation.kt` etc. |
| `continuation` | `ConnectorType`, `ContinuationRequest`, `WorkflowContinuationService` | |

**HTTP REST API for agents:** **Not Present.** Agent API is gRPC only.

---

## 6. Agent Adapter architecture

**Process entry:** `agent-adapter/app/adapter.py` (`run_adapter`), **not** `main.py`.

`main.py` is the **gRPC helper** (`grpc.insecure_channel('localhost:50051')`).

| `MCP_TRANSPORT` | What runs |
|---|---|
| `stdio` (default) | MCP stdio **plus** uvicorn FastAPI `server.py` (webhook/events/sessions) **plus** `PollingWorker` **plus** `PairingWatcher` |
| `http` | Single uvicorn wrapping FastMCP streamable HTTP with custom routes **plus** workers |

**HTTP MCP app routes** (`mcp_server.py`): `GET /`, `POST /mcp`, `POST /webhook/bridge` (**HMAC**), `GET /events`, `POST /sessions/register`, `POST /continuation/register`, `POST|DELETE /continuation/{session_id}`, `POST /vault/resolve` (localhost only).

**stdio FastAPI routes** (`server.py`): `GET /`, `POST /webhook/bridge` (**no HMAC** — calls `process_bridge_webhook` directly), `GET /events`, `POST /sessions/register`. **Missing:** `/continuation/*`, `/vault/resolve`, `AdapterAuthMiddleware`.

**Pending workflows:** in-memory dict only (`workflow_service.py`). Restart loses mapping → webhook 404.

**Claude session map:** in-memory (`continuation/session_registry.py`).

**Bridge session + SSE tokens:** SQLite `app/data/sessions.sqlite3` (`session_registry.py`).

**Orphan modules (exist, not imported into runtime):**

- `identity_provider.py`
- `grpc_client.py`
- `bridge/bridge_client.py`

---

## 7. bridge-sdk

**Location:** `bridge-sdk/`.  
**Role:** pip-installable Python client (`BridgeClient`) talking to **Adapter MCP + SSE**, not to Bridge gRPC.

**Imported by Adapter?** **No.**  
**Imported by Bridge?** **No.**

Adapter registers `SdkProvider` for `platform=sdk` (`workflow_context.py`). Wake is a **no-op** (status/SSE only); SDK waits on SSE/`get_action_status`.

Methods (from `client.py` docstring): `send_payment`, `send_fill_form`, `send_transaction`, `store_pii`, wait variants, `run(...)`.

**Status:** Implemented as an **external consumer**, prototype quality.

---

## 8. Workflow Engine

**Class:** `bridge.workflow.WorkflowEngine`  
**Invoked by:** `WorkflowEventConsumer.consume`, `WorkflowRecoveryService.recoverUnfinishedWorkflows` → `resume`.

`process(event)`:

1. `WorkflowContextLoader.load`
2. `WorkflowTransitionValidator.shouldProcessEvent` (also used as lightweight idempotency)
3. Find handler via `ObjectProvider<List<AbstractWorkflowEventHandler<*>>>`
4. `WorkflowCommandExecutor.execute(decision)`

Handlers (`@Component`):

| Handler | Event |
|---|---|
| `ActionCreatedEventHandler` | ACTION_CREATED |
| `GuardianApprovedEventHandler` | GUARDIAN_APPROVED |
| `GuardianRejectedEventHandler` | GUARDIAN_REJECTED |
| `ActionResponseReceivedEventHandler` | ACTION_RESPONSE_RECEIVED |
| `WorkflowCompletedEventHandler` | WORKFLOW_COMPLETED |
| `WorkflowFailedEventHandler` | WORKFLOW_FAILED |

**Dead path:** `shouldProcessEvent` accepts `WORKFLOW_COMPLETED` / `WORKFLOW_FAILED` only when state is `IN_PROGRESS`. Live handlers transition to `COMPLETED`/`FAILED` **before** publishing those events. Consumer **ignores** them. Notify already happens in `ActionResponseReceivedEventHandler` / `GuardianRejectedEventHandler`.

---

## 9. Workflow states, steps, events, commands

### WorkflowState (`WorkflowState.kt`)

`RECEIVED`, `WAITING_FOR_GUARDIAN`, `WAITING_FOR_VAULT_RESPONSE`, `IN_PROGRESS`, `COMPLETED`, `FAILED`

**`IN_PROGRESS` is never assigned by any live handler.** Validator allows `WAITING_FOR_VAULT_RESPONSE → IN_PROGRESS`. Recovery for `IN_PROGRESS` is empty.

### WorkflowStep (`WorkflowStep.kt`)

`ACTION_RECEIVED`, `VERIFY_AGENT`, `REQUEST_VAULT_EVALUATION`, `WAIT_FOR_VAULT_RESPONSE`, `NOTIFY_AGENT`, `FINISHED`

**`WAIT_FOR_VAULT_RESPONSE` is never assigned** in `TransitionCommand`s found in handlers. Terminal transitions force step `FINISHED` in `WorkflowTransitionService` (overrides `NOTIFY_AGENT`).

### WorkflowEventType

`ACTION_CREATED`, `GUARDIAN_APPROVED`, `GUARDIAN_REJECTED`, `ACTION_RESPONSE_RECEIVED`, `WORKFLOW_COMPLETED`, `WORKFLOW_FAILED`

Kafka topic: **`workflow-events`**. JSON serialization via Jackson (`KafkaWorkflowEventPublisher`).

### Commands (`WorkflowCommand.kt`)

`TransitionCommand`, `PublishEventCommand`, `VerifyAgentCommand`, `RequestVaultEvaluationCommand`, `NotifyAgentCommand`, `UpdateActionStatusCommand`

Enum `WorkflowCommandType` **exists and is unused**. Field `WorkflowEntity.lastExecutedCommand` **is never written**.

---

## 10. Kafka usage

| Item | Value | Evidence |
|---|---|---|
| Topic | `workflow-events` | `KafkaWorkflowEventPublisher`, `WorkflowEventConsumer` |
| Bootstrap | `localhost:9092` | `application.properties` |
| Producer serializers | String/String | properties |
| Listener groupId | `workflow-engine` (annotation) | overrides property `bridge-group` |
| Retry | `FixedBackOff(2000L, 2L)` → 3 attempts | `KafkaRetryConfig.kt` |
| Security | PLAINTEXT in compose | `docker-compose.yml` |
| Auto-create | `spring.kafka.admin.auto-create=true` | properties |

Producer failure: logged only (`KafkaWorkflowEventPublisher`).

---

## 11. PostgreSQL / database model

**Config:** `jdbc:postgresql://localhost:5432/${POSTGRES_DB:bridge_db}`, user `${POSTGRES_USER:user}`, password `${POSTGRES_PASSWORD:}`, `ddl-auto=update`.

Compose service `db` uses `env_file: agent-adapter/.env`.

### Table `actions` (`ActionEntity`)

| Column | Notes |
|---|---|
| `request_id` PK | |
| `agent_id` | |
| `user_install_id` | |
| `action_type` | string, validated in service |
| `parameters_json` | jsonb |
| `context_json` | jsonb; **never populated on create** |
| `status` | `StatusType` STRING |
| `result_data` | text |
| `created_at`, `updated_at` | |

### Table `workflows` (`WorkflowEntity`)

| Column | Notes |
|---|---|
| `workflow_id` PK | |
| `request_id` unique | logical 1:1 with actions; **no JPA relation** |
| `connector_type` | enum |
| `connector_context` | opaque |
| `current_state`, `current_step` | |
| `context_json` | ActionContext JSON |
| `created_at`, `updated_at`, `completed_at` | |
| `last_executed_command` | **unused** |

No other JPA entities found.

---

## 12. gRPC + Protocol Buffers

**File:** `src/main/proto/bridge.proto`  
**Service:** `BridgeService`

| RPC | Request | Response |
|---|---|---|
| `SendAction` | `ActionRequest` | `ActionResponse` |
| `GetActionStatus` | `StatusRequest` | `StatusResponse` |

**ActionRequest fields:** `agent_id`, `user_install_id`, `action_type`, `parameters` map, `connector_type`, `connector_context`. **No `platform` field.**

**StatusType enum:** UNSPECIFIED, RECEIVED, WAITING_FOR_USER, IN_PROGRESS, COMPLETED, FAILED, REJECTED, EXPIRED, FAILED_APP_NOT_INSTALLED.

**Kotlin actually writes:** RECEIVED, FAILED (validation), COMPLETED, REJECTED.  
**Never set in Kotlin:** WAITING_FOR_USER, IN_PROGRESS, EXPIRED, FAILED_APP_NOT_INSTALLED.

`StatusResponse.updated_at` exists in proto; **`getActionStatus` does not set it**.

gRPC is **plaintext**; no interceptors/auth found.

---

## 13. MCP tools

**Server name:** `bridge-adapter` (`FastMCP` in `mcp_server.py`).

| Tool | Status | Notes |
|---|---|---|
| `send_action` | Implemented | pairing, session bind, PII sanitize, gRPC |
| `store_pii` | Implemented | local Fernet store; returns `vault://` token |
| `get_action_status` | Implemented | **temporary polling loop** up to 20×1s while status is RECEIVED or IN_PROGRESS |

Claude Channel MCP (`bridge-wake`) tool: `get_continuation_context` — **not** an Adapter tool.

Transports: stdio or Streamable HTTP `/mcp`. `.mcp.json` points Adapter HTTP to `http://127.0.0.1:8000/mcp`.

---

## 14. Guardian integration

**Interface:** `GuardianGateway.verifyAgent`  
**Impl:** `GuardianGatewayAdapter`

| Call | Used in workflow? |
|---|---|
| GET `http://localhost:8001/v1/authenticate/agent?did=` | **Yes** (`VerifyAgentCommand`) |
| POST `http://localhost:8001/v1/report` | **No callers** of `reportOutcome` |
| `verifyAgentSync` | **No callers** |

URL is **hardcoded**. No TLS, no auth headers. `trustLevel` on approved event is **ignored** by `GuardianApprovedEventHandler`.

**In-repo mock:** `guardian-mock/guardian_mock.py` FastAPI **:8001**, hardcoded DIDs `agent-123`, `trusted-bot-1`. This is a **mock**, not a production Guardian.

---

## 15. Vault integration

Two distinct “vault” concepts exist:

### A. External Vault (payment / form evaluation)

Bridge hosts **WebSocket** `/vault-websocket` (`WebSocketConfig`, `setAllowedOrigins("*")`, **no WS auth**).

Inbound types: `connection_init` → `connection_ack`; `action_approved`; `action_rejected`. Other types ignored.

Outbound: `payment_request` with Base64 `data` (`amount;currency;timestamp`) — log/comment may say “encrypted”; **code is Base64**. `form_fill_request` with `form_url` + `fields`.

Single mutable `vaultSession`. **No `afterConnectionClosed`.** Send failure in `VaultGatewayAdapter` may **only log** (workflow can stick in `WAITING_FOR_VAULT_RESPONSE`). Missing session **does** publish a failure event from the handler.

**In-repo mock:** `mock-vault/vault_sim.py` connects to `ws://localhost:8081/vault-websocket`. Demo / e2e.

**FILL_FORM default URL:** `http://127.0.0.1:9000/register` (`VaultEvaluationCommandFactory`, Adapter `DEMO_FORM_URL`). Target: `demo-forms/`.

### B. Adapter local PII store

`PiiVaultStore` (`vault_store.py`): Fernet encryption to `app/data/pii_vault.json`. Refs `vault://pii/{fieldType}/{token}`. Resolve via `POST /vault/resolve` (localhost-only) for mock-vault FILL_FORM.

This is **not** the same component as the external Vault.

---

## 16. Install Directory / pairing

**Implemented optionally.**

| Piece | Status |
|---|---|
| `install-directory/server.py` | Mock HTTP directory, default port **8010** |
| APIs | `POST /api/pair/start`, `POST /api/pair/complete`, `GET /api/installs/{id}`, `GET /api/pair/{code}`, `GET /pair?code=` |
| Adapter client | `install_directory_client.py` if `INSTALL_DIRECTORY_URL` set |
| `PairingService` | Wired into `send_action` and session register |
| `PairingWatcher` | Started always; **exits immediately** if URL unset |
| Fallback | `vault_config.json` `userInstallId` when directory is None |

Storage: SQLite `install-directory/data/directory.sqlite3`; Adapter pairing file `app/data/pairing.json`.

**Not** in docker-compose. Port **8010** also used by Gemini POC MCP in `.gemini/settings.json` — collision risk.

---

## 17. Continuation architecture

**Bridge:** `NotifyAgentCommand` → `ContinuationRegistry` (implements `WorkflowContinuationService`) keyed by `ConnectorType`.

**Adapter:** webhook or `PollingWorker` → thin continuation wrappers → `ContinuationService.handle` → `WakeDispatcher` → provider + SSE.

Default Adapter: `CONNECTOR_TYPE=WEBHOOK`, `CONNECTOR_CONTEXT=http://127.0.0.1:8000/webhook/bridge`.

---

## 18. Webhook continuation

**Bridge:** `WebhookContinuation` + `WebhookTransport` — **Implemented**. HMAC-SHA256 required (`WEBHOOK_SECRET` missing → `error(...)`). Headers: `X-Webhook-Signature` (`sha256=` hex), `X-Webhook-Timestamp`, `X-Webhook-Nonce`. Payload `timestamp.nonce.body`.

**Adapter HTTP MCP:** verifies signature + in-memory nonce replay (`webhook_signature.py`).

**Adapter stdio FastAPI:** **does not verify HMAC**.

Body: `WebhookNotification(workflowId, requestId, status, message)`. `status` is **workflow state name**, not necessarily `StatusType`.

---

## 19. Polling continuation

**Split implementation:**

| Side | Status |
|---|---|
| Bridge `PollingContinuation` | **Stub** (`// todo:`) — `continueWorkflow` only logs |
| Adapter `PollingWorker` | **Implemented** — polls `GetActionStatus` every 2s default, timeout 120s, for pending workflows with `connectorType==POLLING` |
| Adapter `get_action_status` MCP | short wait loop (20s) — separate from PollingWorker |

When `CONNECTOR_TYPE=POLLING`, Bridge notify is a no-op; Adapter worker observes status changes.

---

## 20. Channel continuation

**Bridge `ChannelContinuation`:** **Implemented** — HTTP POST via `HttpChannelTransport` (no HMAC).

**Dead:** `connectors/channel/ChannelTransport.kt` — duplicate, no callers.

**Adapter Claude path** typically uses WEBHOOK to Adapter, then Adapter POSTs to Claude Channel `/wake` or `/continuation/{id}`. Bridge CHANNEL connector is a **generic HTTP POST of `NotifyAgent`**, not Claude-specific.

---

## 21. Thread continuation

**Stub** — `ThreadContinuation.kt` logs + `// todo: resume the existing conversation thread`. Not part of the live default flow.

---

## 22. Claude integration

| Piece | Status |
|---|---|
| MCP tools via Adapter | Implemented |
| `claude-channel/server.ts` (`bridge-wake`) | Implemented |
| HTTP `GET /health`, `POST /wake` | Implemented |
| MCP notification `notifications/claude/channel` | Implemented |
| Tool `get_continuation_context` | Implemented |
| Register with Adapter `/continuation/register` | Implemented (HTTP MCP mode) |
| `ClaudeProvider` | Implemented; SSRF allowlist `claude_url_allowlist.py` |

`.mcp.json` starts `bridge-wake` with `ADAPTER_BASE_URL=http://127.0.0.1:8000`.

---

## 23. OpenAI integration

| Piece | Status |
|---|---|
| `openai-client/client.py` | Implemented local chat client |
| Conversations + Responses APIs | Implemented |
| `OpenAIProvider` wake `responses.create(conversation=...)` | Implemented |
| SSE subscribe | Implemented |
| Requires `OPENAI_API_KEY` | External dependency |

---

## 24. Gemini integration

| Piece | Status |
|---|---|
| `gemini-client/client.py` | Implemented |
| Interactions API `previous_interaction_id` | Implemented |
| `GeminiProvider` | Implemented |
| `gemini-bridge-hooks` | Implemented hooks + **explicit POC** (`poc-mcp-server.py` port 8010) |
| Requires Gemini/Google API key | External |

---

## 25. SSE

**Endpoint:** `GET /events?platform&sessionId&token`  
**Notifier:** `SseClientNotifier` — one subscriber per `(platform, sessionId)`  
**Events observed in code:** `connected`, `workflow.updated`, `vault.paired`  
**Auth:** `sseToken` from `POST /sessions/register`  
**Limits:** `ADAPTER_MAX_SSE_CONNECTIONS`, `ADAPTER_SSE_QUEUE_MAXSIZE` (defaults mentioned in Adapter code: 100 connections, queue 32 — **verify defaults in those files if citing numbers**; code uses env with defaults).

---

## 26. Security mechanisms that are ACTUALLY implemented

| Mechanism | Where | Notes |
|---|---|---|
| Context separation (architecture) | Adapter/Bridge/Vault split | Design; not a crypto protocol |
| Action-type validation | `ActionService` | PAYMENT/TRANSACTION/FILL_FORM |
| FILL_FORM vault:// requirement | Adapter sanitize + Bridge validate | |
| Local Fernet PII store | `PiiVaultStore` | Adapter-local, not the external Vault |
| Bearer `ADAPTER_AUTH_TOKEN` | HTTP MCP middleware only | **Disabled if token unset**; stdio FastAPI **unprotected** |
| HMAC webhook | Bridge outbound; Adapter HTTP MCP inbound | stdio inbound **skips** |
| Webhook replay window + nonce | Adapter `webhook_signature.py` | in-memory nonces |
| Claude wake URL allowlist | localhost http `/wake` or `/continuation/{uuid}` | SSRF mitigation, local-only |
| `/vault/resolve` localhost-only | MCP HTTP | |
| Session bind `ensure_bound` | SQLite session registry | 403/conflict on mismatch |
| SSE token | session registry | |
| Pending workflow TTL/capacity | Adapter memory | |
| Secrets in `.env` | convention | `.env` not audited as committed; **not verified** |

**Not implemented in Bridge Kotlin:** TLS, gRPC auth, JWT/OAuth, WebSocket auth, Guardian auth, encryption of payment payload (Base64 only).

**Do not call Base64 encryption.**

---

## 27. Error handling

- Invalid action type / FILL_FORM plaintext secrets → gRPC `ActionResponse` status `FAILED` (empty requestId).
- Workflow init exception after action persist → gRPC `INTERNAL`; possible orphan action.
- Guardian HTTP failure → treated as reject event.
- Vault missing session → failure event from WS handler send path.
- Vault adapter exception on send → **may only log**.
- Kafka publish failure → log only.
- Unknown connector type on init → exception via `toConnectorType()`.
- Adapter webhook unknown requestId → 404.
- HMAC fail (HTTP MCP) → 401.
- Pairing required → MCP JSON pairing payload, not Bridge call.
- Session conflict → error dict from `send_action`.

---

## 28. Idempotency

| Layer | What exists |
|---|---|
| Action create | 2-minute identical request reuse (`ActionService.processAction`) |
| SendAction workflow | reuse workflow by `request_id` |
| Event processing | `shouldProcessEvent` ignores events for wrong state |
| Command-level | **Not implemented** (`lastExecutedCommand` unused) |
| Webhook nonce | Adapter HTTP MCP only |
| Kafka consumer | at-least-once + ignore duplicate-stage events |

---

## 29. Recovery

`WorkflowRecoveryScheduler.recoverOnStartup` on `ApplicationReadyEvent` only.

`WorkflowEngine.resume` is **state-driven**, not fake Kafka replay:

- RECEIVED → transition + VerifyAgent
- WAITING_FOR_GUARDIAN → VerifyAgent again
- WAITING_FOR_VAULT_RESPONSE → resend vault eval
- IN_PROGRESS → no-op
- terminal → no-op

**No periodic recovery.** Adapter pending map **not recovered**.

---

## 30. Configuration / environment variables

### Bridge (`application.properties` + code)

| Name | Default / note |
|---|---|
| `POSTGRES_DB` | `bridge_db` |
| `POSTGRES_USER` | `user` |
| `POSTGRES_PASSWORD` | empty |
| `PORT` | `8081` (Spring HTTP) |
| Kafka bootstrap | `localhost:9092` hardcoded in properties |
| `WEBHOOK_SECRET` | **required** for webhook send |
| gRPC port | **50051 hardcoded**, no env |
| Guardian URL | **hardcoded** `localhost:8001` |

`EnvLoader` copies `agent-adapter/.env` into system properties if unset.

### Adapter (non-exhaustive, actually read)

`MCP_TRANSPORT`, `ADAPTER_HOST` (`0.0.0.0`), `ADAPTER_PORT` (`8000`), `ADAPTER_PUBLIC_BASE`, `DEMO_FORM_URL`, `ADAPTER_AUTH_TOKEN`, `WEBHOOK_SECRET`, `WEBHOOK_REPLAY_*`, `CONNECTOR_TYPE`, `CONNECTOR_CONTEXT`, `ADAPTER_POLL_*`, `ADAPTER_PAIR_POLL_*`, `ADAPTER_PENDING_WORKFLOW_TTL_SECONDS`, `ADAPTER_MAX_PENDING_WORKFLOWS`, `ADAPTER_MAX_SSE_CONNECTIONS`, `ADAPTER_SSE_QUEUE_MAXSIZE`, `SESSION_REGISTRY_TTL_SECONDS`, `INSTALL_DIRECTORY_URL`, `VAULT_STORE_KEY`, `OPENAI_*`, `GEMINI_*` / `GOOGLE_API_KEY`.

### Others

Install Directory: `INSTALL_DIRECTORY_HOST/PORT/PUBLIC_BASE`, `DEFAULT_VAULT_SERVICE_URL`.  
Claude Channel: `ADAPTER_BASE_URL`, `CHANNEL_PORT`.  
Clients: `BRIDGE_MCP_URL`, `BRIDGE_EVENTS_URL`, `*_BRIDGE_AGENT_ID`.

---

## 31. Tests / mocks / demos

| Item | Kind |
|---|---|
| `guardian-mock/` | Mock Guardian |
| `mock-vault/` | Mock Vault WS client |
| `demo-forms/` | Demo HTML form server :9000 |
| `install-directory/` | Mock pairing directory |
| `gemini-bridge-hooks` POC | Fake MCP :8010 |
| `agent-adapter/app/test_*.py` | Manual e2e, need live stack |
| `bridge-sdk/tests/run_tests.py` | SDK tests (not a Bridge integration suite) |
| Kotlin unit tests | **Not Present** |

No automated CI test results were verified in this audit. **Do not invent pass rates.**

---

## 32. Known bugs / inconsistencies

1. `WORKFLOW_COMPLETED` / `WORKFLOW_FAILED` ignored after terminal transition (state gate vs publish order).
2. `IN_PROGRESS` unreachable in live path; recovery empty; completed/failed handlers assume it.
3. `WAIT_FOR_VAULT_RESPONSE` step unused; `NOTIFY_AGENT` step overwritten to `FINISHED` on terminal transition.
4. `lastExecutedCommand` / `WorkflowCommandType` unused.
5. `ActionEntity.contextJson` unused.
6. `GetActionStatus` omits `updated_at`.
7. Kafka property `group-id=bridge-group` vs listener `workflow-engine`.
8. `@EnableScheduling` without schedules; comments about heartbeats are false.
9. Guardian `reportOutcome` / `verifyAgentSync` dead.
10. Vault send exception may hang workflow; WS session not cleared on close; single-session.
11. Base64 labeled “encrypted” in comments/logs.
12. HMAC gap: stdio FastAPI webhook unsigned.
13. Bearer auth gap: stdio FastAPI unsigned; auth off if token unset.
14. gRPC hardcoded insecure localhost.
15. Workflow init failure after action persist → orphan action.
16. Adapter pending workflows not durable.
17. Port 8010 collision (Install Directory vs Gemini POC).
18. `requirements.txt` omits `httpx` / `python-dotenv` / `pydantic` despite imports.
19. Root `README.md` outdated (gRPC-only instructions).
20. `SendAction` description still tells clients to poll even when webhook is primary.

---

## 33. Partial implementations

- Recovery (startup only; IN_PROGRESS unimplemented).
- Polling (Adapter yes, Bridge connector stub).
- Auth/HMAC (transport-dependent).
- Channel connector (Bridge HTTP POST exists; default path is Adapter webhook + Claude Channel).
- Guardian (auth used; reporting unused; mock service).
- Vault (prototype WS protocol; mock client).
- Pairing (optional env; mock directory).

---

## 34. TODO / stub functionality

- `PollingContinuation.kt` `// todo:`
- `ThreadContinuation.kt` `// todo:`
- `ContinuationProvider.resolve` ABC `NotImplementedError` (base class only; `DefaultContinuationProvider` used)

---

## 35. Future work (inferred from stubs/gaps; not claimed as implemented)

- Real THREAD continuation.
- Bridge-side POLLING connector (or document that polling is Adapter-only).
- Durable Adapter pending-workflow store.
- gRPC TLS and authentication.
- WebSocket authentication and multi-Vault sessions.
- Periodic recovery / command idempotency.
- Wire Guardian `reportOutcome`.
- Replace Base64 with real payload protection if required.
- Production Guardian/Vault (replace mocks).
- Automated test suite.
- Docker images for Bridge/Adapter (**Not Present**).

---

## Capability table

| Capability | Status | Evidence | Notes |
|---|---|---|---|
| gRPC `SendAction` async accept | Implemented | `BridgeServiceImpl.sendAction` | Returns RECEIVED immediately |
| gRPC `GetActionStatus` | Implemented | `BridgeServiceImpl.getActionStatus` | No `updated_at` |
| Action persistence | Implemented | `ActionEntity`, `ActionService` | |
| Workflow persistence | Implemented | `WorkflowEntity`, `WorkflowInitializationService` | |
| Kafka workflow events | Implemented | `KafkaWorkflowEventPublisher`, `WorkflowEventConsumer` | topic `workflow-events` |
| WorkflowEngine state machine | Implemented | `WorkflowEngine`, handlers | IN_PROGRESS unused |
| Guardian verify | Implemented | `GuardianGatewayAdapter.verifyAgent` | hardcoded :8001; mock in repo |
| Guardian report | Stub / unused | `reportOutcome` no callers | |
| Vault WebSocket | Implemented | `VaultWebSocketHandler`, `WebSocketConfig` | prototype; mock client |
| Payment payload encryption | Not Present | Base64 in `sendRequestToVault` | comments may say encrypted |
| WEBHOOK continuation (Bridge) | Implemented | `WebhookContinuation` | HMAC required |
| CHANNEL continuation (Bridge) | Implemented | `ChannelContinuation` | no HMAC |
| POLLING continuation (Bridge) | Stub | `PollingContinuation` | |
| THREAD continuation (Bridge) | Stub | `ThreadContinuation` | |
| Adapter MCP `send_action` | Implemented | `mcp_server.py` | |
| Adapter MCP `store_pii` | Implemented | `mcp_server.py` | |
| Adapter MCP `get_action_status` | Implemented | short poll loop | |
| Adapter webhook ingress | Partial | HMAC on HTTP MCP only | stdio skips HMAC |
| Adapter PollingWorker | Implemented | `polling_worker.py` | used if CONNECTOR_TYPE=POLLING |
| Claude Channel wake | Implemented | `claude-channel/server.ts`, `ClaudeProvider` | |
| OpenAI Responses wake | Implemented | `openai_provider.py` | needs API key |
| Gemini Interactions wake | Implemented | `gemini_provider.py` | needs API key |
| SSE | Implemented | `GET /events`, `SseClientNotifier` | |
| Pairing / Install Directory | Partial | optional `INSTALL_DIRECTORY_URL`; mock server | |
| Adapter local PII vault | Implemented | `vault_store.py` Fernet | demo/local |
| bridge-sdk | Implemented | `bridge-sdk/` | not imported by Adapter |
| Bearer auth | Partial | HTTP MCP only; optional | |
| HMAC + replay protection | Partial | Bridge send + HTTP MCP verify | |
| SSRF allowlist (Claude) | Implemented | `claude_url_allowlist.py` | localhost only |
| TLS | Not Present | insecure gRPC/WS/HTTP localhost | |
| JWT / OAuth | Not Present | | |
| Agent Notification Service | Not Present | | |
| Startup workflow recovery | Partial | `WorkflowRecoveryScheduler` | once; IN_PROGRESS no-op |
| Periodic recovery | Not Present | no `@Scheduled` | |
| Command idempotency field | Not Present | unused column | |
| Kotlin unit tests | Not Present | | |
| Dockerized Bridge/Adapter | Not Present | compose is infra only | |
| Production Guardian | Not Present | `guardian-mock` | |
| Production Vault | Not Present | `mock-vault` | |

---

## Verdict

The current repository implements a **working local prototype** of: MCP → gRPC → Kafka workflow → Guardian mock → Vault mock → webhook/SSE/provider wake, with optional pairing and a Python SDK consumer.

It does **not** implement production security (TLS, gRPC auth, WS auth), a real Guardian/Vault, Bridge-side polling/thread continuation, durable Adapter workflow mapping, or an automated verification suite.
