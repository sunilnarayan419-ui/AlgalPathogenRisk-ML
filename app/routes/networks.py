from fastapi import APIRouter, HTTPException

from app.schemas_v1 import NetworkSummaryRequest
from app.services import analysis_service as svc

router = APIRouter(prefix="/api/v1/networks", tags=["networks"])


@router.get("/status")
def status():
    return {"available": True, "external_interaction_databases_configured": [],
            "supported_loaders": ["STRING links[.detailed] (app.networks.loaders.load_string_links)",
                                  "BioGRID TAB3 (app.networks.loaders.load_biogrid_tab3)"],
            "note": ("Loaders run offline via scripts/build_network.py on files you download "
                     "yourself; no interaction data is bundled or fetched by the API. Edges carry "
                     "source, version and evidence type. Centrality does not imply causation.")}


@router.post("/summary")
def summary(body: NetworkSummaryRequest):
    """Summarise a caller-supplied edge list (provenance required). Descriptive only."""
    try:
        return svc.network_from_payload(body.model_dump(exclude_none=True))
    except (svc.PayloadError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
