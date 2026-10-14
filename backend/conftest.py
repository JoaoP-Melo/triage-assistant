import os
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from typing import Any, Generator
from unittest.mock import MagicMock, patch

from dotenv import load_dotenv
from fastapi import HTTPException
from fastapi.testclient import TestClient
import jwt
from pymongo import MongoClient
from pymongo.database import Database
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

load_dotenv()

# PostgreSQL para testes
TEST_DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# MongoDB para testes
MONGODB_URL = os.getenv("MONGODB_URL")

from app.auth.models import User
from app.core.database import Base, get_db, get_mongo_db
from app.core.security import ALGORITHM, SECRET_KEY, get_current_user, hash_password
from app.main import app


# ─────────────────────────────────────────────────────────────────────────────
# 1. Fixtures de Bancos de Dados (PostgreSQL e MongoDB do Docker Compose)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def mongodb_session() -> Generator[Database, None, None]:
    """Conecta à instância real do MongoDB de testes do Docker Compose,
    garantindo limpeza e isolamento das coleções antes e após cada teste.
    """
    try:
        client = MongoClient(MONGODB_URL, serverSelectionTimeoutMS=2000)
        client.admin.command("ping")
    except Exception as exc:
        pytest.fail(
            f"Não foi possível conectar ao MongoDB de testes do Docker Compose em '{MONGODB_URL}'. "
            f"Certifique-se de que o container do docker compose está ativo ('docker compose up -d mongodb'). "
            f"Erro: {exc}"
        )

    db = client.get_default_database(default="test_triage")

    # Limpa coleções de teste antes da execução
    for col in db.list_collection_names():
        if not col.startswith("system."):
            db[col].delete_many({})

    yield db

    # Limpa coleções de teste após a execução para não deixar sujeira
    for col in db.list_collection_names():
        if not col.startswith("system."):
            db[col].delete_many({})
    client.close()


