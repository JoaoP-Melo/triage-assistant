"""Testes de integração para POST /triage/submit.

Valida regras de negócio de triagem de sintomas de pacientes:
- Validação estrita de schemas e allowlist de sintomas (422)
- Autenticação e RBAC (401 para sem token/inválido, 403 para não-pacientes)
- Persistência no MongoDB real de testes (Docker Compose) com status WAITING
- Roteamento híbrido (ML XGBoost vs Fallback IA Groq via mocks)
- Contrato da API e proteção contra vazamento de campos internos
"""

from __future__ import annotations

import uuid
import pytest
from app.classification.service import predict_triage


# ─────────────────────────────────────────────────────────────────────────────
# 1. Entrada inválida → 422
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "override,desc",
    [
        # severidade fora de 1-10
        ({"perceived_severity": 0}, "severidade=0"),
        ({"perceived_severity": 11}, "severidade=11"),
        # duração ≤ 0
        ({"symptom_duration_hours": 0}, "duração=0"),
        ({"symptom_duration_hours": -1}, "duração=-1"),
        # menos de 3 sintomas
        ({"primary_symptoms": ["FEBRE", "NAUSEA"]}, "2 sintomas"),
        # mais de 3 sintomas
        ({"primary_symptoms": ["FEBRE", "NAUSEA", "TOSSE", "COCEIRA"]}, "4 sintomas"),
        # sintomas duplicados
        ({"primary_symptoms": ["FEBRE", "FEBRE", "NAUSEA"]}, "sintomas duplicados"),
        # sintoma fora da allowlist
        ({"primary_symptoms": ["FEBRE", "NAUSEA", "GRIPE"]}, "sintoma inválido"),
        # descrição vazia
        ({"description": ""}, "descrição vazia"),
        # descrição acima do limite (2001 chars)
        ({"description": "x" * 2001}, "descrição acima do limite"),
    ],
)
def test_invalid_input_422(client, valid_payload, override, desc):
    """Garante que entradas fora da especificação clínica são rejeitadas com 422."""
    payload = {**valid_payload, **override}
    resp = client.post("/triage/submit", json=payload)
    assert resp.status_code == 422, f"Esperado 422 para: {desc}"


# ─────────────────────────────────────────────────────────────────────────────
# 2. Autenticação e RBAC
# ─────────────────────────────────────────────────────────────────────────────

def test_no_token_returns_401(client, valid_payload):
    """Requisição sem cabeçalho Authorization deve retornar 401."""
    client.headers.pop("Authorization", None)
    response = client.post("/triage/submit", json=valid_payload)
    assert response.status_code == 401


@pytest.mark.parametrize(
    "kind,expected_status",
    [
        ("expired", 401),
        ("invalid_signature", 401),
        ("no_role", 401),
        ("no_user_id", 401),
    ],
)
def test_invalid_tokens(client, valid_payload, make_token, kind, expected_status):
    """Tokens expirados, assinatura inválida ou sem role/user_id → 401."""
    token = make_token(kind=kind)
    resp = client.post(
        "/triage/submit",
        json=valid_payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == expected_status


def test_doctor_role_returns_403(valid_payload, client_factory):
    """Apenas usuários com role 'patient' podem submeter triagens; médicos recebem 403."""
    with client_factory(role="doctor") as c:
        resp = c.post("/triage/submit", json=valid_payload)
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Apenas pacientes podem submeter triagens."


def test_user_id_from_jwt_not_body(valid_payload, client_factory):
    """user_id enviado no corpo é ignorado; documento usa estritamente o user_id do JWT."""
    jwt_uid = str(uuid.uuid4())
    body_uid = str(uuid.uuid4())
    payload = {**valid_payload, "user_id": body_uid}

    with client_factory(user_id=jwt_uid) as c:
        resp = c.post("/triage/submit", json=payload)
        db = c._mongo_db

    assert resp.status_code == 201
    tickets = list(db["tickets"].find())
    assert len(tickets) == 1
    assert tickets[0]["user_id"] == jwt_uid
    assert tickets[0]["user_id"] != body_uid


# ─────────────────────────────────────────────────────────────────────────────
# 3. Rate limit → 429
# ─────────────────────────────────────────────────────────────────────────────

def test_rate_limit_returns_429(valid_payload, client_factory):
    """Quando rate limit for atingido via middleware/dependência de segurança → 429."""
    with client_factory(force_429=True) as c:
        resp = c.post("/triage/submit", json=valid_payload)
    assert resp.status_code == 429


# ─────────────────────────────────────────────────────────────────────────────
# 4. Roteamento híbrido (ML XGBoost vs Fallback IA Groq via mocks)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "confidence,expected_processed_by",
    [
        (0.90, "ML_XGBOOST"),   # exatamente no corte de 90% → ML
        (0.9999, "ML_XGBOOST"), # alta confiança → ML
        (0.8999, "AGENT_LLM"),  # abaixo de 90% → fallback IA
        (0.50, "AGENT_LLM"),    # baixa confiança → fallback IA
    ],
)
def test_hybrid_routing(valid_payload, mock_ml, client_factory, confidence, expected_processed_by):
    """Verifica o roteamento híbrido com base no score de confiança do modelo."""
    ml_cfg = mock_ml(
        confidence=confidence,
        processed_by=expected_processed_by,
    )
    with client_factory(ml_cfg=ml_cfg) as c:
        resp = c.post("/triage/submit", json=valid_payload)
        mock = c._predict_triage_mock

    assert resp.status_code == 201
    mock.assert_called_once()


