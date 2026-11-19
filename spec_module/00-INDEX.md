# ÍNDICE DA ESPECIFICAÇÃO — LEIA-ME PRIMEIRO

Esta especificação foi dividida em arquivos pequenos, um por módulo/responsabilidade, para evitar que o agente de desenvolvimento precise reler o projeto inteiro a cada tarefa.

## Regras de leitura (obrigatórias para o agente)

1. **Nunca leia o projeto inteiro.** Identifique a qual módulo a tarefa pertence usando a tabela abaixo e abra **apenas** o arquivo correspondente.
2. **Cada arquivo de módulo é autossuficiente.** Ele já contém o trecho do schema de banco necessário, as rotas de backend daquele módulo e a especificação do frontend correspondente. Não é necessário abrir outro arquivo além dele para implementar a tarefa.
3. **Não releia um arquivo já lido na mesma sessão/tarefa.** Guarde as informações relevantes no contexto e reutilize-as. Só releia se o usuário disser explicitamente que o conteúdo mudou.
4. **Se a tarefa for ambígua**, pergunte ao usuário a qual módulo ela pertence antes de abrir mais de um arquivo "para checar".
5. `02-database-schema-completo.md` é a fonte canônica do banco de dados. Abra-o **somente** para tarefas de migration/DBA que afetam mais de um módulo — para implementar rotas normais, use o trecho de schema já duplicado dentro do arquivo do módulo específico.
6. Ao terminar uma tarefa, não é necessário reconfirmar lendo os arquivos de novo — confie no que já foi lido nesta sessão.

## Mapa de módulos

| Arquivo | Quando abrir |
|---|---|
| `01-visao-geral-e-stack.md` | Apenas na primeira tarefa do projeto, para contexto geral (arquitetura, stack, KPIs). Não precisa reabrir depois. |
| `02-database-schema-completo.md` | Somente para migrations ou alterações estruturais no banco que cruzam módulos. |
| `03-modulo-auth.md` | Cadastro, login, refresh, logout, sessões, RBAC. |
| `04-modulo-triage-paciente.md` | Formulário de triagem do paciente e rota `POST /triage/submit`. |
| `05-modulo-dashboard-medico.md` | Kanban do médico e rota `GET /triage/my-assigned-tickets`. |
| `06-modulo-ml.md` | Pipeline de Machine Learning (`POST /ml/predict`). Módulo interno, sem frontend. |
| `07-modulo-assistente-ia.md` | Fallback via LLM (`POST /assistant/classify`). Módulo interno, sem frontend. |
| `08-integracoes-e-infra.md` | Integração com Jira, Docker, CI/CD e deploy. |

## Convenção de frontend (vale para todos os módulos que têm interface)

Cada módulo do frontend vive em `frontend/src/modules/<nome-do-modulo>/`, com a estrutura:

```
modules/<nome-do-modulo>/
├── pages/        # telas/rotas do React Router
├── components/   # componentes menores e reutilizáveis da tela
├── services/      # chamadas HTTP (axios) — único lugar que fala com o backend
├── types/         # interfaces TypeScript espelhando os schemas Pydantic
└── hooks/         # estado local, contexto, lógica de UI
```

Os detalhes específicos de cada módulo (quais telas, quais campos, quais services) estão na seção **"Frontend (React + TypeScript)"** dentro do respectivo arquivo de módulo. Módulos que são só de backend (`ml`, `assistente_ia`) não têm essa seção.
