from typing import Any

from fastapi import APIRouter, Depends, Query, status
from pymongo.database import Database
from sqlalchemy.orm import Session

from app.core.database import get_db, get_mongo_db
from app.core.security import get_current_user
from app.triage.schemas import (
    TriageFinishResponse,
    TriageQueueResponse,
    TriageSubmitRequest,
    TriageSubmitResponse,
)
from app.triage.service import (
    finish_doctor_triage_ticket,
    get_doctor_triage_queue,
    submit_triage,
)

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


@router.get(
    "/queue",
    response_model=TriageQueueResponse,
    status_code=status.HTTP_200_OK,
    summary="Fila de atendimentos abertos da especialidade do médico",
)
def get_triage_queue_endpoint(
    limit: int = Query(default=20, ge=1, le=50, description="Quantidade máxima de itens a retornar"),
    offset: int = Query(default=0, ge=0, description="Deslocamento para paginação"),
    current_user: dict[str, Any] = Depends(get_current_user),
    pg_db: Session = Depends(get_db),
    mongo_db: Database = Depends(get_mongo_db),
) -> TriageQueueResponse:
    """Retorna os tickets abertos (status WAITING) correspondentes à especialidade médica do usuário logado."""
    result = get_doctor_triage_queue(
        current_user=current_user,
        pg_db=pg_db,
        mongo_db=mongo_db,
        limit=limit,
        offset=offset,
    )
    return TriageQueueResponse(**result)


@router.patch(
    "/{ticket_id}/finish",
    response_model=TriageFinishResponse,
    status_code=status.HTTP_200_OK,
    summary="Finaliza um atendimento aberto da especialidade médica",
)
def finish_triage_endpoint(
    ticket_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
    pg_db: Session = Depends(get_db),
    mongo_db: Database = Depends(get_mongo_db),
) -> TriageFinishResponse:
    """Finaliza um atendimento aberto com atualização atômica e validação de especialidade."""
    result = finish_doctor_triage_ticket(
        ticket_id=ticket_id,
        current_user=current_user,
        pg_db=pg_db,
        mongo_db=mongo_db,
    )
    return TriageFinishResponse(**result)


