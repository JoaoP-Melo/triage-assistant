import logging
from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException, status
from pymongo.database import Database
from sqlalchemy.orm import Session

from app.auth.models import User
from app.classification.service import predict_triage
from app.triage.schemas import TriageSubmitRequest

logger = logging.getLogger(__name__)


def submit_triage(
    payload: TriageSubmitRequest,
    current_user: dict[str, Any],
    mongo_db: Database,
) -> dict[str, Any]:
    """Regra de negócio para submissão de triagem de sintomas de paciente.

    Fluxo:
    1. Valida se o usuário tem role == 'patient' (RBAC).
    2. Persiste o ticket inicial no MongoDB com status='WAITING' e triage_result=None.
    3. Executa a classificação clínica via pipeline híbrido (app.classification.service):
       - Tenta classificar via ML (XGBoost) com confiança mínima de 90%.
       - Se confiança < 90% ou falha do ML: aciona automaticamente o fallback via
         Assistente de IA (Groq LLM) em app.classification.ia.service.classify_with_llm.
       Ambos são chamadas internas Python, sem rota HTTP exposta.
    4. Atualiza o documento no MongoDB com o triage_result obtido.
    5. Retorna o JSON sanitizado com ticket_id, assigned_specialty, urgency_level e status.
    """
    if current_user.get("role") != "patient":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas pacientes podem submeter triagens.",
        )

    # 1. Payload do paciente exatamente como recebido (validado pelo schema)
    patient_input = payload.model_dump()

    # 2. Monta documento inicial
    ticket_doc = {
        "user_id": current_user["user_id"],
        "patient_input": patient_input,
        "triage_result": None,
        "status": "WAITING",
        "created_at": datetime.now(UTC),
    }

    # Inserção inicial no MongoDB
    insert_result = mongo_db["tickets"].insert_one(ticket_doc)
    ticket_id = str(insert_result.inserted_id)

    # 3. Pipeline de classificação híbrido: ML (XGBoost) com fallback automático para IA (Groq).
    # Se confiança >= 0.90 → resultado do XGBoost. Se < 0.90 ou falha → resultado do Groq LLM.
    ml_result = predict_triage(patient_input)

    # Formata o triage_result conforme especificação
    triage_result = {
        "assigned_specialty": ml_result.get("assigned_specialty", "CLINICA_GERAL"),
        "urgency_level": ml_result.get("urgency_level", "MEDIA"),
        "confidence_score": ml_result.get("confidence_score", 0.0),
        "processed_by": ml_result.get("processed_by", "ML_XGBOOST"),
        "llm_justification": ml_result.get("llm_justification", None),
        "token_consumption": ml_result.get("token_consumption", 0),
    }

    # 4. Atualiza documento persistido com triage_result
    mongo_db["tickets"].update_one(
        {"_id": insert_result.inserted_id},
        {"$set": {"triage_result": triage_result}},
    )

    # 5. Retorno sanitizado
    return {
        "ticket_id": ticket_id,
        "assigned_specialty": triage_result["assigned_specialty"],
        "urgency_level": triage_result["urgency_level"],
        "status": "WAITING",
        "created_at": ticket_doc["created_at"],
    }


# Constantes de status de tickets
STATUS_WAITING = "WAITING"
STATUS_FINALIZED = "FINALIZED"
OPEN_STATUS = STATUS_WAITING

VALID_SPECIALTIES = {
    "CLINICA_GERAL",
    "CARDIOLOGIA",
    "DERMATOLOGIA",
    "OTORRINOLARINGOLOGIA",
    "PNEUMOLOGIA",
}

