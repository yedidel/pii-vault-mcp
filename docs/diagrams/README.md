# Agent Layer Diagrams

High-resolution architecture artifacts for `pii-vault-mcp`.

| File | Description |
|---|---|
| [01-architecture.svg](./01-architecture.svg) / [PNG](./01-architecture.png) | System architecture (clients → Adapter → Bridge → Vault) |
| [02-sequence.svg](./02-sequence.svg) / [PNG](./02-sequence.png) | Sequence: send_action → webhook → wake |
| [03-workflow.svg](./03-workflow.svg) / [PNG](./03-workflow.png) | Bridge WorkflowState / WorkflowStep |
| [04-erd.svg](./04-erd.svg) / [PNG](./04-erd.png) | ERD: `actions` + `workflows` |

PNGs are rendered at ~3200px width for slides/docs.

## Regenerate PNGs

```bash
cd docs/diagrams
rsvg-convert -w 3200 01-architecture.svg -o 01-architecture.png
rsvg-convert -w 3200 02-sequence.svg -o 02-sequence.png
rsvg-convert -w 3200 03-workflow.svg -o 03-workflow.png
rsvg-convert -w 3200 04-erd.svg -o 04-erd.png
```
