<div align="center">

# 🩺 Triage Assistant

**Triagem clínica inteligente: Machine Learning + IA generativa classificam a especialidade e a urgência de cada paciente e organizam a fila de atendimento dos médicos.**

[![CI/CD](https://github.com/JoaoP-Melo/triage-assistant/actions/workflows/ci.yml/badge.svg)](https://github.com/JoaoP-Melo/triage-assistant/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?logo=typescript&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-4169E1?logo=postgresql&logoColor=white)
![MongoDB](https://img.shields.io/badge/MongoDB-8-47A248?logo=mongodb&logoColor=white)
![XGBoost](https://img.shields.io/badge/XGBoost-ML-EB5B0C)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)

[🎥 Vídeos](#-demonstração-em-vídeo) · [🚀 Como rodar](#-como-rodar-localmente) · [🏗️ Arquitetura](#️-arquitetura) · [🧠 Decisões técnicas](#-decisões-técnicas-que-valem-destaque)

</div>

---

## 💡 O problema

Em filas de pronto atendimento, pacientes graves podem esperar atrás de casos leves e o paciente muitas vezes não sabe qual especialista procurar. O **Triage Assistant** automatiza a primeira etapa: o paciente descreve seus sintomas e o sistema devolve **a especialidade indicada** e **o nível de urgência**; o médico, por sua vez, enxerga uma **fila já priorizada** pela gravidade.

> ⚠️ Projeto de portfólio com fins educacionais. Não é um dispositivo médico e não substitui avaliação profissional.

## ✨ O que o sistema faz

**Para o paciente**
- Cadastro e login seguros
- Formulário de triagem: severidade percebida (1 a 10), duração dos sintomas, 3 sintomas principais (lista controlada) e relato livre
- Resultado imediato com **especialidade recomendada**, **nível de urgência** e protocolo do atendimento

**Para o médico**
- Fila de atendimentos da **sua especialidade**, ordenada por urgência (Emergência > Alta > Média > Baixa) e depois por ordem de chegada
- Paginação ("carregar mais") e atualização da fila
- Finalização de atendimento com confirmação e atualização atômica no banco

## 🧠 Classificação híbrida (ML + LLM)

O núcleo do projeto é um pipeline que combina um modelo clássico, rápido e barato, com um LLM usado só quando o modelo não tem certeza:

```mermaid
flowchart LR
    A[Paciente envia sintomas] --> B[Feature engineering<br/>scalers + binarizer + TF-IDF]
    B --> C[XGBoost]
    C -->|confiança ≥ 90%| D[Resultado ML]
    C -->|confiança < 90% ou falha| E[Fallback LLM<br/>Groq via SDK OpenAI]
    E --> F[Validação Pydantic<br/>+ normalização por allow-list]
    D --> G[(Ticket no MongoDB<br/>status WAITING)]
    F --> G
    G --> H[Fila do médico<br/>ordenada por urgência]
```

- **Especialidades:** Clínica Geral, Cardiologia, Dermatologia, Otorrinolaringologia e Pneumologia
- **Urgência:** Baixa, Média, Alta e Emergência
- A resposta do LLM é forçada a JSON, **validada com Pydantic** e normalizada contra listas permitidas, com retries e fallback seguro se o provedor falhar

## 🏗️ Arquitetura

```mermaid
flowchart TB
    U[Navegador<br/>React + Vite + TS] -->|HTTPS / JWT| API[FastAPI]
    API --> PG[(PostgreSQL<br/>usuários e sessões)]
    API --> MG[(MongoDB<br/>tickets de triagem)]
    API --> ML[XGBoost + scikit-learn]
    API -.fallback.-> LLM[LLM Groq]
    GH[GitHub Actions] -->|testes + build| R[Deploy hook Render]
```

| Camada | Tecnologias |
|---|---|
| Frontend | React 19, TypeScript, Vite, React Router, nginx (build em Docker multi-stage) |
| Backend | Python 3.12, FastAPI, Pydantic, SQLAlchemy 2, PyMongo, Alembic, slowapi |
| Dados | PostgreSQL 17 (contas/sessões) e MongoDB 8 (tickets e resultados de triagem) |
| IA / ML | XGBoost, scikit-learn (TF-IDF, scalers, binarizers), LLM via Groq |
| Auth | JWT de acesso (15 min), refresh token opaco rotativo com revogação em cadeia, bcrypt |
| DevOps | Docker, Docker Compose, GitHub Actions (testes, build e deploy no Render) |
| Qualidade | pytest, Ruff, TypeScript estrito, ESLint |

## 🎥 Demonstração em vídeo

> 💡 **Como adicionar:** edite este arquivo no GitHub, arraste o `.mp4` para dentro do editor (limite de ~100 MB) e ele gera um link `https://github.com/user-attachments/...`. Cole esse link **sozinho em uma linha** que o GitHub exibe o player. Alternativa: suba no YouTube e use `[![Título](URL_DA_THUMB)](URL_DO_VIDEO)`.

### 1. Fluxo do paciente: da triagem ao resultado
`🎬 VÍDEO EM BREVE`

### 2. Fluxo do médico: fila priorizada e finalização de atendimento
`🎬 VÍDEO EM BREVE`

### 3. Projeto rodando com um comando (`docker compose up`)
`🎬 VÍDEO EM BREVE`

## 🚀 Como rodar localmente

**Pré-requisitos:** Docker e Docker Compose. Opcional: uma chave de API da Groq para ativar o fallback de IA (sem ela, o sistema usa um resultado de contingência).

**1. Clone o repositório**
```bash
git clone https://github.com/JoaoP-Melo/triage-assistant.git
cd triage-assistant
```

**2. Crie os arquivos de ambiente**

`.env` (raiz, usado pelo Postgres no compose)
```env
POSTGRES_USER=triage
POSTGRES_PASSWORD=troque-por-uma-senha-forte
POSTGRES_DB=triage_db
```

`backend/.env`
```env
SECRET_KEY=gere-com-openssl-rand-hex-32
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
GROQ_API_KEY=            # opcional
GROQ_MODEL=              # opcional, ex.: modelo disponível na sua conta Groq
RATE_LIMIT_ENABLED=true   # habilitar rate limiting
FORWARDED_ALLOW_IPS=127.0.0.1
```

`frontend/.env`
```env
VITE_API_URL=http://localhost:8000
```

**3. Suba tudo**
```bash
docker compose up --build
```

| Serviço | URL |
|---|---|
| Frontend | http://localhost:5173 |
| API + Swagger | http://localhost:8000/docs |

As migrações do Alembic rodam automaticamente ao iniciar o backend.

### 🧪 Testes
```bash
docker compose up -d db mongodb backend
docker compose exec backend pytest
```
Os testes cobrem as rotas de autenticação, revogação em cadeia, auditoria médica, rate limiting e submissão de triagem. A mesma suíte roda no GitHub Actions a cada push e pull request.

### 🔁 Retreinar o modelo
```bash
cd backend
python app/classification/ml/train.py
```
Gera os artefatos (`model.json` e `.joblib`) em `backend/app/classification/ml/artifacts/`.

## 🔌 Endpoints principais

| Método | Rota | Descrição | Acesso | Rate Limit |
|---|---|---|---|---|
| POST | `/auth/register` | Cadastro de paciente | Público | 3/minuto (IP) |
| POST | `/auth/register/doctor` | Cadastro de médico | Público | 3/minuto (IP) |
| POST | `/auth/login` | Login: devolve JWT e define refresh token em cookie HttpOnly | Público | 5/minuto (IP) |
| POST | `/auth/refresh` | Renova token com rotação e detecção de reuso em cascata | Cookie | 20/minuto (IP) |
| POST | `/auth/logout` | Revoga a sessão atual | Cookie | Não limitado |
| POST | `/triage/submit` | Envia sintomas e recebe especialidade + urgência | Paciente | 10/minuto (JWT/IP) |
| GET | `/triage/queue` | Fila da especialidade do médico (paginada) | Médico | 60/minuto (JWT/IP) |
| PATCH | `/triage/{ticket_id}/finish` | Finaliza ticket gravando auditoria do médico | Médico | Não limitado |

## 🛡️ Segurança, Rate Limiting e Proxy

### 1. Detecção de IP Real atrás de Proxy Reverso (`--proxy-headers` e `--forwarded-allow-ips`)
Em ambientes de produção hospedados atrás de proxies reversos (como Nginx, Render ou Cloudflare), o contêiner do backend recebe conexões TCP originadas do endereço IP interno do próprio proxy.
- **Por que isso importa:** Sem `--proxy-headers` configurado no Uvicorn, todas as requisições de todos os clientes chegam com o mesmo IP (o IP do proxy). Como consequência, o rate limiter compartilharia um único contador global para todos os usuários, bloqueando clientes legítimos indevidamente ao atingir o limite.
- **Segurança contra IP Spoofing:** A flag `--forwarded-allow-ips` **nunca deve ser configurada como `*`** em produção. Se configurada como `*`, qualquer cliente externo pode forjar o cabeçalho `X-Forwarded-For` com um IP arbitrário e burlar completamente o rate limiter. Por padrão, o Dockerfile configura `FORWARDED_ALLOW_IPS` restrito a `127.0.0.1`, devendo receber o bloco/IP confiável do proxy no ambiente (ex: Render).

### 2. Armazenamento de Rate Limit: Limitação da Memória (`memory://`) e Uso de Redis
Por padrão, o rate limiter utiliza `RATE_LIMIT_STORAGE_URI=memory://`, armazenando os contadores de requisições na memória local do processo Uvicorn.
- **Limitação:** Em arquiteturas com múltiplos workers (`--workers > 1`) ou múltiplas réplicas/instâncias em escala horizontal (load balancing), cada processo mantém sua própria contagem isolada, permitindo que um usuário execute `N * limite` requisições no mesmo intervalo.
- **Ambiente de produção distribuído:** Para escalabilidade horizontal perfeita e contagem atômica compartilhada, defina a variável de ambiente `RATE_LIMIT_STORAGE_URI=redis://[:senha]@host:porta/db`.

### 3. Revogação em Cadeia de Refresh Tokens (Detecção de Reuso)
O fluxo de `/auth/refresh` valida se o hash SHA-256 do token recebido já se encontra revogado (`is_revoked = True`). Caso positivo:
- Trata-se de um indicativo de roubo ou vazamento de credenciais (reuso de token já rotacionado).
- Executa imediatamente a revogação atômica em lote de **todas as sessões ativas do usuário** (`UPDATE auth_sessions SET is_revoked = true WHERE user_id = :id AND is_revoked = false`) e efetua o commit antes de retornar o erro.
- Registra aviso nos logs (`WARNING`) com `user_id` e IP de origem (sem expor o token).
- Limpa o cookie `refresh_token` no cliente e responde com HTTP 401 genérico (sem revelar o mecanismo de defesa ao atacante).
- *Limitação*: O access token JWT emitido previamente permanece válido até o término de sua expiração natural (15 minutos).

## 🧩 Decisões técnicas que valem destaque

- **Híbrido ML + LLM com limiar de confiança:** o modelo barato responde na maioria dos casos e o LLM só entra quando a confiança fica abaixo de 90%, o que controla custo e latência.
- **Saída do LLM tratada como dado não confiável:** JSON validado por schema Pydantic, normalização por allow-list, retries com backoff e fallback seguro.
- **Duas bases, cada uma no que faz melhor:** PostgreSQL para dados relacionais e sessões; MongoDB para documentos de triagem de formato flexível, com índice composto para a consulta da fila.
- **Autenticação em camadas:** access token curto mantido só em memória no frontend, refresh token opaco guardado apenas como hash SHA-256, cookie `HttpOnly` + `Secure` + `SameSite=Strict` e rotação a cada renovação.
- **Autorização no servidor:** o papel não é aceito do cliente; as rotas de médico revalidam usuário, papel e especialidade no banco, e a finalização do ticket usa filtro atômico (`_id` + status + especialidade).
- **Sem XSS por construção:** todo texto do usuário é renderizado via JSX, sem `dangerouslySetInnerHTML`.
- **CI/CD completo:** testes no GitHub Actions, build do frontend e disparo de deploy no Render apenas na branch `main`.

## 👤 Autor

**João Pedro Melo**
[GitHub](https://github.com/JoaoP-Melo) · [LinkedIn](https://www.linkedin.com/in/SEU-PERFIL) · seu-email@exemplo.com

Aberto a feedback e a oportunidades! Se curtiu o projeto, deixe uma ⭐.