@pytest.fixture(scope="session")
def setup_db() -> Generator[None, None, None]:
    """Cria as tabelas no banco de dados de teste PostgreSQL e remove ao final da sessão."""
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as exc:
        pytest.fail(
            f"Não foi possível conectar ao PostgreSQL de testes em '{TEST_DATABASE_URL}'. "
            f"Certifique-se de que o container do docker compose está ativo ('docker compose up -d db'). "
            f"Erro: {exc}"
        )
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(setup_db) -> Generator[Session, None, None]:
    """Fornece uma sessão isolada de banco de dados PostgreSQL por teste com rollback."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    # Injeta a sessão de teste no override do get_db
    overrides_backup = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = lambda: session

    yield session

    session.close()
    transaction.rollback()
    connection.close()

    if overrides_backup is not None:
        app.dependency_overrides[get_db] = overrides_backup
    else:
        app.dependency_overrides.pop(get_db, None)


# ─────────────────────────────────────────────────────────────────────────────
# 2. Fixtures de Payload e Tokens JWT
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def valid_payload() -> dict[str, Any]:
    """Payload padrão válido para submissão de triagem de sintomas."""
    return {
        "perceived_severity": 5,
        "symptom_duration_hours": 24.0,
        "primary_symptoms": ["FEBRE", "DOR_DE_CABECA", "TOSSE"],
        "description": "Paciente relata febre e dor de cabeça há 24 horas.",
    }


@pytest.fixture
def make_token():
    """Factory fixture para gerar tokens JWT em diversos estados (válido, expirado, inválido, roles distintas)."""
    def _maker(
        role: str = "patient",
        user_id: str = "test-patient-uuid",
        kind: str | None = None,
        **extra_claims,
    ) -> str:
        now = datetime.now(UTC)
        payload = {
            "sub": user_id,
            "user_id": user_id,
            "role": role,
            "iat": now,
            "exp": now + timedelta(minutes=15),
            **extra_claims,
        }

        key = SECRET_KEY or "test-secret-key-change-in-production"
        alg = ALGORITHM or "HS256"

        if kind == "expired":
            payload["exp"] = now - timedelta(minutes=10)
            payload["iat"] = now - timedelta(minutes=20)
        elif kind == "invalid_signature":
            key = "different-secret-key-invalid-signature"
        elif kind == "no_role":
            payload.pop("role", None)
        elif kind == "no_user_id":
            payload.pop("sub", None)
            payload.pop("user_id", None)

        return jwt.encode(payload, key, algorithm=alg)

    return _maker


@pytest.fixture
def patient_token(make_token) -> str:
    """Token JWT válido de paciente."""
    return make_token(role="patient")


@pytest.fixture
def auth_headers(patient_token: str) -> dict[str, str]:
    """Header Authorization Bearer com token de paciente."""
    return {"Authorization": f"Bearer {patient_token}"}


# ─────────────────────────────────────────────────────────────────────────────
# 3. Fixtures de Mock para Machine Learning e Agente de IA
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_ml():
    """Factory fixture para simular respostas do pipeline de ML e IA (Groq)."""
    def _factory(
        confidence: float = 0.95,
        processed_by: str | None = None,
        assigned_specialty: str = "CLINICA_GERAL",
        urgency_level: str = "MEDIA",
        raise_exc: Exception | None = None,
    ) -> dict[str, Any]:
        if processed_by is None:
            processed_by = "ML_XGBOOST" if confidence >= 0.90 else "AGENT_LLM"
        return {
            "result": {
                "assigned_specialty": assigned_specialty,
                "urgency_level": urgency_level,
                "confidence_score": confidence,
                "processed_by": processed_by,
                "llm_justification": (
                    "Justificativa médica gerada pelo agente de IA."
                    if processed_by == "AGENT_LLM"
                    else None
                ),
                "token_consumption": 120 if processed_by == "AGENT_LLM" else 0,
            },
            "raise_exc": raise_exc,
        }
    return _factory


@pytest.fixture
def mock_ml_service():
    """Mock isolado do modelo XGBoost (predict_triage_ml)."""
    with patch("app.classification.service.predict_triage_ml") as mocked_svc:
        mocked_svc.return_value = {
            "assigned_specialty": "CLINICA_GERAL",
            "urgency_level": "MEDIA",
            "confidence_score": 0.95,
            "processed_by": "ML_XGBOOST",
            "llm_justification": None,
            "token_consumption": 0,
        }
        yield mocked_svc


@pytest.fixture
def mock_ia_service():
    """Mock isolado do agente de IA Groq LLM (classify_with_llm)."""
    with patch("app.classification.service.classify_with_llm") as mocked_svc:
        mocked_svc.return_value = {
            "assigned_specialty": "CLINICA_GERAL",
            "urgency_level": "MEDIA",
            "confidence_score": 0.85,
            "processed_by": "AGENT_LLM",
            "llm_justification": "Classificação clínica assistida por IA (Groq).",
            "token_consumption": 150,
        }
        yield mocked_svc


# ─────────────────────────────────────────────────────────────────────────────
# 4. Clients de Teste (TestClient e client_factory)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def client_factory(mongodb_session: Database, make_token):
    """ContextManager factory para instanciar TestClient configurado sob demanda."""
    @contextmanager
    def _create_client(
        role: str = "patient",
        user_id: str = "test-patient-uuid",
        force_429: bool = False,
        ml_cfg: dict[str, Any] | None = None,
        mongo_fail_write: bool = False,
    ):
        token = make_token(role=role, user_id=user_id)
        headers = {"Authorization": f"Bearer {token}"}

        if mongo_fail_write:
            mock_collection = MagicMock()
            mock_collection.insert_one.side_effect = Exception("Falha de escrita simulada no MongoDB")
            fake_db = MagicMock()
            fake_db.__getitem__.return_value = mock_collection
            current_mongo = fake_db
        else:
            current_mongo = mongodb_session

        overrides_backup = dict(app.dependency_overrides)
        app.dependency_overrides[get_mongo_db] = lambda: current_mongo

        if force_429:
            def _raise_429():
                raise HTTPException(status_code=429, detail="Too Many Requests")
            app.dependency_overrides[get_current_user] = _raise_429

        mock_predict = MagicMock()
        if ml_cfg:
            if ml_cfg.get("raise_exc"):
                mock_predict.side_effect = ml_cfg["raise_exc"]
            else:
                mock_predict.return_value = ml_cfg.get("result", {})
        else:
            mock_predict.return_value = {
                "assigned_specialty": "CLINICA_GERAL",
                "urgency_level": "MEDIA",
                "confidence_score": 0.95,
                "processed_by": "ML_XGBOOST",
                "llm_justification": None,
                "token_consumption": 0,
            }

        with patch("app.triage.service.predict_triage", mock_predict):
            with TestClient(app, raise_server_exceptions=False) as tc:
                tc.headers.update(headers)
                tc._mongo_db = current_mongo
                tc._predict_triage_mock = mock_predict
                yield tc

        app.dependency_overrides.clear()
        app.dependency_overrides.update(overrides_backup)

    return _create_client


@pytest.fixture
def client(mongodb_session: Database, make_token) -> Generator[TestClient, None, None]:
    """TestClient FastAPI pré-configurado com MongoDB real do Docker Compose e mocks para ML/IA."""
    token = make_token(role="patient", user_id="test-patient-uuid")
    mock_predict = MagicMock(return_value={
        "assigned_specialty": "CLINICA_GERAL",
        "urgency_level": "MEDIA",
        "confidence_score": 0.95,
        "processed_by": "ML_XGBOOST",
        "llm_justification": None,
        "token_consumption": 0,
    })

    app.dependency_overrides[get_mongo_db] = lambda: mongodb_session

    with patch("app.triage.service.predict_triage", mock_predict):
        with TestClient(app, raise_server_exceptions=False) as test_client:
            test_client.headers["Authorization"] = f"Bearer {token}"
            test_client._mongo_db = mongodb_session
            test_client._predict_triage_mock = mock_predict
            yield test_client

    app.dependency_overrides.clear()


# ─────────────────────────────────────────────────────────────────────────────
# 5. Fixtures de Usuários para Testes de Autenticação
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def patient_user(db_session: Session) -> User:
    """Cria um usuário paciente no banco de dados de teste."""
    user = User(
        full_name="Paciente Teste",
        email="patient@example.com",
        hashed_password=hash_password("Senha123!"),
        role="patient",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def doctor_user(db_session: Session) -> User:
    """Cria um usuário médico no banco de dados de teste."""
    user = User(
        full_name="Doutor Teste",
        email="doctor@example.com",
        hashed_password=hash_password("Senha123!"),
        role="doctor",
        specialization="Cardiologia",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user
