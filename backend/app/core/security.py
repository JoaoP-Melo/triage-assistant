import os
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import bcrypt
import jwt
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))


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
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Gera um JWT de acesso assinado com claims padrão e expiração padrão de 15 minutos.

    Args:
        data: Dicionário com os dados (claims) a serem codificados no token.
        expires_delta: Duração personalizada de expiração. Se não informado, utiliza ACCESS_TOKEN_EXPIRE_MINUTES.

    Returns:
        Token JWT assinado em formato string.
    """
    to_encode = data.copy()
    now = datetime.now(timezone.utc)

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
