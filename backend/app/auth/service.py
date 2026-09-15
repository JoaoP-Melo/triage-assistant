from datetime import datetime, timedelta, timezone
import hashlib
import re
import secrets
from typing import Any, Tuple

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.auth.models import AuthSession, User
from app.auth.schemas import LoginRequest, RegisterRequest
from app.core.security import create_access_token, hash_password, verify_password


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


def register_user(db: Session, payload: RegisterRequest) -> dict[str, str]:
    """Regras de negócio para o cadastro de pacientes:

    - Verifica se as senhas são idênticas
    - Aplica a validação de política de senha forte
    - Verifica unicidade do e-mail
    - Gera o hash seguro da senha
    - Persiste o usuário com role='patient' fixo
    """
    if payload.password1 != payload.password2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="As senhas informadas não coincidem.",
        )

    validate_strong_password(payload.password1)

    existing_user = db.query(User).filter(User.email == payload.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="E-mail já cadastrado.",
        )

    hashed_pw = hash_password(payload.password1)
    new_user = User(
        full_name=payload.name,
        email=payload.email,
        hashed_password=hashed_pw,
        role="patient",
        is_active=True,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"message": "Conta criada com sucesso"}


def login_user(db: Session, payload: LoginRequest) -> Tuple[dict[str, Any], str]:
    """Regras de negócio para o login do usuário:

    - Verifica existência do usuário, status ativo e correspondência do hash de senha
    - Gera o Access Token JWT com expiração de 15 minutos
    - Gera o Refresh Token opaco e armazena o hash SHA-256 em auth_sessions
    - Retorna a tupla (dados_da_resposta, refresh_token_puro)
    """
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not user.is_active or not verify_password(payload.password, user.hashed_password):
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
    refresh_token_hash = hashlib.sha256(raw_refresh_token.encode("utf-8")).hexdigest()

    # 3. Persiste a sessão em auth_sessions
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
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
