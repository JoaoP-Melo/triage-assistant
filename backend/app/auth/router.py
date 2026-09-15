from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.auth.schemas import LoginRequest, LoginResponse, RegisterRequest, RegisterResponse
from app.auth.service import login_user, register_user
from app.core.database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastra um novo paciente",
)
def register(
    payload: RegisterRequest,
    db: Session = Depends(get_db),
) -> RegisterResponse:

    """Recebe a requisição de cadastro de paciente e orquestra a chamada para a camada de serviço."""

    result = register_user(db=db, payload=payload)

    return RegisterResponse(**result)


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Realiza o login do usuário",
)
def login(
    payload: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> LoginResponse:

    """Recebe as credenciais, orquestra a autenticação no serviço e injeta o refresh token em cookie seguro HttpOnly."""
    data, refresh_token = login_user(db=db, payload=payload)

    # Configuração do cookie seguro com Refresh Token (HttpOnly + Secure + SameSite=Strict)
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=7 * 24 * 60 * 60,  # 7 dias em segundos
        path="/auth",
    )

    return LoginResponse(**data)
