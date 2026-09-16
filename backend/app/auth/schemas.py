from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    name: str = Field(
        ..., min_length=2, max_length=150, description="Nome completo do paciente"
    )
    email: EmailStr = Field(..., description="E-mail único de acesso")
    password1: str = Field(..., min_length=8, description="Senha de acesso")
    password2: str = Field(..., min_length=8, description="Confirmação da senha")


class RegisterResponse(BaseModel):
    message: str = Field(default="Conta criada com sucesso")


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., description="E-mail cadastrado")
    password: str = Field(..., description="Senha de acesso")


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    role: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class RefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LogoutResponse(BaseModel):
    message: str = Field(default="Sessão encerrada com sucesso")
