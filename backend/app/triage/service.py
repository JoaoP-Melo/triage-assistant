from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status
from pymongo.database import Database

from app.triage.schemas import TriageSubmitRequest
from app.classification.service import predict_triage


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
