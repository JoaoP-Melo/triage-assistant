from fastapi import APIRouter, Cookie, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.auth.schemas import (
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    RefreshResponse,
    RegisterDoctorRequest,
    RegisterRequest,
    RegisterResponse,
)
from app.auth.service import (
    login_user,
    logout_user,
    refresh_session,
    register_doctor,
    register_user,
)
from app.core.database import get_db
from app.core.rate_limit import (
    RATE_LIMIT_LOGIN,
    RATE_LIMIT_REFRESH,
    RATE_LIMIT_REGISTER,
    limiter,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastra um novo paciente",
)
@limiter.limit(RATE_LIMIT_REGISTER)
def register(
    request: Request,
    payload: RegisterRequest,
    db: Session = Depends(get_db),
) -> RegisterResponse:
    """Recebe a requisição de cadastro de paciente e orquestra a chamada para a camada de serviço."""
    result = register_user(db=db, payload=payload)
    return RegisterResponse(**result)


@router.post(
    "/register/doctor",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastra um novo médico",
)
@limiter.limit(RATE_LIMIT_REGISTER)
def register_doctor_endpoint(
    request: Request,
    payload: RegisterDoctorRequest,
    db: Session = Depends(get_db),
) -> RegisterResponse:
    """Recebe a requisição de cadastro de médico e orquestra a chamada para a camada de serviço."""
    result = register_doctor(db=db, payload=payload)
    return RegisterResponse(**result)


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Realiza o login do usuário",
)
@limiter.limit(RATE_LIMIT_LOGIN)
def login(
    request: Request,
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


@router.post(
    "/refresh",
    response_model=RefreshResponse,
    status_code=status.HTTP_200_OK,
    summary="Renova o token de acesso via refresh token",
)
@limiter.limit(RATE_LIMIT_REFRESH)
def refresh(
    request: Request,
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
) -> RefreshResponse:
    """Orquestra a renovação do access token e a rotação do refresh token via cookie seguro."""
    client_ip = request.client.host if request.client else "unknown"
    data, new_refresh_token = refresh_session(
        db=db, refresh_token=refresh_token, client_ip=client_ip
    )

    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=7 * 24 * 60 * 60,  # 7 dias em segundos
        path="/auth",
    )

    return RefreshResponse(**data)


@router.post(
    "/logout",
    response_model=LogoutResponse,
    status_code=status.HTTP_200_OK,
    summary="Encerra a sessão do usuário",
)
def logout(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
) -> LogoutResponse:
    """Orquestra a revogação da sessão no serviço e remove o cookie do refresh token no cliente."""
    result = logout_user(db=db, refresh_token=refresh_token)

    response.delete_cookie(
        key="refresh_token",
        path="/auth",
        httponly=True,
        secure=True,
        samesite="strict",
    )

    return LogoutResponse(**result)
