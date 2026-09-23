from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.models import AuthSession, User
from app.core.security import hash_token, verify_password


# ============================================================================
# 1. POST /auth/register
# ============================================================================


def test_register_patient_success(client: TestClient, db_session: Session) -> None:
    """Testa o cadastro com sucesso de paciente."""
    payload = {
        "name": "Novo Paciente",
        "email": "novo_paciente@example.com",
        "password1": "SenhaForte123!",
        "password2": "SenhaForte123!",
    }
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 201
    json_data = response.json()
    assert json_data["message"] == "Conta criada com sucesso"

    # Verificações de segurança e banco
    user = (
        db_session.query(User)
        .filter(User.email == "novo_paciente@example.com")
        .first()
    )
    assert user is not None
    assert user.role == "patient"
    assert verify_password("SenhaForte123!", user.hashed_password)

    # Sanitização: a resposta não deve expor campos internos
    assert "hashed_password" not in json_data
    assert "refresh_token_hash" not in json_data


def test_register_patient_duplicate_email(
    client: TestClient, patient_user: User
) -> None:
    """Testa cadastro de paciente com e-mail já cadastrado (409)."""
    payload = {
        "name": "Outro Paciente",
        "email": patient_user.email,
        "password1": "SenhaForte123!",
        "password2": "SenhaForte123!",
    }
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 409
    assert response.json()["detail"] == "E-mail já cadastrado."


def test_register_patient_mismatched_passwords(client: TestClient) -> None:
    """Testa cadastro de paciente com senhas divergentes (400)."""
    payload = {
        "name": "Paciente Erro",
        "email": "divergente@example.com",
        "password1": "SenhaForte123!",
        "password2": "SenhaDiferente123!",
    }
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 400
    assert response.json()["detail"] == "As senhas informadas não coincidem."


def test_register_patient_weak_password(client: TestClient) -> None:
    """Testa cadastro de paciente com senha fraca (8+ caracteres sem maiúscula/número/especial -> 400)."""
    payload = {
        "name": "Paciente Senha Fraca",
        "email": "fraca@example.com",
        "password1": "minhasenhafraca",
        "password2": "minhasenhafraca",
    }
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 400


# ============================================================================
# 2. POST /auth/register/doctor
# ============================================================================


def test_register_doctor_success(client: TestClient, db_session: Session) -> None:
    """Testa cadastro de médico com especialização válida."""
    payload = {
        "name": "Doutora Ana",
        "email": "dra_ana@example.com",
        "password1": "SenhaForte123!",
        "password2": "SenhaForte123!",
        "specialization": "Pediatria",
    }
    response = client.post("/auth/register/doctor", json=payload)
    assert response.status_code == 201
    json_data = response.json()
    assert json_data["message"] == "Conta de médico criada com sucesso"

    user = db_session.query(User).filter(User.email == "dra_ana@example.com").first()
    assert user is not None
    assert user.role == "doctor"
    assert user.specialization == "Pediatria"
    assert verify_password("SenhaForte123!", user.hashed_password)
    assert "hashed_password" not in json_data


def test_register_doctor_missing_or_empty_specialization(client: TestClient) -> None:
    """Testa cadastro de médico sem especialização ou especialização vazia/espaços (400)."""
    payload = {
        "name": "Doutor Sem Especialidade",
        "email": "sem_esp@example.com",
        "password1": "SenhaForte123!",
        "password2": "SenhaForte123!",
        "specialization": "   ",
    }
    response = client.post("/auth/register/doctor", json=payload)
    assert response.status_code == 400


def test_register_doctor_ignore_role_escalation(
    client: TestClient, db_session: Session
) -> None:
    """Garante que tentativa de privilege escalation (role="admin") no payload é ignorada."""
    payload = {
        "name": "Tentativa Admin",
        "email": "hacker@example.com",
        "password1": "SenhaForte123!",
        "password2": "SenhaForte123!",
        "specialization": "Cardiologia",
        "role": "admin",
    }
    response = client.post("/auth/register/doctor", json=payload)
    assert response.status_code == 201

    user = db_session.query(User).filter(User.email == "hacker@example.com").first()
    assert user is not None
    assert user.role == "doctor"  # Role deve permanecer estritamente 'doctor'


def test_register_doctor_duplicate_email(client: TestClient, doctor_user: User) -> None:
    """Testa erro de e-mail duplicado no cadastro de médico (409)."""
    payload = {
        "name": "Outro Medico",
        "email": doctor_user.email,
        "password1": "SenhaForte123!",
        "password2": "SenhaForte123!",
        "specialization": "Dermatologia",
    }
    response = client.post("/auth/register/doctor", json=payload)
    assert response.status_code == 409


def test_register_doctor_mismatched_passwords(client: TestClient) -> None:
    """Testa senhas divergentes no cadastro de médico (400)."""
    payload = {
        "name": "Medico Erro",
        "email": "doc_divergente@example.com",
        "password1": "SenhaForte123!",
        "password2": "SenhaErrada123!",
        "specialization": "Neurologia",
    }
    response = client.post("/auth/register/doctor", json=payload)
    assert response.status_code == 400