def test_high_confidence_predict_triage_called_once(valid_payload, mock_ml, client_factory):
    """Confidence ≥ 0.90: predict_triage chamado uma vez com payload íntegro."""
    ml_cfg = mock_ml(confidence=0.95)
    with client_factory(ml_cfg=ml_cfg) as c:
        resp = c.post("/triage/submit", json=valid_payload)
        mock = c._predict_triage_mock

    assert resp.status_code == 201
    mock.assert_called_once()
    called_input = mock.call_args[0][0]
    assert called_input["perceived_severity"] == valid_payload["perceived_severity"]
    assert called_input["symptom_duration_hours"] == valid_payload["symptom_duration_hours"]
    assert called_input["primary_symptoms"] == valid_payload["primary_symptoms"]
    assert called_input["description"] == valid_payload["description"]


def test_boundary_0_90_uses_ml(valid_payload, mock_ml, client_factory):
    """Exatamente 0.90 → ML_XGBOOST (limite inclusivo de corte)."""
    ml_cfg = mock_ml(confidence=0.90, processed_by="ML_XGBOOST")
    with client_factory(ml_cfg=ml_cfg) as c:
        resp = c.post("/triage/submit", json=valid_payload)
    assert resp.status_code == 201


def test_boundary_0_8999_uses_llm(valid_payload, mock_ml, client_factory):
    """0.8999 < 0.90 → aciona fallback AGENT_LLM."""
    ml_cfg = mock_ml(confidence=0.8999, processed_by="AGENT_LLM")
    with client_factory(ml_cfg=ml_cfg) as c:
        resp = c.post("/triage/submit", json=valid_payload)
    assert resp.status_code == 201


def test_classification_service_hybrid_pipeline(valid_payload, mock_ml_service, mock_ia_service):
    """Valida a lógica interna do classification/service.py usando mocks isolados de ML e IA:
    - Se ML tiver confiança >= 0.90, não aciona a IA.
    - Se ML tiver confiança < 0.90, aciona a IA.
    """
    # 1. Caso Alta Confiança no ML (>= 0.90)
    mock_ml_service.return_value = {
        "assigned_specialty": "CARDIOLOGIA",
        "urgency_level": "ALTA",
        "confidence_score": 0.95,
        "processed_by": "ML_XGBOOST",
        "llm_justification": None,
        "token_consumption": 0,
    }
    result_high = predict_triage(valid_payload)
    assert result_high["processed_by"] == "ML_XGBOOST"
    assert result_high["assigned_specialty"] == "CARDIOLOGIA"
    mock_ia_service.assert_not_called()

    # 2. Caso Baixa Confiança no ML (< 0.90) → aciona IA Groq
    mock_ml_service.return_value = {
        "assigned_specialty": "CLINICA_GERAL",
        "urgency_level": "MEDIA",
        "confidence_score": 0.72,
        "processed_by": "ML_XGBOOST",
        "llm_justification": None,
        "token_consumption": 0,
    }
    result_low = predict_triage(valid_payload)
    assert result_low["processed_by"] == "AGENT_LLM"
    mock_ia_service.assert_called_once()


# ─────────────────────────────────────────────────────────────────────────────
# 5. Tratamento de Exceções a Jusante
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "exc,desc",
    [
        (RuntimeError("ML falhou criticamente"), "exceção ML"),
        (TimeoutError("ML timeout"), "timeout ML"),
    ],
)
def test_ml_failure_propagates_500(valid_payload, mock_ml, client_factory, exc, desc):
    """Falha não tratada em predict_triage propaga status 500 para a rota."""
    ml_cfg = mock_ml(raise_exc=exc)
    with client_factory(ml_cfg=ml_cfg) as c:
        resp = c.post("/triage/submit", json=valid_payload)
    assert resp.status_code == 500, f"Esperado 500 para: {desc}"


@pytest.mark.parametrize(
    "exc,desc",
    [
        (RuntimeError("IA falhou no provedor"), "exceção IA no fallback"),
        (TimeoutError("IA timeout no provedor"), "timeout IA no fallback"),
    ],
)
def test_ia_failure_propagates_500(valid_payload, mock_ml, client_factory, exc, desc):
    """Exceção durante execução de IA propaga 500 caso o serviço falhe sem fallback."""
    ml_cfg = mock_ml(raise_exc=exc)
    with client_factory(ml_cfg=ml_cfg) as c:
        resp = c.post("/triage/submit", json=valid_payload)
    assert resp.status_code == 500, f"Esperado 500 para: {desc}"


