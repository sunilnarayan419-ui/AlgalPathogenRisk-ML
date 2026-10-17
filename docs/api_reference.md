# API

Interactive docs: `/docs` (Swagger) and `/redoc`. Errors: 400 unreadable body, 404 missing resource/artifact,
409 duplicate name or batch-confounded contrast, 413 too large, 422 invalid input, 500 generic (details only in logs).

## Health and readiness
| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness only; `risk_model_loaded` is always false (no validated risk model exists) |
| GET | `/ready` | Component status: model artifact loaded or not (with reason), `risk_model_validated: false`, GEO file present |

## Datasets and QC
| GET/POST | `/api/v1/datasets`, `/api/v1/datasets/audit`, `/{id}` | list; audit a raw TSV body and record its checksum; detail |
| GET | `/v1/datasets/GSE128981/audit` | legacy metadata audit |
| POST | `/v1/expression-matrices/validate` | legacy FPKM-matrix QC report (raw body, max 25 MB) |

## Experiments and analysis
| POST | `/api/v1/experiments/design` \| `power-analysis` \| `randomize` \| `analyze` | planning and Welch analysis |
| POST | `/api/v1/analysis/differential-expression` | log2-FPKM OLS + BH on a posted genes x samples matrix (<= 5000 x 200); 409 if contrast is batch-confounded |

## Networks
| GET | `/api/v1/networks/status` | module status |
| POST | `/api/v1/networks/summary` | summary (+ optional neighbourhood) of a posted edge list; provenance fields required; duplicates -> 422 |

## Models
| GET/POST | `/api/v1/models/status`, `/evaluate` | availability; grouped genotype baseline |
| GET | `/api/v1/models/current` | metadata of the persisted artifact; 404 if none |
| POST | `/api/v1/models/train-demo` | trains on **synthetic** data, persists to `ALGAL_MODEL_DIR` |
| POST | `/api/v1/models/predict` | `{"records":[{"f0":0.1,...}]}`; 404 no artifact, 422 schema mismatch |
| POST | `/api/v1/models/register-current` | records the artifact in SQL (idempotent on checksum) |
| GET | `/api/v1/models/versions` | registered model versions |

## Economics (hypothetical inputs)
| POST | `/api/v1/economics/break-even` \| `sensitivity` \| `uncertainty` | scenario math; Monte Carlo net benefit with EVPI |

```powershell
curl -X POST http://127.0.0.1:8000/api/v1/models/train-demo -H "Content-Type: application/json" -d '{"seed":1}'
curl http://127.0.0.1:8000/ready
curl -X POST http://127.0.0.1:8000/api/v1/economics/uncertainty -H "Content-Type: application/json" `
  -d '{"p":[0,0.4],"L":[100,100],"C":[10,10],"e":[0.5,0.5],"n":5000}'
```
Scores returned by `/predict` are uncalibrated and are not validated pathogen probabilities.
**Status:** service logic behind the new routes was executed; the HTTP layer (`tests/test_ml_api.py`) was not run in the authoring sandbox.
