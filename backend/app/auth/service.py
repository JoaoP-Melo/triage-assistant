from datetime import UTC, datetime, timedelta
import re
import secrets
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.auth.models import AuthSession, User
from app.auth.schemas import LoginRequest, RegisterDoctorRequest, RegisterRequest
from app.core.security import (
    create_access_token,
    hash_password,
    hash_token,
    verify_password,
)


def validate_strong_password(password: str) -> None:
    """Valida a política de senha forte:

    - Mínimo de 8 caracteres
    - Pelo menos 1 letra maiúscula
    - Pelo menos 1 número
    - Pelo menos 1 caractere especial
    """
    if len(password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A senha deve ter no mínimo 8 caracteres.",
        )
    if not re.search(r"[A-Z]", password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A senha deve conter pelo menos uma letra maiúscula.",
        )
    if not re.search(r"\d", password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A senha deve conter pelo menos um número.",
        )
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>\-_=+[\]\\;/~`]", password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A senha deve conter pelo menos um caractere especial.",
        )


def _create_user(
    db: Session,
    name: str,
    email: str,
    password1: str,
    password2: str,
    role: str,
    specialization: str | None = None,
) -> User:
    """Função interna compartilhada para validação e criação de usuários."""
    if password1 != password2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="As senhas informadas não coincidem.",
        )

    validate_strong_password(password1)

    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="E-mail já cadastrado.",
        )

    hashed_pw = hash_password(password1)
    new_user = User(
        full_name=name,
        email=email,
        hashed_password=hashed_pw,
        role=role,
        specialization=specialization,
        is_active=True,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


def register_user(db: Session, payload: RegisterRequest) -> dict[str, str]:
    """Regras de negócio para o cadastro de pacientes:

    - Reaproveita validações em _create_user
    - Persiste o usuário com role='patient' fixo
    """
    _create_user(
        db=db,
        name=payload.name,
        email=payload.email,
        password1=payload.password1,
        password2=payload.password2,
        role="patient",
    )

    return {"message": "Conta criada com sucesso"}


def register_doctor(db: Session, payload: RegisterDoctorRequest) -> dict[str, str]:
    """Regras de negócio para o cadastro de médicos:

    - Valida se a especialização é informada e válida (não vazia)
    - Reaproveita validações de e-mail e senha em _create_user
    - Persiste o usuário com role='doctor' fixo
    """
    specialization = payload.specialization.strip() if payload.specialization else ""
    if not specialization or len(specialization) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A especialização é obrigatória e deve ter no mínimo 3 caracteres.",
        )

    _create_user(
        db=db,
        name=payload.name,
        email=payload.email,
        password1=payload.password1,
        password2=payload.password2,
        role="doctor",
        specialization=specialization,
    )

    return {"message": "Conta de médico criada com sucesso"}


def login_user(db: Session, payload: LoginRequest) -> tuple[dict[str, Any], str]:
    """Regras de negócio para o login do usuário:

    - Verifica existência do usuário, status ativo e correspondência do hash de senha
    - Gera o Access Token JWT com expiração de 15 minutos
    - Gera o Refresh Token opaco e armazena o hash SHA-256 em auth_sessions
    - Retorna a tupla (dados_da_resposta, refresh_token_puro)
    """
    user = db.query(User).filter(User.email == payload.email).first()
    if (
        not user
        or not user.is_active
        or not verify_password(payload.password, user.hashed_password)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas.",
        )

    # 1. Access Token (JWT - 15 minutos)
    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role},
        expires_delta=timedelta(minutes=15),
    )

    # 2. Refresh Token opaco
    raw_refresh_token = secrets.token_urlsafe(32)
    refresh_token_hash = hash_token(raw_refresh_token)

    # 3. Persiste a sessão em auth_sessions
    expires_at = datetime.now(UTC) + timedelta(days=7)
    session = AuthSession(
        user_id=user.id,
        refresh_token_hash=refresh_token_hash,
        is_revoked=False,
        expires_at=expires_at,
    )
    db.add(session)
    db.commit()

    response_data = {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "name": user.full_name,
            "role": user.role,
        },
    }

    return response_data, raw_refresh_token


def refresh_session(
    db: Session, refresh_token: str | None
) -> tuple[dict[str, Any], str]:
    """Regras de negócio para renovação de sessão (Refresh Token Rotation):

    - Valida a presença do refresh token no cookie
    - Localiza sessão válida e ativa em auth_sessions pelo hash SHA-256
    - Valida status do usuário proprietário da sessão
    - Executa rotação: invalida a sessão atual (is_revoked=True) e cria uma nova
    - Emite novo Access Token (15 min) e novo Refresh Token opaco (7 dias)
    - Retorna a tupla (dados_da_resposta, novo_refresh_token_puro)
    """
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token inválido ou expirado.",
        )

    token_hash = hash_token(refresh_token)
    now = datetime.now(UTC)

    session = (
        db.query(AuthSession)
        .filter(
            AuthSession.refresh_token_hash == token_hash,
            AuthSession.is_revoked.is_(False),
            AuthSession.expires_at > now,
        )
        .first()
    )

    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token inválido",
        )

    user = (
        db.query(User)
        .filter(User.id == session.user_id, User.is_active.is_(True))
        .first()
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token inválido",
        )

    # 1. Rotação do Refresh Token: invalida a sessão anterior
    session.is_revoked = True

    # 2. Emissão do novo Access Token JWT (15 minutos)
    new_access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role},
        expires_delta=timedelta(minutes=15),
    )

    # 3. Emissão e persistência do novo Refresh Token opaco (7 dias)
    new_raw_refresh_token = secrets.token_urlsafe(32)
    new_refresh_token_hash = hash_token(new_raw_refresh_token)
    new_expires_at = datetime.now(UTC) + timedelta(days=7)

    new_session = AuthSession(
        user_id=user.id,
        refresh_token_hash=new_refresh_token_hash,
        is_revoked=False,
        expires_at=new_expires_at,
    )
    db.add(new_session)
    db.commit()

    response_data = {
        "access_token": new_access_token,
        "token_type": "bearer",
    }

    return response_data, new_raw_refresh_token


def logout_user(db: Session, refresh_token: str | None) -> dict[str, str]:
    """Regras de negócio para o encerramento de sessão (logout):

    - Caso não exista refresh token informado, considera a sessão já finalizada
    - Localiza a sessão em auth_sessions pelo hash SHA-256
    - Revoga a sessão logicamente (is_revoked=True) preservando histórico de auditoria
    - Retorna mensagem padronizada e segura
    """
    if not refresh_token:
        return {"message": "Sessão encerrada com sucesso"}

    token_hash = hash_token(refresh_token)
    session = (
        db.query(AuthSession)
        .filter(AuthSession.refresh_token_hash == token_hash)
        .first()
    )

    if session and not session.is_revoked:
        session.is_revoked = True
        db.commit()

    return {"message": "Sessão encerrada com sucesso"}
