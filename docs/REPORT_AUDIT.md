# REPORT AUDIT — The Bridge academic report vs current code

**Original report:** `/Users/yhd/Downloads/עותק של The_Bridge_Final_Report_HE_Polished.docx`  
**Compared against:** current repository (see `docs/CURRENT_IMPLEMENTATION_AUDIT.md`).  
**Do not overwrite the original report.**

Classification: **CORRECT** / **PARTIALLY CORRECT** / **OUTDATED** / **INCORRECT** / **UNSUPPORTED BY CURRENT CODE** / **MISSING FROM REPORT**.

XML fragments leaked into several Hebrew paragraphs of the extracted DOCX (Word corruption). Those are formatting defects, not architectural claims.

---

## Cover / metadata

| Item | Classification | Notes |
|---|---|---|
| Title, authors, advisor, CoralOS, מכון טל תשפ״ו | CORRECT | Preserve. Duplicate cover pages in the file. |
| English subtitle | CORRECT | |

---

## תקציר (Hebrew abstract)

**Classification: PARTIALLY CORRECT**

| Current statement | Problem | Evidence | Proposed replacement |
|---|---|---|---|
| Guardian and Vault as coordination targets | Implies production systems | Repo contains `guardian-mock/` and `mock-vault/` | State that integration **gateways** are implemented; runtime peers used in the prototype are **mocks** unless a real service is substituted. |
| “שכבת תיווך ואורקסטרציה מאובטחת” | Over-claims security | No TLS/gRPC auth/WS auth | “שכבת תיווך ואורקסטרציה שמממשת הפרדת הקשר ומנגנוני אבטחה **חלקיים** באב-טיפוס מקומי” |
| Two MCP tools implied later; abstract omits `store_pii` and pairing | Incomplete | `mcp_server.py` | Mention `store_pii` and optional pairing if space allows; do not list every endpoint. |
| Webhook as the completion path | CORRECT for default | `DefaultContinuationProvider` WEBHOOK | Keep; note polling is Adapter-side fallback. |

Abstract length is appropriate. Do not turn it into a TOC.

---

## English Abstract

**Classification: PARTIALLY CORRECT**

Same issues as Hebrew abstract: “secure Vault” / Guardian without mock distinction; no pairing/`store_pii`; “secure” without TLS caveat.

**Proposed replacement (substance):** keep structure; add that Guardian and Vault **interfaces** are implemented and that the repository’s runnable peers are **mock services**; call the system a **functional prototype**.

---

## תודות

**CORRECT** — preserve.

---

## תוכן עניינים / רשימת איורים / רשימת טבלאות

**PARTIALLY CORRECT / OUTDATED**

- Manual page numbers (30, 34, …) will be stale after edits. Use Word automatic TOC/captions.
- Figure 6.1 vs “איור 1” inconsistency in body.
- Chapter 8 body contains a stray heading “10. מודל הנתונים והתמדה”.
- Missing 14.3; 15 starts at 15.1; “בדיקות והרצות” heading lost its chapter number in the extract.
- Duplicate OpenAI/Gemini paragraphs (9.2).

---

## 1. מבוא

**Classification: CORRECT** (motivation and core idea).

Minor: “Backend מתמשכת” is fair for Bridge+PostgreSQL; Adapter pending state is **not** durable — say so later, not necessarily here.

---

## 2. רקע תאורטי

| Subsection | Classification | Notes |
|---|---|---|
| 2.1 Agents + tools | CORRECT | |
| 2.2 Prompt injection / Context Separation; Louck et al. | CORRECT if citation is kept as supplied | arXiv:2505.12490 is in the original bibliography — keep; do not invent extra papers. |
| 2.3 MCP — “הסוכן רואה שני כלים: send_action ו-get_action_status” | **INCORRECT** | Third tool `store_pii`. Replacement: three tools. |
| 2.4 EDA / Kafka | CORRECT | |
| 2.5 Long-running workflow | CORRECT | |

