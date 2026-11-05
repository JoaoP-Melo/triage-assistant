from datetime import UTC, datetime
from unittest.mock import MagicMock
import uuid

from bson import ObjectId
from fastapi import HTTPException
from fastapi.testclient import TestClient
import pytest

from app.auth.models import User
from app.core.database import get_db, get_mongo_db
from app.core.security import get_current_user
from app.main import app
from app.triage.service import finish_doctor_triage_ticket


class FakeMongoCollection:
    def __init__(self):
        self.docs = {}

    def insert_one(self, doc):
        doc_id = doc.get("_id") or ObjectId()
        doc["_id"] = doc_id
        self.docs[str(doc_id)] = doc.copy()
        result = MagicMock()
        result.inserted_id = doc_id
        return result

    def update_one(self, filter_query, update_query):
        target_id = str(filter_query.get("_id"))
        doc = self.docs.get(target_id)
        result = MagicMock()
        if not doc:
            result.matched_count = 0
            result.modified_count = 0
            return result

        # Check status and specialty filter
        if "status" in filter_query and doc.get("status") != filter_query["status"]:
            result.matched_count = 0
            result.modified_count = 0
            return result

        spec_filter = filter_query.get("triage_result.assigned_specialty")
        if (
            spec_filter
            and doc.get("triage_result", {}).get("assigned_specialty") != spec_filter
        ):
            result.matched_count = 0
            result.modified_count = 0
            return result

        if "$set" in update_query:
            doc.update(update_query["$set"])
            result.matched_count = 1
            result.modified_count = 1
            return result

        result.matched_count = 1
        result.modified_count = 0
        return result

    def find_one(self, filter_query):
        target_id = str(filter_query.get("_id"))
        return self.docs.get(target_id)


class FakeMongoDB:
    def __init__(self):
        self.collection = FakeMongoCollection()

    def __getitem__(self, item):
        if item == "tickets":
            return self.collection
        return MagicMock()


@pytest.fixture
def fake_mongo():
    return FakeMongoDB()


@pytest.fixture
def doctor_a():
    doc_id = uuid.uuid4()
    user = User(
        id=doc_id,
        full_name="Dra. Alice Silva",
        email="alice@hospital.com",
        role="doctor",
        specialization="CARDIOLOGIA",
        is_active=True,
    )
    return user


@pytest.fixture
def doctor_b():
    doc_id = uuid.uuid4()
    user = User(
        id=doc_id,
        full_name="Dr. Bruno Castro",
        email="bruno@hospital.com",
        role="doctor",
        specialization="CARDIOLOGIA",
        is_active=True,
    )
    return user


@pytest.fixture
def fake_pg_session(doctor_a, doctor_b):
    session = MagicMock()

    def fake_query(model):
        query_mock = MagicMock()
        if model == User:

            def fake_filter(*args, **kwargs):
                filter_mock = MagicMock()

                # filter by email
                def fake_first():
                    # check called args if needed
                    str_args = str(args)
                    if "alice" in str_args:
                        return doctor_a
                    if "bruno" in str_args:
                        return doctor_b
                    return doctor_a

                filter_mock.first = fake_first
                return filter_mock

            query_mock.filter = fake_filter
        return query_mock

    session.query = fake_query
    return session


def test_doctor_a_finalizes_ticket_audited(fake_mongo, doctor_a, fake_pg_session):
    ticket_id = ObjectId()
    fake_mongo.collection.docs[str(ticket_id)] = {
        "_id": ticket_id,
        "status": "WAITING",
        "triage_result": {"assigned_specialty": "CARDIOLOGIA", "urgency_level": "ALTA"},
        "created_at": datetime.now(UTC),
    }

    current_user_a = {
        "user_id": str(doctor_a.id),
        "email": doctor_a.email,
        "role": "doctor",
    }

    result = finish_doctor_triage_ticket(
        ticket_id=str(ticket_id),
        current_user=current_user_a,
        pg_db=fake_pg_session,
        mongo_db=fake_mongo,
    )

    assert result["ticket_id"] == str(ticket_id)
    assert result["status"] == "FINALIZED"
    assert result["finalized_by_name"] == doctor_a.full_name
    assert isinstance(result["finalized_at"], datetime)

    # Verifica gravação no documento MongoDB
    saved = fake_mongo.collection.docs[str(ticket_id)]
    assert saved["status"] == "FINALIZED"
    assert saved["finalized_by"] == str(doctor_a.id)
    assert saved["finalized_by_name"] == doctor_a.full_name
    assert saved["finalized_at"] == result["finalized_at"]


def test_cannot_refinish_ticket_and_audit_not_overwritten(
    fake_mongo, doctor_a, doctor_b, fake_pg_session
):
    ticket_id = ObjectId()
    initial_time = datetime(2026, 11, 1, 10, 0, tzinfo=UTC)
    fake_mongo.collection.docs[str(ticket_id)] = {
        "_id": ticket_id,
        "status": "FINALIZED",
        "triage_result": {"assigned_specialty": "CARDIOLOGIA", "urgency_level": "ALTA"},
        "finalized_by": str(doctor_a.id),
        "finalized_by_name": doctor_a.full_name,
        "finalized_at": initial_time,
    }

    current_user_b = {
        "user_id": str(doctor_b.id),
        "email": doctor_b.email,
        "role": "doctor",
    }

    # Tentar finalizar novamente com Médico B deve lançar 404
    with pytest.raises(HTTPException) as exc_info:
        finish_doctor_triage_ticket(
            ticket_id=str(ticket_id),
            current_user=current_user_b,
            pg_db=fake_pg_session,
            mongo_db=fake_mongo,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Atendimento não encontrado ou indisponível."

    # Dados de auditoria continuam intactos (pertencentes ao Médico A)
    doc = fake_mongo.collection.docs[str(ticket_id)]
    assert doc["finalized_by"] == str(doctor_a.id)
    assert doc["finalized_by_name"] == doctor_a.full_name
    assert doc["finalized_at"] == initial_time


def test_finish_endpoint_requires_doctor_role_and_token(fake_mongo, fake_pg_session):
    client = TestClient(app)
    ticket_id = str(ObjectId())

    # 1. Sem token -> 401
    resp_no_token = client.patch(f"/triage/{ticket_id}/finish")
    assert resp_no_token.status_code == 401

    # 2. Usuário com role patient -> 403
    app.dependency_overrides[get_current_user] = lambda: {
        "user_id": "patient-1",
        "email": "paciente@hospital.com",
        "role": "patient",
    }
    app.dependency_overrides[get_db] = lambda: fake_pg_session
    app.dependency_overrides[get_mongo_db] = lambda: fake_mongo

    try:
        resp_patient = client.patch(f"/triage/{ticket_id}/finish")
        assert resp_patient.status_code == 403
        assert resp_patient.json()["detail"] == "Acesso restrito a médicos autorizados."
    finally:
        app.dependency_overrides.clear()
