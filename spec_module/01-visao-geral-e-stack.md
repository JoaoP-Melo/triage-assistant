# 01 — Visão Geral e Stack

> Leia este arquivo apenas na primeira tarefa do projeto, para contexto geral. Não é necessário reabri-lo depois — o arquivo do módulo específico já tem tudo que você precisa para implementar uma rota.

## Projeto
**Simulador de Agendamento Inteligente** — versão 1.0.0.

Plataforma híbrida de inteligência e roteamento de triagem médica, em arquitetura Fullstack (React + FastAPI), que classifica a urgência e a especialidade médica de um paciente a partir dos sintomas informados, usando roteamento de dois níveis (ML rápido + fallback LLM) para otimizar tempo de resposta e custo.

## Stack

| Camada | Função principal | Tecnologias |
|---|---|---|
| Frontend | Formulário do paciente + Kanban/Dashboard do médico | React (TypeScript) + Tailwind |
| Backend | Autenticação JWT, validações e orquestração do pipeline | Python, FastAPI, Celery, JWT, Scikit-Learn, Pydantic, Pytest |
| Roteamento Híbrido | Classificação rápida por ML (≥90%) ou fallback com LLM | XGBoost + Gemini/OpenAI |
| Fila & Banco | Processamento assíncrono e persistência | Redis + MongoDB Atlas + PostgreSQL |
| Integração Externa | Criação automática de chamados corporativos | Jira REST API |
| Infra & MLOps | Testes automatizados e deploy contínuo | Docker + GitHub Actions + AWS |

## Arquitetura (Monólito Modular)

Backend em FastAPI, frontend em React + TypeScript. Persistência poliglota:
- **PostgreSQL (relacional):** credenciais de autenticação, hashes de senha e perfis de usuário (ACID).
- **MongoDB Atlas (NoSQL):** formulários de triagem, textos livres e payloads dinâmicos gerados pela IA.
- **Redis + Celery:** filas de tarefas assíncronas e rate limiting.

## Padrões de qualidade (Clean Code / SOLID)
- Rotas (`router.py`) só orquestram: recebem requisição, injetam dependências, chamam o `service.py`.
- `service.py` (um por módulo) concentra toda regra de negócio, validação e persistência.
- `core/` isola sessão de banco e funções genéricas de segurança (JWT, hash).
- Validação estrita de entrada/saída via Pydantic, inclusive forçando a LLM a retornar JSON estrito.
- CI/CD: GitHub Actions roda pytest e linters a cada push.

## Segurança (visão geral — detalhes no `03-modulo-auth.md`)
- JWT Access Token, expiração curta de 15 min.
- Refresh Token opaco em cookie `HttpOnly` + `Secure` + `SameSite=Strict`.
- RBAC separando `patient` e `doctor`.
- Rate Limiting (SlowAPI + Redis) contra abuso e controle de custo de IA.

## Fluxo de dados (alto nível)
1. Paciente preenche o formulário de triagem no frontend (React + TS).
2. Backend aplica Rate Limiting (Redis/SlowAPI).
3. Backend transforma os dados (MinMaxScaler, StandardScaler, MultiLabelBinarizer, TfidfVectorizer) → matriz `X_final`.
4. `X_final` passa pelo modelo de ML (XGBoost). Se confiança ≥ 90%, classificação é aceita direto; senão, cai no fallback LLM.
5. Resultado é persistido no MongoDB (`tickets`), evento vai para a fila Redis/Celery (dashboards em tempo real), e um worker cria automaticamente um card no Jira.
6. Médico acessa o Dashboard Kanban e vê apenas os tickets da sua especialidade/atribuídos a ele.

## Infraestrutura e Deploy
- Containerização completa (frontend, backend, workers Celery, Redis) via Docker Compose.
- CI/CD: GitHub Actions roda testes (pytest) e linters a cada push.
- Hospedagem — Fase 1: Render + MongoDB Atlas. Fase 2: migração para AWS EC2.

## KPIs (métricas de sucesso)
- Redução de 70% no consumo de tokens via roteamento híbrido.
- Redução de 85% no tempo inicial de triagem (< 3 segundos).
- 94% de precisão na atribuição correta das especialidades médicas.

## Módulos do sistema (referência rápida)
- `auth` — cadastro, login, sessões, RBAC.
- `triage` — submissão do formulário do paciente e listagem de tickets do médico.
- `ml` — pipeline de feature engineering e inferência do modelo supervisionado.
- `assistente_ia` — fallback via LLM para casos de baixa confiança.
- Integrações (`Jira`) e infraestrutura descritas em `08-integracoes-e-infra.md`.
