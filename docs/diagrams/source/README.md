# Diagram sources (current implementation)

These diagrams match **executable code** as of the 2026-09-16 audit. Do not copy older report figures if they show an Agent Notification Service, treat POLLING/THREAD as complete, or omit in-repo mocks.

| File | Report figure | Content |
|---|---|---|
| `01-architecture.mmd` | 6.1 | Runtime processes and protocols |
| `02-sequence.mmd` | 6.2 | WEBHOOK happy path |
| `03-workflow-states.mmd` | 8.1 | Live `WorkflowState` transitions |
| `04-erd.mmd` | 10.1 | JPA tables (logical `request_id` only) |
| `05-components.mmd` | 7.1 | Principal classes |

Render with Mermaid (CLI or live editor) and insert PNGs into Word with captions **below** figures.

Existing files `02-sequence.png`, `03-workflow.png`, `04-erd.svg` in the parent folder are **legacy** unless regenerated from these sources.
