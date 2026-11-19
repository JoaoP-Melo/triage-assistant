# 08 — Integrações Externas e Infraestrutura

> Arquivo autossuficiente. Abra apenas para tarefas relacionadas à integração com Jira, containerização, CI/CD ou deploy.

## Integração Externa (Jira REST API) `Em desenvolvimento`
- Um worker (Celery) dispara uma requisição HTTP para a API do Jira, criando uma issue/ticket automatizado na fila corporativa com as informações pré-preenchidas da triagem.
- Disparo assíncrono: a mensagem/evento do ticket recém-criado é enviada para a fila gerenciada por Redis + Celery.
- O `ticket_issue_key` retornado pelo Jira é gravado de volta no documento do MongoDB (`tickets.ticket_issue_key`).

## Processamento Assíncrono (Redis + Celery) `Em desenvolvimento`
- Usado para: atualizar dashboards em tempo real, gerenciar concorrência, e disparar a integração com o Jira sem bloquear a resposta ao paciente.
- Também usado pelo SlowAPI para controle de Rate Limiting das rotas expostas ao paciente/médico.

## Containerização e Deploy
- Toda a aplicação (Frontend, Backend FastAPI, Workers Celery, Redis) é empacotada em containers isolados via Docker Compose.
- **CI/CD:** cada `git push` no GitHub aciona o GitHub Actions, que executa testes unitários (`pytest`) e linters.
- **Hospedagem:**
  - Fase 1: deploy automatizado no Render, conectado ao MongoDB Atlas.
  - Fase 2: migração para instância AWS EC2.

## KPIs de referência `Verifição pendente`
- Redução de 70% no consumo de tokens via roteamento híbrido.
- Redução de 85% no tempo inicial de triagem (< 3 segundos).
- 94% de precisão na atribuição correta das especialidades médicas.
