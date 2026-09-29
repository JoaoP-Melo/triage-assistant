from typing import Any

from fastapi import APIRouter, Depends, status
from pymongo.database import Database

from app.core.database import get_mongo_db
from app.core.security import get_current_user
from app.triage.schemas import TriageSubmitRequest, TriageSubmitResponse
from app.triage.service import submit_triage

router = APIRouter(prefix="/triage", tags=["triage"])


@router.post(
    "/submit",
    response_model=TriageSubmitResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submissão de triagem de sintomas do paciente",
)
def submit_triage_endpoint(
    payload: TriageSubmitRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
    mongo_db: Database = Depends(get_mongo_db),
) -> TriageSubmitResponse:
    """Orquestra a submissão de sintomas do paciente, protegida por autenticação JWT."""
    result = submit_triage(
        payload=payload,
        current_user=current_user,
        mongo_db=mongo_db,
    )
    return TriageSubmitResponse(**result)
