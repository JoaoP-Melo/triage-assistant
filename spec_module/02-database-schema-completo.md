# 02 — Database Schema Completo (fonte canônica)

> Abra este arquivo **apenas** para tarefas de migration/DBA que afetam mais de um módulo. Para implementar uma rota específica, use o trecho de schema já duplicado dentro do arquivo do módulo correspondente (`03-modulo-auth.md`, `04-modulo-triage-paciente.md`, etc.) — não é necessário ler este arquivo inteiro.

## PostgreSQL (relacional)

### Tabela: `users`
Armazena credenciais de autenticação, perfil básico e nível de acesso (RBAC).

| Campo | Tipo | Restrições / Index | Descrição |
|---|---|---|---|
| `id` | UUID / BIGSERIAL | PRIMARY KEY | Identificador único do usuário. |
| `full_name` | VARCHAR(150) | NOT NULL | Nome completo. |
| `email` | VARCHAR(255) | UNIQUE, NOT NULL, INDEX | E-mail de login. |
| `hashed_password` | VARCHAR(255) | NOT NULL | Hash da senha (bcrypt / argon2). |
| `role` | VARCHAR(20) | NOT NULL, DEFAULT 'patient' | `patient` ou `doctor`. |
| `specialization` | VARCHAR(100) | NULLABLE | Especialidade médica. Obrigatório só se `role='doctor'`. |
| `is_active` | BOOLEAN | NOT NULL, DEFAULT TRUE | Conta ativa/suspensa. |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Data de criação. |

Observações:
- Para `role='patient'`, `specialization` (e `crm`) ficam `NULL`.
- Para `role='doctor'`, `specialization` e `crm` são obrigatórios na validação Pydantic.
- `users.id` é gravado no MongoDB como `user_id` para vincular o histórico clínico.

### Tabela: `auth_sessions`
Gerencia Refresh Tokens ativos, revogação de sessões e detecção de reuso indevido.

| Campo | Tipo | Restrições / Index | Descrição |
|---|---|---|---|
| `id` | UUID | PRIMARY KEY | Identificador da sessão/token. |
| `user_id` | UUID / BIGSERIAL | FK `users.id`, NOT NULL, INDEX | Dono da sessão. |
| `refresh_token_hash` | VARCHAR(255) | NOT NULL, INDEX | Hash SHA-256 do Refresh Token. |
| `is_revoked` | BOOLEAN | NOT NULL, DEFAULT FALSE | Sessão invalidada (ex: logout). |
| `expires_at` | TIMESTAMPTZ | NOT NULL | Expiração do Refresh Token (ex: +7 dias). |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Data do login. |

Boas práticas de segurança:
- Nunca salvar o Refresh Token em texto puro — sempre hash SHA-256.
- Refresh Token Rotation: a cada `/auth/refresh`, o token antigo vira `is_revoked=TRUE` e uma nova sessão é inserida.
- Refresh Token trafega só via cookie `HttpOnly` + `Secure` + `SameSite=Strict`.

## MongoDB Atlas (NoSQL)

### Coleção: `tickets`
Todo o ciclo de vida da triagem: submissão → roteamento híbrido (ML/LLM) → acompanhamento/atribuição pelo médico.

```json
{
  "_id": ObjectId("65f1a23b4c9e8d7f6a5b4c3d"),

  "user_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11", // FK do PostgreSQL (users.id)
  "patient_input": {
    "perceived_severity": 7,
    "symptom_duration_hours": 24,
    "primary_symptoms": ["FEBRE", "DOR_DE_CABACA", "NAUSEA"],
    "description": "Estou com febre alta desde ontem à noite e uma dor forte na cabeça que não passa com analgésico."
  },

  "triage_result": {
    "assigned_specialty": "CLINICA_GERAL",
    "urgency_level": "ALTA",              // BAIXA | MEDIA | ALTA | EMERGENCIA
    "confidence_score": 0.94,
    "processed_by": "ML_XGBOOST",         // ML_XGBOOST | AGENT_LLM
    "llm_justification": null,            // só preenchido se processed_by = AGENT_LLM
    "token_consumption": 0
  },

  "status": "WAITING",                     // WAITING | IN_PROGRESS | COMPLETED | CANCELLED
  "assigned_doctor_id": null,              // FK do PostgreSQL quando um médico assume
  "doctor_feedback": {
    "was_correct_assignment": null
  },

  "ticket_issue_key": "TRIAG-102",
  "created_at": ISODate("2026-09-04T20:00:00Z"),
  "updated_at": ISODate("2026-09-04T20:00:00Z")
}
```