def test_malformed_ia_output_uses_defaults(valid_payload, client_factory):
    """Quando o retorno de classificação for malformado, o service aplica defaults seguros."""
    malformed_cfg = {
        "result": {"broken": True},
        "raise_exc": None,
    }
    with client_factory(ml_cfg=malformed_cfg) as c:
        resp = c.post("/triage/submit", json=valid_payload)

    assert resp.status_code == 201
    data = resp.json()
    assert data["assigned_specialty"] == "CLINICA_GERAL"
    assert data["urgency_level"] == "MEDIA"


# ─────────────────────────────────────────────────────────────────────────────
# 6. Persistência no MongoDB do Docker Compose
# ─────────────────────────────────────────────────────────────────────────────

def test_ticket_persisted_with_waiting_status(valid_payload, client_factory):
    """Ticket é persistido no MongoDB real com status='WAITING' e timestamp created_at."""
    with client_factory() as c:
        resp = c.post("/triage/submit", json=valid_payload)
        db = c._mongo_db

    assert resp.status_code == 201
    tickets = list(db["tickets"].find())
    assert len(tickets) >= 1
    ticket = tickets[0]
    assert ticket["status"] == "WAITING"
    assert ticket["created_at"] is not None
    assert ticket["triage_result"] is not None


def test_mongo_write_failure_returns_500_without_internal_details(valid_payload, client_factory):
    """Falha de escrita no MongoDB deve responder 500 sem expor mensagens internas da infraestrutura."""
    with client_factory(mongo_fail_write=True) as c:
        resp = c.post("/triage/submit", json=valid_payload)

    assert resp.status_code >= 500
    assert "Falha de escrita simulada no MongoDB" not in resp.text


# ─────────────────────────────────────────────────────────────────────────────
# 7. Contrato de Resposta (TriageSubmitResponse)
# ─────────────────────────────────────────────────────────────────────────────

ALLOWED_RESPONSE_KEYS = {"ticket_id", "assigned_specialty", "urgency_level", "status", "created_at"}
FORBIDDEN_KEYS = {"llm_justification", "token_consumption", "confidence_score"}


def test_response_contract_allowed_keys_only(valid_payload, client):
    """Resposta contém rigorosamente os campos permitidos pelo schema TriageSubmitResponse."""
    resp = client.post("/triage/submit", json=valid_payload)
    assert resp.status_code == 201
    data = resp.json()
    assert set(data.keys()) == ALLOWED_RESPONSE_KEYS


@pytest.mark.parametrize("forbidden_key", list(FORBIDDEN_KEYS))
def test_response_does_not_leak_internal_fields(valid_payload, client, forbidden_key):
    """Campos de consumo de IA, confiança e justificativa médica interna não vazam na resposta."""
    resp = client.post("/triage/submit", json=valid_payload)
    assert resp.status_code == 201
    data = resp.json()
    assert forbidden_key not in data, f"Campo proibido '{forbidden_key}' encontrado na resposta"


def test_response_status_is_waiting(valid_payload, client):
    """Status inicial do ticket deve ser estritamente 'WAITING'."""
    resp = client.post("/triage/submit", json=valid_payload)
    assert resp.status_code == 201
    assert resp.json()["status"] == "WAITING"


def test_response_created_at_is_present(valid_payload, client):
    """Campo created_at está presente na resposta."""
    resp = client.post("/triage/submit", json=valid_payload)
    assert resp.status_code == 201
    assert resp.json().get("created_at") is not None


def test_response_ticket_id_is_string(valid_payload, client):
    """ticket_id retornado é uma string válida (ObjectId do MongoDB serializado)."""
    resp = client.post("/triage/submit", json=valid_payload)
    assert resp.status_code == 201
    ticket_id = resp.json().get("ticket_id")
    assert isinstance(ticket_id, str) and len(ticket_id) > 0


# ─────────────────────────────────────────────────────────────────────────────
# 8. Repasse íntegro dos dados do paciente ao classificador
# ─────────────────────────────────────────────────────────────────────────────

def test_ml_receives_payload_unchanged(valid_payload, client):
    """predict_triage recebe exatamente os mesmos dados enviados pelo paciente."""
    resp = client.post("/triage/submit", json=valid_payload)
    assert resp.status_code == 201

    mock = client._predict_triage_mock
    mock.assert_called_once()
    received = mock.call_args[0][0]

    assert received["perceived_severity"] == valid_payload["perceived_severity"]
    assert received["symptom_duration_hours"] == valid_payload["symptom_duration_hours"]
    assert received["primary_symptoms"] == valid_payload["primary_symptoms"]
    assert received["description"] == valid_payload["description"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("perceived_severity", 3),
        ("symptom_duration_hours", 48.5),
        ("description", "Dor leve persistente sem febre."),
    ],
)
def test_ml_receives_each_field_correctly(valid_payload, mock_ml, client_factory, field, value):
    """Cada campo individual modificado é repassado ao classificador com integridade."""
    payload = {**valid_payload, field: value}
    with client_factory() as c:
        resp = c.post("/triage/submit", json=payload)
        mock = c._predict_triage_mock

    assert resp.status_code == 201
    received = mock.call_args[0][0]
    assert received[field] == value