# REPORT_CHANGELOG — corrections from the original academic DOCX to `docs/FINAL_REPORT_HE.md`

Original: `/Users/yhd/Downloads/עותק של The_Bridge_Final_Report_HE_Polished.docx`  
New: `docs/FINAL_REPORT_HE.md`  
The original file was **not** overwritten.

---

## Framing and genre

- Kept academic structure (cover, bilingual abstracts, acknowledgements, background, requirements, alternatives, architecture, implementation, security, testing, discussion, future work, bibliography, appendices).
- Added an explicit A/B/C/D/E classification (implemented / partial / external / mock / future) so prototype pieces are not narrated as production services.
- Added Word-conversion formatting notes (A4, David/Arial, heading sizes, automatic TOC/captions) instead of stale manual page numbers.

## Abstracts

- Hebrew and English abstracts rewritten for accuracy: three MCP tools, webhook as **default** path, prototype scope, Guardian/Vault **gateways vs in-repo mocks**.
- Softened “מאובטחת/secure” to architecture + partial prototype controls.
- English abstract is professional prose, not a word-for-word calque.

## Introduction / background

- Preserved motivation, Context Separation, Louck et al. [1], EDA, long-running workflows.
- Corrected MCP: **three** tools (`store_pii` added).
- Added short background on gRPC/Protobuf, WebSocket, SSE, mediation, with `[REFERENCE REQUIRED]` where a second official URL should be locked at submission time.
- Did **not** invent citations.

## Problem / scope

- Scope no longer claims Guardian/Vault are absent from the repository.
- States clearly: mocks live in-repo; production services are out of scope.
- Pairing/Install Directory marked optional + mock.

## Requirements

- FR table annotated with actual implementation status.
- Added FR-1b for `store_pii`.
- NFR performance claim removed as unsupported (no measurements).
- Recovery NFR narrowed to startup-only.

## Alternatives

- Preserved design rationale (direct access, long RPC, webhook, Adapter, gRPC).
- Resolved contradiction: §5.3 vs old §9.6 — Bridge POLLING is stub; Adapter PollingWorker is real; defaults 2s / 120s.

## Architecture

- Regenerated diagrams from **current class/protocol names** under `docs/diagrams/source/`.
- Added mocks, demo-forms, bridge-sdk, local PiiVaultStore.
- Stated Agent Notification Service **does not exist** (kept as historical note in the conclusion only).

## Detailed design

- Documented ports **8081 + 50051**, `EnvLoader`, hardcoded Guardian URL, insecure gRPC.
- Documented unused `reportOutcome` / `verifyAgentSync`.
- Recovery described as `ApplicationReadyEvent`, not a periodic scheduler.
- Documented orphan-action risk on workflow init failure.
- Documented Adapter stdio vs HTTP process split.

## Workflow engine

- Listed enums completely, then stated which values are **unused in the live path** (`IN_PROGRESS`, step `WAIT_FOR_VAULT_RESPONSE`).
- Documented that `WORKFLOW_COMPLETED` / `WORKFLOW_FAILED` are published then **ignored** by `shouldProcessEvent`.
- Corrected agent-visible statuses actually written by Kotlin.
- Documented unused `last_executed_command`.
- Kafka topic `workflow-events`, consumer group `workflow-engine`.

## Agents / continuation

- Removed duplicate OpenAI/Gemini paragraphs.
- Added `SdkProvider` / bridge-sdk relationship (Adapter does not import the SDK).
- Claude Channel vs Bridge `CHANNEL` connector distinguished.
- HMAC/stdio gap documented with continuation chapter cross-links.

## Data model

- Same columns as JPA; unused columns labeled unused.
- No invented FK; logical `request_id` only.
- Adapter in-memory pending map retained as a limitation (was already in the original — kept).

## APIs

- MCP table includes `store_pii`; dropped false `updatedAt` on GetActionStatus.
- HTTP table split **by process** (Adapter HTTP MCP vs stdio vs Channel vs Directory vs Bridge WS).

## Security

- Largest rewrite: only mechanisms present in code.
- Bearer: HTTP MCP only; disabled if token unset.
- HMAC + replay: HTTP MCP inbound; Bridge outbound requires secret; stdio skips verify.
- SSRF allowlist kept as Claude-local.
- Fernet local PII vs Base64 payment payload — **Base64 is not called encryption**.
- TLS/JWT explicitly not implemented.
- Least-privilege presented as design, with prototype violations (open WS origins, open gRPC).

## Testing

- Removed implication of a supplied signed run log in the repo.
- No invented pass rates or timings.
- Listed actual scripts and the absence of Kotlin unit tests.

## Discussion / future work

- Added §14.3 limitations (was a skipped number in the original).
- Expanded future work beyond THREAD only, matching stubs and gaps.
- Discussion compares objectives and [1][2] without claiming a formal security proof.

## Conclusion

- Summarizes **implemented** prototype; does not claim future work as done.
- Keeps the architectural evolution paragraph (no Agent Notification Service).

## Bibliography

- Kept original genuine sources; split concatenated URL blobs.
- Marked items needing a pinned version/access date.
- No new fabricated papers.

## Appendices

- Component map labeled A/B/D/E.
- Glossary distinguishes two vaults.
- Env table expanded with hardcoded ports and `MCP_TRANSPORT`.
- Dropped dumping source code.

## Not changed in application code

Per instructions, **no production code was modified** to make the report true. Bugs (dead completed-event handlers, HMAC stdio gap, etc.) are documented, not silently fixed.

## DOCX

`pandoc` was not available. **No** `The_Bridge_Final_Report_Corrected.docx` was generated, to avoid a broken RTL file. Convert `FINAL_REPORT_HE.md` in Word using the header instructions.