**MISSING:** short background on gRPC, Protobuf, WebSocket, SSE, HMAC — used later. Add with official docs already in bibliography or `[REFERENCE REQUIRED]`.

---

## 3. הגדרת הבעיה ומטרות

**3.1 Problem: CORRECT**

**3.2 Goals: CORRECT** (including webhook-not-polling as primary).

**3.3 Scope: PARTIALLY CORRECT / INCORRECT**

| Statement | Why wrong | Evidence | Replacement |
|---|---|---|---|
| Guardian and Vault “אינם במאגר הקוד” | **INCORRECT** | `guardian-mock/`, `mock-vault/` | They are **external to Bridge’s process** and **mocked in-repo**. Bridge does not implement a production Vault/Guardian. |
| “ניהול מנגנוני התעוררות מגוונים (Webhooks, Polling, SSE)” | PARTIALLY CORRECT | Bridge POLLING is stub; Adapter PollingWorker is real; SSE is Adapter | Distinguish Bridge connectors vs Adapter. |
| Pairing + Install Directory + Pairing Watcher “נכללו” | PARTIALLY CORRECT | Optional; mock directory; watcher no-ops without URL | “מומשו באב-טיפוס, מותנים ב-`INSTALL_DIRECTORY_URL`” |

---

## 4. דרישות

**4.1 FR table: PARTIALLY CORRECT**

| ID | Classification | Comment |
|---|---|---|
| FR-1 send_action | CORRECT | Also `store_pii` missing as FR |
| FR-2 gRPC | CORRECT | |
| FR-3 persist Action+Workflow | CORRECT | |
| FR-4 Guardian then Vault | CORRECT (with mock peers) | |
| FR-5 persist status/state/step | PARTIALLY CORRECT | `WAIT_FOR_VAULT_RESPONSE` step unused; `last_executed_command` unused |
| FR-6 Kafka or Vault events | CORRECT | |
| FR-7 webhook on finish | PARTIALLY CORRECT | Only if `connector_type=WEBHOOK` (default). POLLING: Bridge notify is stub |
| FR-8 wake + notify client | CORRECT for implemented providers | |
| FR-9 get_action_status | CORRECT | |
| FR-10 pairing QR PAIRING_REQUIRED | PARTIALLY CORRECT | Optional Install Directory; blocks when service configured and unpaired |
| FR-11 FILL_FORM vault:// | CORRECT | |

**MISSING FR:** `store_pii`; HMAC/auth as requirements vs implemented-optional.

**4.2 NFR: PARTIALLY CORRECT**

- “מידע רגיש יישמר ב-Vault” — two vaults: Adapter Fernet store **and** external Vault mock. Clarify.
- Recovery NFR overstates: startup-only, IN_PROGRESS unimplemented.
- Performance NFR (“טיפוסית ויעילה”) — **UNSUPPORTED BY CURRENT CODE** (no measurements). Soften to design intent.

---

## 5. חלופות ושיקולי תכנון

| Section | Classification |
|---|---|
| 5.1 Direct agent-to-sensitive-systems rejected | CORRECT |
| 5.2 Long request-response rejected | CORRECT |
| 5.3 Polling not primary | CORRECT as design; **conflicts with 9.6** |
| 5.4 Webhook two-step continuation | CORRECT |
| 5.5 Adapter anti-corruption | CORRECT |
| 5.6 gRPC/Protobuf | CORRECT |
| 5.7 CHANNEL vs THREAD; THREAD stub | CORRECT |

**9.6 vs 5.3:** 9.6 claims “תמיכה מלאה במנגנון Polling”. That is **INCORRECT** for Bridge (`PollingContinuation` stub) and **PARTIALLY CORRECT** for Adapter.

---

## 6. ארכיטקטורה

**6.1 table: PARTIALLY CORRECT**

