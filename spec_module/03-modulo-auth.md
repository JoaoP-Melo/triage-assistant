# 03 — Módulo Auth (Autenticação e Sessões)

> Arquivo autossuficiente: contém o schema de banco necessário, as regras de arquitetura, as 5 rotas do módulo e a especificação do frontend. O cadastro de pacientes e o cadastro de médicos são realizados por endpoints separados. Não é necessário abrir outros arquivos para trabalhar neste módulo.

## Schema de banco usado por este módulo (PostgreSQL)

### Tabela `users`

Modelo SQLAlchemy:

```python
class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name = Column(String(150), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="patient")
    specialization = Column(String(100), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
```

| Campo | Tipo | Restrições |
|---|---|---|
| id | UUID | PK, valor padrão `uuid.uuid4` |
| full_name | VARCHAR(150) | NOT NULL |
| email | VARCHAR(255) | UNIQUE, NOT NULL, INDEX |
| hashed_password | VARCHAR(255) | NOT NULL |
| role | VARCHAR(20) | NOT NULL, DEFAULT `'patient'` |
| specialization | VARCHAR(100) | NULLABLE; preenchido para médicos |
| is_active | BOOLEAN | NOT NULL, DEFAULT `TRUE` |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT `now()` |

Os valores de perfil utilizados pelo módulo são `patient` e `doctor`. O campo `specialization` armazena a especialidade do médico. Não existe campo `crm` no modelo `User` especificado atualmente.

### Tabela `auth_sessions`

| Campo | Tipo | Restrições |
|---|---|---|
| id | UUID | PK |
| user_id | UUID | FK `users.id`, NOT NULL, INDEX |
| refresh_token_hash | VARCHAR(255) | NOT NULL, INDEX (hash SHA-256, nunca o token puro) |
| is_revoked | BOOLEAN | NOT NULL, DEFAULT `FALSE` |
| expires_at | TIMESTAMPTZ | NOT NULL (ex.: criação + 7 dias) |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT `now()` |

## Regras de arquitetura deste módulo

- `router.py`: só orquestra (recebe requisição, injeta dependências, chama `service.py` e devolve resposta). Nenhuma regra de negócio deve ficar aqui.
- `service.py`: concentra as regras de negócio — validação de e-mail duplicado, confirmação e política de senha, hash de senha, geração/decodificação de JWT, geração e rotação de Refresh Token e persistência.
- `core/`: injeção da sessão do banco (`get_db`) e funções genéricas reutilizáveis de decodificação/criação de token e hash de senha.
- Respostas sempre sanitizadas: nunca expor `hashed_password`, `refresh_token_hash` ou qualquer detalhe interno do banco.
- O cadastro público de pacientes e o cadastro de médicos devem permanecer separados. O endpoint de cadastro de pacientes não pode criar usuários com perfil `doctor`.

## Rotas

### 1. `POST /auth/register` — cadastro de pacientes

- **Finalidade:** cadastrar exclusivamente usuários com perfil de paciente.
- **Payload (Pydantic):** `name`, `email`, `password1`, `password2`.
- **Dependência:** sessão do banco (`core`).
- **Regras (`service.py`):**
  - Verificar se `email` já está cadastrado.
  - Validar `password1 == password2`.
  - Validar a política de senha forte definida pelo módulo (mínimo de caracteres, maiúscula, número e caractere especial).
  - Gerar hash seguro da senha e persistir na tabela `users`.
  - Definir `role='patient'` no backend. O cliente não pode escolher ou sobrescrever o perfil.
  - Mapear o campo recebido `name` para `full_name` no banco.
- **Retorno:** `{"message": "Conta criada com sucesso"}`.

### 2. `POST /auth/register_doctor_endpoint` — cadastro de médicos

- **Finalidade:** cadastrar usuários com perfil de médico. Esta rota é separada de `/auth/register`, que continua exclusiva para pacientes.
- **Payload (Pydantic):**

```python
name: str = Field(
    ..., min_length=2, max_length=150, description="Nome completo do médico"
)
email: EmailStr = Field(..., description="E-mail único de acesso")
password1: str = Field(..., min_length=8, description="Senha de acesso")
password2: str = Field(..., min_length=8, description="Confirmação da senha")
specialization: str = Field(
    ..., min_length=3, max_length=100, description="Especialidade médica"
)
```

- **Dependência:** sessão do banco (`core`).
- **Regras (`service.py`):**
  - Verificar se `email` já está cadastrado.
  - Validar `password1 == password2`.
  - Aplicar também as regras de segurança de senha do módulo; as restrições mínimas de tamanho do schema devem ser respeitadas.
  - Gerar hash seguro da senha. Nunca persistir a senha em texto puro.
  - Mapear `name` para `full_name`.
  - Persistir `specialization` no campo homônimo da tabela `users`.
  - Definir `role='doctor'` no backend. O cliente não deve controlar esse campo.
  - Não exigir nem persistir `crm`: esse campo não faz parte do payload nem do modelo `User` especificado.
- **Retorno:** não especificado nesta atualização. Manter o contrato de resposta já implementado no backend; não inventar campos de resposta.

### 3. `POST /auth/login` — autenticação

