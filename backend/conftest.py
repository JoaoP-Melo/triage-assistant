import os
from typing import Generator

from dotenv import load_dotenv
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Carrega as variáveis de ambiente do arquivo backend/.env
load_dotenv()

# Obtém a URL do banco de dados de teste (com fallback caso não esteja configurado)
TEST_DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

from app.auth.models import User
from app.core.database import Base, get_db
from app.core.security import hash_password
from app.main import app


@pytest.fixture(scope="session", autouse=True)
def setup_db() -> Generator[None, None, None]:
    """Cria as tabelas no banco de dados de teste PostgreSQL e remove ao final da sessão de testes."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Fornece uma sessão isolada de banco de dados por teste com rollback ao final para não deixar sujeira."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """TestClient do FastAPI utilizando a sessão do banco de testes PostgreSQL."""

    def _override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def patient_user(db_session: Session) -> User:
    """Factory fixture para criar um usuário paciente com senha com hash seguro."""
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
    """Factory fixture para criar um usuário médico com senha com hash seguro."""
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