def test_register_doctor_weak_password(client: TestClient) -> None:
    """Testa senha fraca no cadastro de médico (400)."""
    payload = {
        "name": "Medico Fraco",
        "email": "doc_fraco@example.com",
        "password1": "minhasenhafraca",
        "password2": "minhasenhafraca",
        "specialization": "Ortopedia",
    }
    response = client.post("/auth/register/doctor", json=payload)
    assert response.status_code == 400


# ============================================================================
# 3. POST /auth/login
# ============================================================================


def test_login_success(client: TestClient, patient_user: User) -> None:
    """Testa login bem-sucedido retornando access_token e cookie HttpOnly de refresh."""
    payload = {
        "email": patient_user.email,
        "password": "Senha123!",
    }
    response = client.post("/auth/login", json=payload)
    assert response.status_code == 200
    json_data = response.json()

    assert "access_token" in json_data
    assert json_data["token_type"] == "bearer"
    assert json_data["user"]["name"] == patient_user.full_name
    assert json_data["user"]["role"] == "patient"
    assert "hashed_password" not in json_data

    # Verifica presença do cookie HttpOnly com refresh_token
    assert "refresh_token" in response.cookies
    cookie_header = response.headers.get("set-cookie", "")
    assert "httponly" in cookie_header.lower()
    assert "samesite=strict" in cookie_header.lower()


def test_login_nonexistent_email(client: TestClient) -> None:
    """Testa login com e-mail inexistente (401 com mensagem genérica)."""
    payload = {
        "email": "inexistente@example.com",
        "password": "Senha123!",
    }
    response = client.post("/auth/login", json=payload)
    assert response.status_code == 401
    assert response.json()["detail"] == "Credenciais inválidas."


def test_login_incorrect_password(client: TestClient, patient_user: User) -> None:
    """Testa login com senha incorreta (401 com mesma mensagem genérica)."""
    payload = {
        "email": patient_user.email,
        "password": "SenhaErrada123!",
    }
    response = client.post("/auth/login", json=payload)
    assert response.status_code == 401
    assert response.json()["detail"] == "Credenciais inválidas."


# ============================================================================
# 4. POST /auth/refresh
# ============================================================================


def test_refresh_success(
    client: TestClient, patient_user: User, db_session: Session
) -> None:
    """Testa renovação de token via refresh token com rotação de sessão."""
    # 1. Efetua login para obter cookie
    login_resp = client.post(
        "/auth/login",
        json={"email": patient_user.email, "password": "Senha123!"},
    )
    raw_refresh_token = login_resp.cookies.get("refresh_token")

    # 2. Chama rota /auth/refresh enviando cookie
    client.cookies.set("refresh_token", raw_refresh_token)
    refresh_resp = client.post("/auth/refresh")
    assert refresh_resp.status_code == 200
    json_data = refresh_resp.json()

    assert "access_token" in json_data
    assert json_data["token_type"] == "bearer"
    assert "refresh_token" in refresh_resp.cookies

    # 3. Verifica rotação no banco de dados (sessão antiga marcada como revogada)
    old_hash = hash_token(raw_refresh_token)
    old_session = (
        db_session.query(AuthSession)
        .filter(AuthSession.refresh_token_hash == old_hash)
        .first()
    )
    assert old_session is not None
    assert old_session.is_revoked is True


def test_refresh_missing_cookie(client: TestClient) -> None:
    """Testa chamada a /auth/refresh sem cookie (401)."""
    client.cookies.clear()
    response = client.post("/auth/refresh")
    assert response.status_code == 401
    assert response.json()["detail"] == "Refresh token inválido ou expirado."


def test_refresh_revoked_or_expired_token(
    client: TestClient, patient_user: User, db_session: Session
) -> None:
    """Testa chamada com refresh token revogado ou expirado (401)."""
    raw_token = "invalid-or-revoked-token"
    token_h = hash_token(raw_token)

    revoked_session = AuthSession(
        user_id=patient_user.id,
        refresh_token_hash=token_h,
        is_revoked=True,
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    db_session.add(revoked_session)
    db_session.commit()

    client.cookies.set("refresh_token", raw_token)
    response = client.post("/auth/refresh")
    assert response.status_code == 401
    assert response.json()["detail"] == "Refresh token inválido"


# ============================================================================
# 5. POST /auth/logout
# ============================================================================


def test_logout_success(
    client: TestClient, patient_user: User, db_session: Session
) -> None:
    """Testa encerramento de sessão com revogação e remoção do cookie."""
    # Login prévio
    login_resp = client.post(
        "/auth/login",
        json={"email": patient_user.email, "password": "Senha123!"},
    )
    raw_refresh_token = login_resp.cookies.get("refresh_token")

    client.cookies.set("refresh_token", raw_refresh_token)
    logout_resp = client.post("/auth/logout")
    assert logout_resp.status_code == 200
    assert logout_resp.json()["message"] == "Sessão encerrada com sucesso"

    # Confirma revogação na base de dados
    token_h = hash_token(raw_refresh_token)
    session = (
        db_session.query(AuthSession)
        .filter(AuthSession.refresh_token_hash == token_h)
        .first()
    )
    assert session is not None
    assert session.is_revoked is True


def test_logout_without_cookie(client: TestClient) -> None:
    """Testa logout sem cookie de refresh (deve responder com sucesso padronizado sem estourar erro)."""
    client.cookies.clear()
    response = client.post("/auth/logout")
    assert response.status_code == 200
    assert response.json()["message"] == "Sessão encerrada com sucesso"