| Row | Issue |
|---|---|
| Guardian “External HTTP service” | Incomplete: mock is in repo |
| Vault “External WebSocket client” | Correct as topology; mock is in repo |
| Install Directory | Correct as mock; should be labeled **mock/demo** |
| Missing rows | `bridge-sdk`, `demo-forms`, local `PiiVaultStore` |

**6.2 responsibility split: CORRECT** as design.

**6.3 Happy path: CORRECT** if diagram matches webhook default. Old diagrams must be regenerated from code names.

Figure numbering “איור 1” vs list “איור 6.1”: fix.

---

## 7. תכנון מפורט

| Subsection | Classification | Notes |
|---|---|---|
| 7.1 packages, gRPC 50051 | CORRECT | Add HTTP 8081 |
| 7.2 ActionService idempotency 2 min | CORRECT | |
| 7.3 WorkflowInitializationService | CORRECT | |
| 7.4 Gateways | PARTIALLY CORRECT | Omit unused `reportOutcome` as if live |
| 7.5 Recovery “מונע תלות בזיכרון” | PARTIALLY CORRECT | Startup only; Adapter memory still lost; IN_PROGRESS no-op |

**MISSING:** `EnvLoader`, hardcoded Guardian, Kafka group-id mismatch.

---

## 8. מנוע Workflow

**Stray “10. מודל הנתונים” heading: OUTDATED formatting bug.**

| Claim | Classification | Replacement |
|---|---|---|
| States including IN_PROGRESS | PARTIALLY CORRECT | Enum exists; **live path never enters IN_PROGRESS** |
| Steps including WAIT_FOR_VAULT_RESPONSE | PARTIALLY CORRECT | Enum exists; **never assigned** |
| Events including WorkflowCompleted/Failed | PARTIALLY CORRECT | Published but **ignored** by validator |
| Commands / executor | CORRECT | |
| StatusType vs WorkflowState | PARTIALLY CORRECT | Agent does **not** currently receive IN_PROGRESS from Kotlin writers; proto has it; MCP poll loop waits on IN_PROGRESS anyway |
| “סטטוסים סופיים כגון RECEIVED, IN_PROGRESS…” | **INCORRECT** wording | RECEIVED is initial, not terminal. List actual written statuses. |

---

## 9. שכבת הסוכנים

| Claim | Classification | Notes |
|---|---|---|
| Two MCP tools only | **INCORRECT** | Add `store_pii` |
| Webhook + wake + SSE | CORRECT | |
| Claude Channel flow | CORRECT in HTTP MCP mode; continuation routes missing on stdio FastAPI | |
| OpenAI/Gemini paragraphs duplicated | formatting | Deduplicate |
| 9.5 WebhookContinuation default URL | CORRECT | |
| 9.6 “תמיכה מלאה ב-Polling” | **INCORRECT** | Adapter PollingWorker implemented; Bridge connector stub; timeout default **120s** not “120–300” unless env raised |
| PollingWorker every 2s | CORRECT default | `ADAPTER_POLL_INTERVAL_SECONDS` |

**MISSING:** `SdkProvider`; stdio vs HTTP transport security gap; in-memory pending workflows (mentioned later in 10.3 — good).

---

## 10. מודל נתונים

**Classification: PARTIALLY CORRECT**

- Fields listed match entities.
- `context_json` on actions and `last_executed_command` exist but **unused** — report presents them as active design.
- 10.3 Adapter memory limitation: **CORRECT**.

ERD must not invent FK if code has none.

---

## 11. ממשקי תקשורת

| Item | Classification |
|---|---|
| 11.1 SendAction/GetActionStatus | CORRECT |
| SendAction “יצירת פעולה ו-Workflow והחזרת … סטטוס ראשוני” | CORRECT; also idempotent reuse |
| 11.2 proto fields + timestamps | PARTIALLY CORRECT | `updated_at` not populated |
| 11.3 MCP table missing `store_pii`; get_action_status `updatedAt` | **INCORRECT** | Adapter returns requestId/status/resultData; no updatedAt from Bridge |
| 11.4 HTTP table | PARTIALLY CORRECT | Mixes Adapter HTTP-MCP, stdio subset, Claude Channel, Install Directory. Must split by process. |
| `/vault-websocket` | CORRECT | Spring :8081 |

