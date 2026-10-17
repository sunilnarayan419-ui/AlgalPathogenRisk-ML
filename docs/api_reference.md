# API

Interactive docs at `/docs`. Original routes are kept (`/health`, `/v1/...`). New:

| Method | Path | Purpose |
|---|---|---|
| GET/POST | `/api/v1/datasets`, `/api/v1/datasets/audit`, `/{id}` | list; audit raw TSV body and record checksum; detail |
| POST | `/api/v1/experiments/design` \| `power-analysis` \| `randomize` \| `analyze` | planning and analysis |
| GET/POST | `/api/v1/models/status`, `/evaluate` | availability; genotype baseline |
| GET | `/api/v1/networks/status` | network module status |
| POST | `/api/v1/economics/break-even`, `/sensitivity` | scenario math |

```powershell
curl -X POST http://127.0.0.1:8000/api/v1/experiments/power-analysis -H "Content-Type: application/json" -d '{"endpoint":"continuous","effect_size_d":0.5}'
curl -X POST "http://127.0.0.1:8000/api/v1/datasets/audit?accession=GSE128981" --data-binary "@data\raw\file.tsv.gz"
```
Errors: 400 unreadable body, 413 too large, 422 invalid/unsupported, 409 duplicate name, 500 generic (details only in logs).
