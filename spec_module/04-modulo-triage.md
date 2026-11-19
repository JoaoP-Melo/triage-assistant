# 04-modulo-triage-paciente

> Arquivo autossuficiente: contém o trecho de schema necessário, as três rotas de backend (submissão do paciente, fila do médico e finalização de atendimento) e a especificação do frontend da triagem. Não é necessário abrir outros arquivos para trabalhar neste módulo.

## Schema de dado usado por este módulo (MongoDB — coleção `tickets`)

Este endpoint só **cria** o documento; os campos abaixo são os relevantes para a submissão do paciente (o restante do documento, como `assigned_doctor_id` e `doctor_feedback`, pertence ao módulo do médico, ver `05-modulo-dashboard-medico.md`):

```json
{
  "user_id": "a0eebc99-...",                // FK do PostgreSQL (users.id), extraído do JWT
  "patient_input": {
    "perceived_severity": 7,                 // 1 a 10
    "symptom_duration_hours": 24,
    "primary_symptoms": ["FEBRE", "DOR_DE_CABACA", "NAUSEA"], // exatamente 3, de lista fixa
    "description": "texto livre"
  },
  "triage_result": {
    "assigned_specialty": "CLINICA_GERAL",
    "urgency_level": "ALTA",                 // BAIXA | MEDIA | ALTA | EMERGENCIA
    "confidence_score": 0.94,
    "processed_by": "ML_XGBOOST",            // ML_XGBOOST | AGENT_LLM
    "llm_justification": null,
    "token_consumption": 0
  },
  "status": "WAITING",                       // status inicial sempre WAITING
  "created_at": ISODate("...")
}
```

## Rotas

O módulo possui três operações: submissão de triagem pelo paciente, consulta da fila pelo médico e finalização de um atendimento pelo médico. Todas exigem autenticação JWT por meio de `get_current_user`.

### 1. `POST /triage/submit`

- **Resumo:** submissão de triagem de sintomas do paciente.
- **Status HTTP de sucesso:** `201 Created`.
- **Response model:** `TriageSubmitResponse`.
- **Rate limiting:** `RATE_LIMIT_TRIAGE_SUBMIT`, usando `get_user_or_ip` como chave.
- **Dependências:** usuário autenticado (`get_current_user`) e conexão com MongoDB (`get_mongo_db`).
- **Regras (`service.py`):**
  - Capturar `user_id` de forma segura a partir do usuário autenticado; nunca confiar em um `user_id` enviado no corpo da requisição.
  - Esta operação é destinada ao paciente. Validar no serviço que o usuário autenticado possui `role='patient'`.
  - Receber os dados de sintomas definidos por `TriageSubmitRequest`.
  - Repassar os dados ao fluxo de classificação de triagem e persistir o ticket na coleção `tickets`, com status inicial `WAITING`.
  - Retornar os dados sanitizados definidos por `TriageSubmitResponse`.
- **Função chamada:** `submit_triage(payload, current_user, mongo_db)`.
- **Retorno:** `TriageSubmitResponse`, com os dados do resultado da submissão.

### 2. `GET /triage/queue`

- **Resumo:** consulta a fila de atendimentos abertos da especialidade do médico autenticado.
- **Status HTTP de sucesso:** `200 OK`.
- **Response model:** `TriageQueueResponse`.
- **Rate limiting:** `RATE_LIMIT_TRIAGE_QUEUE`, usando `get_user_or_ip` como chave.
- **Parâmetros de query:**
  - `limit`: quantidade máxima de itens retornados; padrão `20`, mínimo `1` e máximo `50`.
  - `offset`: deslocamento para paginação; padrão `0` e mínimo `0`.
- **Dependências:** usuário autenticado (`get_current_user`), sessão PostgreSQL (`get_db`) e conexão MongoDB (`get_mongo_db`).
- **Regras (`service.py`):**
  - A operação é destinada a médicos. Validar que o usuário autenticado possui `role='doctor'`.
  - Retornar somente tickets abertos com status `WAITING` que correspondam à especialidade médica do usuário autenticado.
  - Aplicar paginação com `limit` e `offset`.
  - Não confiar em especialidade ou identidade de médico fornecidas pelo cliente; utilizar os dados do usuário autenticado.