---

## 12. אבטחה ופרטיות

This chapter is the largest over-claim relative to **transport gaps**.

| Subsection | Classification | Why |
|---|---|---|
| 12.1 Context Separation | CORRECT as architecture | Still demo PII on disk; mock Vault |
| 12.2 Mediation | CORRECT | |
| 12.3 Least privilege | PARTIALLY CORRECT | Design; WS `allowedOrigins=*`; no gRPC auth |
| 12.4 Bearer + session bind | PARTIALLY CORRECT | True for **HTTP MCP**. False for **stdio FastAPI**. Auth **off** if `ADAPTER_AUTH_TOKEN` unset. Session bind **CORRECT** when registry used. |
| 12.4.1 “כל בקשת HTTP נכנסת” | **INCORRECT** | Only `AdapterAuthMiddleware` on HTTP MCP ASGI |
| 12.5 HMAC + replay | PARTIALLY CORRECT | Bridge always signs if secret present (required). Adapter **HTTP MCP** verifies. **stdio webhook does not.** Nonces in-memory. |
| 12.6 SSRF allowlist | CORRECT for Claude wake | Localhost-only by design |
| 12.7 TTL/SSE limits | CORRECT if defaults match code | Cite env names |
| 12.7.3 SDK `load_adapter_env` | CORRECT for SDK, not Adapter core | |
| TLS | **MISSING FROM REPORT** (good — do not add as implemented) | Not Present |
| JWT/OAuth | not claimed | Correct silence |
| Base64 as encryption | not claimed in this chapter | Do **not** add; Vault comments are wrong |

**Proposed security chapter stance:** implemented prototype controls + explicit non-goals (no TLS, optional bearer, HMAC path-dependent).

---

## 13. בדיקות והרצות

**Classification: PARTIALLY CORRECT / UNSUPPORTED**

| Claim | Problem |
|---|---|
| Integration strategy table as expected results | Describes intended behavior, not recorded test evidence |
| “מסמך ההרצות שסופק” | **Not verified from current repository** (no attached run log in repo) |
| Recovery test “Scheduler טוען ומנסה להמשיך” | Overstates: `ApplicationReadyEvent`, not a periodic scheduler |
| Success metric “ללא polling מתמשך” | Conflicts with MCP `get_action_status` loop and optional PollingWorker |

**MISSING:** no Kotlin tests; e2e scripts are manual; do not invent pass/fail counts.

---

## 14. תוצאות, מגבלות ודיון

**14.1 Results: PARTIALLY CORRECT** — feasibility of the architecture is fair; “מאובטח” too strong.

**14.2 Contribution: CORRECT** as engineering contribution claims, if scoped to prototype.

**14.3: MISSING** (number skip).

**14.4 Discussion: CORRECT** (continuation on Adapter). **MISSING:** mock vs production, HMAC/stdio gap, dead WORKFLOW_COMPLETED handlers, two vaults, optional pairing.

---

## 15. עבודה עתידית

**Only 15.1 THREAD: PARTIALLY CORRECT** — THREAD stub is real future work, but incomplete chapter.

**MISSING future work that code actually needs:**

- Bridge POLLING connector or document Adapter-only polling
- TLS / gRPC auth / WS auth
- Durable Adapter pending store
- Command idempotency
- Wire Guardian report
- Automated tests
- Multi-vault sessions
- Replace mocks

---

## 16. סיכום

**PARTIALLY CORRECT**

Correct: no Agent Notification Service; webhook + Adapter wake; Context Separation intent; Kafka/Postgres.

Over-claim: “הגנה על מידע רגיש” without listing prototype limits.

The evolution paragraph (polling / Agent Notification Service → current split) is **historically useful** and matches code (that service does not exist). Keep as history, not as current architecture.

