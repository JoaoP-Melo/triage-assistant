import os

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

RATE_LIMIT_STORAGE_URI = os.getenv("RATE_LIMIT_STORAGE_URI", "memory://")
_enabled_env = os.getenv("RATE_LIMIT_ENABLED", "true").lower()
RATE_LIMIT_ENABLED = _enabled_env in ("true", "1", "t", "yes")

RATE_LIMIT_LOGIN = os.getenv("RATE_LIMIT_LOGIN", "5/minute")
RATE_LIMIT_REGISTER = os.getenv("RATE_LIMIT_REGISTER", "3/minute")
RATE_LIMIT_REFRESH = os.getenv("RATE_LIMIT_REFRESH", "20/minute")
RATE_LIMIT_TRIAGE_SUBMIT = os.getenv("RATE_LIMIT_TRIAGE_SUBMIT", "10/minute")
RATE_LIMIT_TRIAGE_QUEUE = os.getenv("RATE_LIMIT_TRIAGE_QUEUE", "60/minute")


def get_user_or_ip(request: Request) -> str:
    """Extrai o claim 'sub' do JWT no header Authorization Bearer de forma segura (sem lançar exceções).

    Em caso de ausência, erro de decodificação ou token inválido, faz fallback para o endereço IP do cliente.
    """
    auth_header = request.headers.get("Authorization") or request.headers.get(
        "authorization"
    )
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1].strip()
        try:
            from app.core.security import decode_token

            payload = decode_token(token)
            sub = payload.get("sub") or payload.get("user_id")
            if sub:
                return f"user:{sub}"
        except Exception:
            pass
    return get_remote_address(request)


limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=RATE_LIMIT_STORAGE_URI,
    enabled=RATE_LIMIT_ENABLED,
)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """Handler padronizado para resposta 429 com mensagem em português e header Retry-After."""
    response = JSONResponse(
        status_code=429,
        content={"detail": "Muitas tentativas. Tente novamente em alguns instantes."},
    )
    if hasattr(request.app.state, "limiter"):
        app_limiter = request.app.state.limiter
        view_limit = getattr(request.state, "view_rate_limit", None)
        if view_limit:
            response = app_limiter._inject_headers(response, view_limit)
    if "Retry-After" not in response.headers:
        response.headers["Retry-After"] = "60"
    return response
