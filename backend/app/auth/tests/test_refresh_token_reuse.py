from datetime import UTC, datetime, timedelta
import uuid

from fastapi import HTTPException
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.auth.models import AuthSession, User
from app.auth.service import refresh_session
from app.core.database import Base
from app.core.security import hash_password, hash_token


@pytest.fixture
def sqlite_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = testing_session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def user_1(sqlite_db):
    user = User(
        id=uuid.uuid4(),
        full_name="João Silva",
        email="joao@teste.com",
        hashed_password=hash_password("Senha123!"),
        role="patient",
        is_active=True,
    )
    sqlite_db.add(user)
    sqlite_db.commit()
    sqlite_db.refresh(user)
    return user


@pytest.fixture
def user_2(sqlite_db):
    user = User(
        id=uuid.uuid4(),
        full_name="Maria Souza",
        email="maria@teste.com",
        hashed_password=hash_password("Senha123!"),
        role="patient",
        is_active=True,
    )
    sqlite_db.add(user)
    sqlite_db.commit()
    sqlite_db.refresh(user)
    return user


def test_refresh_token_reuse_revokes_all_user_sessions(sqlite_db, user_1):
    # 1. Sessão inicial do usuário (Token A)
    raw_token_a = "token-a-original"
    hash_a = hash_token(raw_token_a)
    session_a = AuthSession(
        id=uuid.uuid4(),
        user_id=user_1.id,
        refresh_token_hash=hash_a,
        is_revoked=False,
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    sqlite_db.add(session_a)
    sqlite_db.commit()

    # 2. Faz refresh legítimo com Token A -> gera Token B
    data, raw_token_b = refresh_session(
        db=sqlite_db, refresh_token=raw_token_a, client_ip="192.168.1.10"
    )
    assert "access_token" in data

    # Sessão A agora está revogada e Sessão B está ativa
    sqlite_db.refresh(session_a)
    assert session_a.is_revoked is True

    # 3. Cria uma sessão C para o mesmo usuário (ex: login em outro dispositivo)
    raw_token_c = "token-c-outro-dispositivo"
    session_c = AuthSession(
        id=uuid.uuid4(),
        user_id=user_1.id,
        refresh_token_hash=hash_token(raw_token_c),
        is_revoked=False,
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    sqlite_db.add(session_c)
    sqlite_db.commit()

    # 4. ATAQUE / REUSO: Reapresenta o Token A já revogado
    with pytest.raises(HTTPException) as exc_info:
        refresh_session(
            db=sqlite_db, refresh_token=raw_token_a, client_ip="203.0.113.195"
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Refresh token inválido"
    assert "Set-Cookie" in exc_info.value.headers
    assert "Max-Age=0" in exc_info.value.headers["Set-Cookie"]

    # 5. Verifica que TODAS as sessões do User 1 foram revogadas
    user_sessions = (
        sqlite_db.query(AuthSession).filter(AuthSession.user_id == user_1.id).all()
    )
    assert len(user_sessions) == 3
    for s in user_sessions:
        assert s.is_revoked is True, f"Sessão {s.id} deveria estar revogada!"

    # 6. Tentar usar o Token B legítimo agora também deve falhar (pois foi revogado em cascata)
    with pytest.raises(HTTPException) as exc_b:
        refresh_session(
            db=sqlite_db, refresh_token=raw_token_b, client_ip="192.168.1.10"
        )
    assert exc_b.value.status_code == 401


def test_other_user_sessions_not_affected(sqlite_db, user_1, user_2):
    # Sessão revogada para User 1
    raw_token_u1 = "token-revogado-u1"
    session_u1 = AuthSession(
        id=uuid.uuid4(),
        user_id=user_1.id,
        refresh_token_hash=hash_token(raw_token_u1),
        is_revoked=True,
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )

    # Sessão ativa para User 2
    raw_token_u2 = "token-ativo-u2"
    session_u2 = AuthSession(
        id=uuid.uuid4(),
        user_id=user_2.id,
        refresh_token_hash=hash_token(raw_token_u2),
        is_revoked=False,
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    sqlite_db.add_all([session_u1, session_u2])
    sqlite_db.commit()

    # Reuso disparado para User 1
    with pytest.raises(HTTPException):
        refresh_session(db=sqlite_db, refresh_token=raw_token_u1, client_ip="10.0.0.1")

    # Sessão do User 2 deve continuar intacta e ativa
    sqlite_db.refresh(session_u2)
    assert session_u2.is_revoked is False

    # User 2 consegue fazer refresh normalmente
    data, new_token_u2 = refresh_session(
        db=sqlite_db, refresh_token=raw_token_u2, client_ip="10.0.0.2"
    )
    assert "access_token" in data


def test_expired_unrevoked_token_does_not_revoke_other_sessions(sqlite_db, user_1):
    # Sessão expirada (mas não revogada)
    raw_expired = "token-expirado"
    session_expired = AuthSession(
        id=uuid.uuid4(),
        user_id=user_1.id,
        refresh_token_hash=hash_token(raw_expired),
        is_revoked=False,
        expires_at=datetime.now(UTC) - timedelta(hours=1),
    )

    # Outra sessão ativa válida do mesmo usuário
    raw_active = "token-valido-ativo"
    session_active = AuthSession(
        id=uuid.uuid4(),
        user_id=user_1.id,
        refresh_token_hash=hash_token(raw_active),
        is_revoked=False,
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    sqlite_db.add_all([session_expired, session_active])
    sqlite_db.commit()

    # Apresentar token expirado -> 401 sem cascata
    with pytest.raises(HTTPException) as exc_info:
        refresh_session(db=sqlite_db, refresh_token=raw_expired, client_ip="10.0.0.1")
    assert exc_info.value.status_code == 401

    # A outra sessão NÃO pode ter sido revogada
    sqlite_db.refresh(session_active)
    assert session_active.is_revoked is False


def test_nonexistent_token_returns_401(sqlite_db):
    with pytest.raises(HTTPException) as exc_info:
        refresh_session(
            db=sqlite_db, refresh_token="token-inexistente-xyz", client_ip="10.0.0.1"
        )
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Refresh token inválido"