SPECIALTY_ALIASES = {
    "clinica geral": "CLINICA_GERAL",
    "clínica geral": "CLINICA_GERAL",
    "clinica_geral": "CLINICA_GERAL",
    "clinica": "CLINICA_GERAL",
    "cardiologia": "CARDIOLOGIA",
    "cardio": "CARDIOLOGIA",
    "dermatologia": "DERMATOLOGIA",
    "dermato": "DERMATOLOGIA",
    "otorrinolaringologia": "OTORRINOLARINGOLOGIA",
    "otorrino": "OTORRINOLARINGOLOGIA",
    "pneumologia": "PNEUMOLOGIA",
    "pneumo": "PNEUMOLOGIA",
}


def _resolve_doctor_profile(
    current_user: dict[str, Any],
    pg_db: Session,
) -> tuple[User, str]:
    """Valida permissões e extrai o perfil do médico e sua especialidade a partir do PostgreSQL.

    Garante que:
    - O token JWT possui claim role='doctor'
    - O email existe no JWT e é normalizado (lowercase)
    - O médico existe no PostgreSQL, está ativo e possui role='doctor'
    - Possui especialidade cadastrada e compatível com o enum clínico (VALID_SPECIALTIES)

    Retorna a tupla (user, assigned_specialty) ou interrompe imediatamente com HTTPException 403.
    """
    jwt_role = current_user.get("role")
    if jwt_role != "doctor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a médicos autorizados.",
        )

    jwt_email = current_user.get("email")
    if not jwt_email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Identificação do médico ausente no token de acesso.",
        )

    email_normalized = str(jwt_email).strip().lower()

    try:
        user = (
            pg_db.query(User)
            .filter(User.email == email_normalized, User.is_active.is_(True))
            .first()
        )
    except Exception as exc:
        logger.error("Erro ao consultar PostgreSQL para obter usuário médico: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao consultar o perfil médico.",
        )

    if not user or user.role != "doctor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a médicos autorizados.",
        )

    if not user.specialization or not user.specialization.strip():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Médico não possui especialidade atribuída no sistema.",
        )

    spec_cleaned = user.specialization.strip().lower()
    assigned_specialty = SPECIALTY_ALIASES.get(spec_cleaned) or user.specialization.strip().upper()

    if assigned_specialty not in VALID_SPECIALTIES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Especialidade médica não cadastrada no catálogo clínico de triagem.",
        )

    return user, assigned_specialty


def _ensure_mongo_index(mongo_db: Database) -> None:
    """Garante a existência do índice composto (triage_result.assigned_specialty, status, created_at)."""
    try:
        mongo_db["tickets"].create_index(
            [
                ("triage_result.assigned_specialty", 1),
                ("status", 1),
                ("created_at", 1),
            ],
            name="idx_triage_queue",
            background=True,
        )
    except Exception as exc:
        logger.warning("Falha não bloqueante ao criar índice no MongoDB: %s", exc)