---

## מקורות

**Classification: PARTIALLY CORRECT**

Keep only sources actually cited. Original includes Louck et al., MCP, gRPC/Protobuf, Spring, Kafka, PostgreSQL, Anthropic Channels, OpenAI Responses, Gemini Interactions.

Problems:

- Entries [2][3][7][9] concatenate two URLs in one item.
- Access dates Aug 4, 2026 — keep if that is when students accessed; do not invent.
- Do **not** add fake papers.
- Add `[REFERENCE REQUIRED]` for WebSocket / SSE / HMAC RFCs if those are discussed in background.

---

## נספח א — מפת רכיבים

**PARTIALLY CORRECT** — classes exist. Label `PollingWorker` vs Bridge stub; `VaultStore` is Adapter Fernet, not external Vault.

---

## נספח ב — מילון

**CORRECT** overall. Clarify two vaults; Bridge SDK “לקוח Python ל-MCP”.

---

## נספח ג — משתני סביבה

**PARTIALLY CORRECT / MISSING**

Listed: ADAPTER_AUTH_TOKEN, WEBHOOK_SECRET, INSTALL_DIRECTORY_URL, CONNECTOR_TYPE, SESSION_REGISTRY_TTL, ADAPTER_PENDING_WORKFLOW_TTL.

Missing (used in code): MCP_TRANSPORT, ADAPTER_PORT, CONNECTOR_CONTEXT, POSTGRES_*, PORT, OPENAI/GEMINI keys, VAULT_STORE_KEY, poll intervals, gRPC has **no** env (hardcoded).

---

## Topic checklist (user-requested)

| Topic | Report vs code |
|---|---|
| Sync vs async | Report correctly async after SendAction. gRPC description still mentions polling. |
| SendAction | Immediate RECEIVED; idempotent reuse — report under-explains reuse. |
| Workflow Engine | Real; IN_PROGRESS/step unused issues omitted. |
| Kafka | Real topic `workflow-events`. |
| WorkflowState/Step | Enums listed as if all used. |
| Persistence | Postgres real; unused columns oversold. |
| Recovery | Oversold as general durability. |
| Guardian | Integration real; “not in repo” false; mock in repo. |
| Vault | WS real; mock in repo; second Fernet vault omitted in architecture table. |
| Webhook | Default path correct. |
| SSE | Real. |
| MCP | Missing `store_pii`. |
| gRPC/Protobuf | Real; `updated_at` unused. |
| Pairing / Install Directory | Present; not labeled mock/optional strongly enough. |
| bridge-sdk | Glossary only; missing from architecture. |
| Continuation | Correct split; CHANNEL vs Claude Channel easy to confuse. |
| Claude Channel | Largely correct. |
| OpenAI/Gemini | Correct; duplicated text. |
| Polling | **Internal contradiction** 5.3 vs 9.6. |
| Thread | Correctly stub. |
| Auth | Over-generalized. |
| TLS | Not claimed as implemented — keep that honesty. |
| HMAC | Over-generalized. |
| JWT/OAuth | Not claimed. |
| Replay | HTTP MCP only. |
| Encryption | Fernet local PII is real; payment WS is Base64. Report must not conflate. |
| SSRF | Claude allowlist real. |
| Secrets | .env convention; not verified gitignore from this pass. |
| userInstallId | Real field + pairing/fallback. |
| Mocks vs production | Insufficiently distinguished. |

---

## Priority corrections for the rewritten report

1. Label **A implemented / B partial / C external / D mock / E future** everywhere it matters.
2. Three MCP tools.
3. Two vaults.
4. Guardian/Vault mocks in-repo.
5. Polling: Adapter worker vs Bridge stub.
6. Security: HTTP MCP vs stdio.
7. Workflow: unused IN_PROGRESS, unused completed-event handlers.
8. Recovery: startup only.
9. Do not invent tests, metrics, or extra citations.
10. Fix numbering, duplicates, and figure/table captions.
