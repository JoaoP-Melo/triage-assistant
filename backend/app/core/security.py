from datetime import UTC, datetime, timedelta
import hashlib
import os
from typing import Any

import bcrypt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))


def hash_token(token: str) -> str:
    """Gera o hash SHA-256 de um token opaco (ex.: refresh token).

    Args:
        token: Token em texto puro a ser hasheado.

    Returns:
        String hexadecimal com o digest SHA-256 do token.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def hash_password(password: str) -> str:
    """Gera o hash seguro de uma senha em texto puro utilizando bcrypt com salt automático."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica se uma senha em texto puro corresponde ao hash bcrypt armazenado."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """Gera um JWT de acesso assinado com claims padrão e expiração padrão de 15 minutos.

    Args:
        data: Dicionário com os dados (claims) a serem codificados no token.
        expires_delta: Duração personalizada de expiração. Se não informado, utiliza ACCESS_TOKEN_EXPIRE_MINUTES.

    Returns:
        Token JWT assinado em formato string.
    """
    to_encode = data.copy()
    now = datetime.now(UTC)

    if expires_delta is not None:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    # Adiciona claims de expiração (exp) e emissão (iat) ao payload
    to_encode.update({"exp": expire, "iat": now})

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """Decodifica e valida a assinatura e a expiração de um JWT.

    Args:
        token: Token JWT em formato string.

    Returns:
        Dicionário com o payload decodificado.

    Raises:
        jwt.ExpiredSignatureError: Se o token estiver expirado.
        jwt.InvalidTokenError: Se o token for inválido ou a assinatura não conferir.
    """
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


oauth2_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(oauth2_scheme),
) -> dict[str, Any]:
    """Extrai e valida o token JWT do header Authorization: Bearer <token>.

    Retorna um dicionário contendo os dados do usuário (ex: user_id, role).
    Lança HTTPException 401 caso o token esteja ausente, expirado ou inválido.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de acesso ausente.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    try:
        payload = decode_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de acesso expirado.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de acesso inválido.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub") or payload.get("user_id")
    role = payload.get("role")

    if not user_id or not role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token com payload inválido.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {"user_id": str(user_id), "role": str(role), **payload}