- **Função chamada:** `get_doctor_triage_queue(current_user, pg_db, mongo_db, limit, offset)`.
- **Retorno:** `TriageQueueResponse`.

### 3. `PATCH /triage/{ticket_id}/finish`

- **Resumo:** finalização de um atendimento aberto da especialidade médica do usuário autenticado.
- **Status HTTP de sucesso:** `200 OK`.
- **Response model:** `TriageFinishResponse`.
- **Parâmetro de caminho:**
  - `ticket_id`: identificador do ticket a ser finalizado.
- **Dependências:** usuário autenticado (`get_current_user`), sessão PostgreSQL (`get_db`) e conexão MongoDB (`get_mongo_db`).
- **Regras (`service.py`):**
  - A operação é destinada a médicos. Validar que o usuário autenticado possui `role='doctor'`.
  - Validar que o ticket pode ser finalizado e pertence à especialidade do médico autenticado.
  - Executar a atualização de forma atômica para evitar que dois processos finalizem simultaneamente o mesmo atendimento.
  - Não confiar em identidade ou especialidade de médico fornecidas pelo cliente; utilizar os dados do usuário autenticado.
- **Função chamada:** `finish_doctor_triage_ticket(ticket_id, current_user, pg_db, mongo_db)`.
- **Retorno:** `TriageFinishResponse`.

---

## Frontend (React + TypeScript)

Pasta: `frontend/src/modules/triage/`

```
modules/triage/
├── pages/
│   ├── TriageFormPage.tsx     # tela do formulário
│   └── TriageResultPage.tsx    # tela de resultado após submissão
├── components/
│   ├── SeveritySlider.tsx      # 1 a 10
│   ├── SymptomDurationInput.tsx
│   ├── SymptomsMultiSelect.tsx # seleção fixa, exatamente 3 itens
│   └── DescriptionTextarea.tsx
├── services/
│   └── triageService.ts        # submitTriage() — chama POST /triage/submit; pode centralizar chamadas às demais rotas conforme os módulos consumidores
├── types/
│   └── triage.types.ts         # espelha patient_input e a resposta do backend
└── hooks/
    └── useTriageForm.ts        # estado do formulário + validação
```

### Regras específicas deste módulo no frontend
- O formulário de submissão e a tela de resultado do paciente só são acessíveis a usuários autenticados com `role='patient'` — proteja essas rotas com `<ProtectedRoute role="patient">` definido no módulo `auth`.
- A consulta da fila (`GET /triage/queue`) e a finalização (`PATCH /triage/{ticket_id}/finish`) são operações exclusivas de médicos autenticados (`role='doctor'`). As telas que consumirem essas operações devem usar proteção de rota para médicos.
- O Access Token já está disponível no `AuthContext` (módulo `auth`) e é anexado automaticamente pelo interceptor do axios (`Authorization: Bearer <token>`) — este módulo não precisa lidar com autenticação diretamente, só consumir `useAuth()` se precisar exibir dados do usuário.
- **Validação client-side (espelha a regra de negócio, para UX):**
  - `perceived_severity`: inteiro entre 1 e 10.
  - `symptom_duration_hours`: número positivo.
  - `primary_symptoms`: exatamente 3 itens selecionados de uma lista fixa (a lista de sintomas disponíveis deve ser definida como constante compartilhada, ex.: `constants/symptoms.ts`, para manter consistência com o que o backend espera).
  - `description`: texto livre obrigatório, com um mínimo razoável de caracteres para gerar contexto útil à IA.
- Após submissão bem-sucedida, redirecionar para `TriageResultPage`, exibindo `ticket_id`, `assigned_specialty`, `urgency_level` (com destaque visual por cor — ex.: vermelho para `EMERGENCIA`) e `status`.
- Tratar estado de carregamento (o roteamento híbrido pode levar alguns segundos se cair no fallback LLM) e estado de erro (ex.: rate limit atingido — exibir mensagem amigável pedindo para tentar novamente em instantes).