def get_doctor_triage_queue(
    current_user: dict[str, Any],
    pg_db: Session,
    mongo_db: Database,
    limit: int = 20,
    offset: int = 0,
) -> dict[str, Any]:
    """Retorna os atendimentos abertos da especialidade do médico logado.

    Fluxo em duas etapas sequenciais:
    1. PostgreSQL: Resolve perfil médico e especialidade via _resolve_doctor_profile (403 se inválido).
    2. MongoDB: Utiliza a especialidade para buscar documentos com status='WAITING'.
       Ordena por urgência clínica (EMERGENCIA > ALTA > MEDIA > BAIXA) e data de criação crescente.
       Pagina com limit/offset e projeta estritamente os campos permitidos.
    """
    # ── Etapa 1: Validação do Médico e Especialidade no PostgreSQL ──
    _, assigned_specialty = _resolve_doctor_profile(current_user=current_user, pg_db=pg_db)

    # ── Etapa 2: Consulta à Fila no MongoDB ──
    _ensure_mongo_index(mongo_db)

    pipeline = [
        {
            "$match": {
                "status": OPEN_STATUS,
                "triage_result.assigned_specialty": assigned_specialty,
            }
        },
        {
            "$addFields": {
                "urgency_rank": {
                    "$switch": {
                        "branches": [
                            {"case": {"$eq": ["$triage_result.urgency_level", "EMERGENCIA"]}, "then": 1},
                            {"case": {"$eq": ["$triage_result.urgency_level", "ALTA"]}, "then": 2},
                            {"case": {"$eq": ["$triage_result.urgency_level", "MEDIA"]}, "then": 3},
                            {"case": {"$eq": ["$triage_result.urgency_level", "BAIXA"]}, "then": 4},
                        ],
                        "default": 5,
                    }
                }
            }
        },
        {"$sort": {"urgency_rank": 1, "created_at": 1}},
        {
            "$facet": {
                "items": [
                    {"$skip": int(offset)},
                    {"$limit": int(limit)},
                    {
                        "$project": {
                            "_id": 0,
                            "ticket_id": {"$toString": "$_id"},
                            "assigned_specialty": "$triage_result.assigned_specialty",
                            "urgency_level": "$triage_result.urgency_level",
                            "status": "$status",
                            "created_at": "$created_at",
                            "patient_input": {
                                "perceived_severity": "$patient_input.perceived_severity",
                                "symptom_duration_hours": "$patient_input.symptom_duration_hours",
                                "primary_symptoms": "$patient_input.primary_symptoms",
                                "description": "$patient_input.description",
                            },
                        }
                    },
                ],
                "total": [{"$count": "count"}],
            }
        },
    ]

    try:
        agg_result = list(mongo_db["tickets"].aggregate(pipeline))
    except Exception as exc:
        logger.error("Erro ao consultar fila de tickets no MongoDB: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao consultar a fila de atendimentos.",
        )

    items: list[dict[str, Any]] = []
    total = 0

    if agg_result:
        facet_data = agg_result[0]
        total_list = facet_data.get("total", [])
        total = total_list[0]["count"] if total_list else 0
        items = facet_data.get("items", [])

    return {
        "items": items,
        "total": total,
    }


def finish_doctor_triage_ticket(
    ticket_id: str,
    current_user: dict[str, Any],
    pg_db: Session,
    mongo_db: Database,
) -> dict[str, Any]:
    """Finaliza um atendimento aberto da especialidade do médico de forma atômica.

    Fluxo:
    1. Valida ticket_id como ObjectId válido (404 genérico se inválido).
    2. PostgreSQL: Valida médico logado e obtém a especialidade via _resolve_doctor_profile.
    3. MongoDB: Atualização atômica combinando _id, status='WAITING' e assigned_specialty.
       Se nenhum documento casar, retorna 404 genérico (evita enumeração).
    4. Atualiza exclusivamente: status='FINALIZED', finalized_at e finalized_by.
    5. Retorna sanitizado { ticket_id, status }.
    """
    try:
        obj_id = ObjectId(ticket_id)
    except (InvalidId, TypeError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Atendimento não encontrado ou indisponível.",
        )

    # 1. Resolve médico e especialidade autorizada no PostgreSQL
    doctor_user, assigned_specialty = _resolve_doctor_profile(current_user=current_user, pg_db=pg_db)

    # 2. Atualização atômica no MongoDB
    filter_query = {
        "_id": obj_id,
        "status": OPEN_STATUS,
        "triage_result.assigned_specialty": assigned_specialty,
    }

    update_query = {
        "$set": {
            "status": STATUS_FINALIZED,
            "finalized_at": datetime.now(UTC),
            "finalized_by": str(doctor_user.id),
        }
    }

    try:
        result = mongo_db["tickets"].update_one(filter_query, update_query)
    except Exception as exc:
        logger.error("Erro ao finalizar ticket no MongoDB: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao finalizar o atendimento.",
        )

    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Atendimento não encontrado ou indisponível.",
        )

    return {
        "ticket_id": ticket_id,
        "status": STATUS_FINALIZED,
    }


