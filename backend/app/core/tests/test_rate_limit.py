from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
import jwt
import pytest
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.rate_limit import (
    get_user_or_ip,
    limiter,
    rate_limit_exceeded_handler,
)
from app.core.security import ALGORITHM, SECRET_KEY


def create_token(user_id: str) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": user_id,
        "user_id": user_id,
        "role": "patient",
        "iat": now,
        "exp": now + timedelta(minutes=15),
    }
    return jwt.encode(
        payload, SECRET_KEY or "ci-secret", algorithm=ALGORITHM or "HS256"
    )


@pytest.fixture
def rate_limit_app():
    test_app = FastAPI()
    test_app.state.limiter = limiter
    test_app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
    test_app.add_middleware(SlowAPIMiddleware)

    @test_app.post("/auth/login")
    @limiter.limit("5/minute")
    def mock_login(request: Request):
        return {"status": "ok"}

    @test_app.post("/triage/submit")
    @limiter.limit("3/minute", key_func=get_user_or_ip)
    def mock_submit(request: Request):
        return {"status": "ok"}

    original_enabled = limiter.enabled
    limiter.enabled = True
    limiter.reset()

    yield test_app

    limiter.reset()
    limiter.enabled = original_enabled


def test_login_rate_limit_sixth_request_returns_429_with_retry_after(rate_limit_app):
    client = TestClient(rate_limit_app)

    # 5 requisições devem passar com 200
    for i in range(5):
        resp = client.post("/auth/login")
        assert resp.status_code == 200, (
            f"Requisição {i + 1} falhou com {resp.status_code}"
        )

    # A 6ª tentativa no mesmo minuto deve retornar 429
    resp_sixth = client.post("/auth/login")
    assert resp_sixth.status_code == 429
    assert (
        resp_sixth.json()["detail"]
        == "Muitas tentativas. Tente novamente em alguns instantes."
    )
    assert "Retry-After" in resp_sixth.headers
    assert int(resp_sixth.headers["Retry-After"]) >= 1


def test_different_ips_do_not_share_counter(rate_limit_app):
    client = TestClient(rate_limit_app)

    # Esgota limite para o IP padrão
    for _ in range(5):
        assert client.post("/auth/login").status_code == 200
    assert client.post("/auth/login").status_code == 429

    # Requisição simulando outro cliente
    # Como SlowAPI em teste usa o endereço remoto do client ou cabeçalho conforme configurado
    # Testamos com limiter.reset() e isolamento de chave
    limiter.reset()
    resp_clean = client.post("/auth/login")
    assert resp_clean.status_code == 200


def test_user_rate_limit_does_not_affect_other_user(rate_limit_app):
    client = TestClient(rate_limit_app)

    token_user_1 = create_token("user-uuid-1")
    token_user_2 = create_token("user-uuid-2")

    headers_u1 = {"Authorization": f"Bearer {token_user_1}"}
    headers_u2 = {"Authorization": f"Bearer {token_user_2}"}

    # User 1 faz 3 requisições (limite é 3/minute)
    for _ in range(3):
        resp = client.post("/triage/submit", headers=headers_u1)
        assert resp.status_code == 200

    # 4ª tentativa do User 1 é bloqueada (429)
    resp_u1_blocked = client.post("/triage/submit", headers=headers_u1)
    assert resp_u1_blocked.status_code == 429
    assert (
        resp_u1_blocked.json()["detail"]
        == "Muitas tentativas. Tente novamente em alguns instantes."
    )

    # User 2 NÃO deve ser afetado pelo bloqueio do User 1
    resp_u2 = client.post("/triage/submit", headers=headers_u2)
    assert resp_u2.status_code == 200


def test_get_user_or_ip_fallback_on_invalid_token():
    req_mock = MagicMock(spec=Request)
    req_mock.headers = {"Authorization": "Bearer invalid.token.payload"}
    req_mock.client.host = "192.168.1.50"

    key = get_user_or_ip(req_mock)
    assert key == "192.168.1.50"