- **Payload (Pydantic):** `email`, `password`.
- **Dependência:** sessão do banco (`core`).
- **Regras (`service.py`):**
  - Consultar o usuário pelo `email` e validar o hash da senha.
  - Considerar o estado `is_active` do usuário antes de permitir a autenticação.
  - Gerar Access Token (JWT), com expiração de 15 minutos.
  - Gerar Refresh Token opaco e salvar seu hash em `auth_sessions`, vinculado ao `user_id`.
  - Enviar o Refresh Token somente via cookie `Set-Cookie` com `HttpOnly`, `Secure` e `SameSite=Strict`.
- **Retorno:** `access_token`, tipo do token e dados básicos do usuário para navegação, incluindo nome e perfil (`role`). Nunca retornar hashes ou o Refresh Token em texto puro no JSON.

### 4. `POST /auth/refresh` — renovação de sessão

- **Gatilho:** chamada automática do frontend quando o Access Token expirar ou uma requisição receber `401` por token inválido/expirado.
- **Dependência:** sessão do banco e leitura do Refresh Token via cookie.
- **Regras (`service.py`):**
  - Ler o Refresh Token do cookie.
  - Validar a sessão correspondente em `auth_sessions` (existe, não revogada e não expirada).
  - Aplicar Refresh Token Rotation: revogar a sessão/token anterior e criar um novo Access Token e um novo Refresh Token, persistindo somente o hash do novo Refresh Token.
  - Atualizar o cookie no navegador com o novo Refresh Token.
- **Retorno:** novo `access_token` no corpo JSON.

### 5. `POST /auth/logout` — encerramento de sessão

- **Dependência:** sessão do banco e leitura do Refresh Token via cookie.
- **Regras (`service.py`):**
  - Ler o Refresh Token do cookie.
  - Localizar a sessão correspondente em `auth_sessions` e revogá-la (ou excluí-la fisicamente, conforme o padrão já adotado no projeto).
  - Instruir o navegador a apagar o cookie (`Set-Cookie` com expiração no passado), usando os mesmos atributos relevantes do cookie original.
- **Retorno:** mensagem mínima confirmando o encerramento, sem expor o token ou o estado interno da sessão.

---

## Frontend (React + TypeScript)

Pasta: `frontend/src/modules/auth/`

```text
modules/auth/
├── pages/
│   ├── LoginPage.tsx
│   ├── RegisterPage.tsx
│   └── RegisterDoctorPage.tsx
├── components/
│   ├── LoginForm.tsx
│   ├── RegisterForm.tsx
│   └── RegisterDoctorForm.tsx
├── services/
│   └── authService.ts        # login, register (paciente), registerDoctor, refresh, logout
├── types/
│   └── auth.types.ts         # espelha os payloads/retornos do backend
├── hooks/
│   └── useAuth.ts             # consome o AuthContext
└── context/
    └── AuthContext.tsx        # estado global: access_token, user, isAuthenticated
```

### Regras específicas deste módulo no frontend

- **Onde guardar o Access Token:** em memória, dentro do `AuthContext` (state do React). Nunca em `localStorage`/`sessionStorage`. O Refresh Token nunca deve ser acessível via JavaScript: fica somente no cookie `HttpOnly`.
- **Cliente HTTP:** uma instância única do axios (`frontend/src/lib/api.ts`) com `withCredentials: true`, para que o cookie do Refresh Token seja enviado automaticamente quando necessário. O frontend não deve manipular o cookie manualmente.
- **Interceptor de refresh automático:** um response interceptor do axios captura erros `401`, chama `POST /auth/refresh` uma única vez, atualiza o `access_token` no `AuthContext` e repete a requisição original. Se o `/refresh` também falhar, limpa o contexto e redireciona para `LoginPage`. A própria chamada de refresh não deve entrar em um ciclo de novas tentativas.
- **Formulários:** `LoginForm.tsx`, `RegisterForm.tsx` e `RegisterDoctorForm.tsx` fazem validações client-side apenas para UX. A validação real e definitiva é sempre a do backend.
- **Cadastro de paciente:** `RegisterForm.tsx` chama `authService.register()` e o endpoint `POST /auth/register`. Não deve enviar ou permitir selecionar `role`.
- **Cadastro de médico:** `RegisterDoctorForm.tsx` chama `authService.registerDoctor()` e o endpoint `POST /auth/register_doctor_endpoint`, enviando `name`, `email`, `password1`, `password2` e `specialization`. Não deve enviar ou permitir selecionar `role`; o backend define `doctor`.
- **Login:** existe um único fluxo de login para pacientes e médicos. O perfil retornado pelo backend determina as permissões e o redirecionamento após autenticação.
- **Roteamento por perfil (RBAC no frontend):** após login, `patient` vai para a tela de triagem (`04-modulo-triage-paciente.md`) e `doctor` vai para o Kanban (`05-modulo-dashboard-medico.md`). Use um componente de rota protegida (ex.: `<ProtectedRoute role="doctor">`) que verifica `isAuthenticated` e `role` do `AuthContext` antes de renderizar a página. A autorização efetiva também deve ser validada no backend.
- **Logout:** chama `authService.logout()`, que dispara `POST /auth/logout` e, independentemente da resposta, limpa o `AuthContext` local e redireciona para o login.
