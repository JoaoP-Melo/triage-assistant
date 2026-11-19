# 06 — Módulo de Classificação de Triagem (ML + IA)

> Especificação unificada dos módulos de classificação por Machine Learning e por IA generativa. Este é um fluxo **interno** acionado pelo módulo `triage` durante a submissão de sintomas do paciente. Não possui frontend próprio e não deve ser exposto diretamente ao usuário final. O módulo `triage` é responsável por persistir o ticket final no MongoDB.

## 1. Objetivo e responsabilidade

O módulo recebe os dados brutos informados pelo paciente e determina:

- `assigned_specialty`: especialidade para a qual a triagem será encaminhada.
- `urgency_level`: nível de urgência (`BAIXA`, `MEDIA`, `ALTA` ou `EMERGENCIA`).
- `confidence_score`: confiança da classificação, quando fornecida pelo modelo de ML.
- `processed_by`: identifica se a classificação foi concluída pelo ML (`ML_XGBOOST`) ou pelo agente de IA (`AGENT_LLM`).
- `llm_justification`: justificativa retornada pela LLM, quando aplicável.
- `token_consumption`: consumo de tokens da LLM, para auditoria de custo/logs.

O fluxo utiliza o modelo de ML como primeira etapa. A IA generativa é acionada como fallback quando a confiança máxima do ML fica abaixo do limiar definido de 90%.

### Limites de responsabilidade

| Componente | Responsabilidade |
|---|---|
| `triage` | Receber a submissão autenticada do paciente, chamar o fluxo de classificação e persistir o ticket final no MongoDB |
| `ml` | Preparar os dados, executar a inferência do modelo e decidir se aceita o resultado ou aciona o fallback de IA |
| `assistant` | Classificar os dados brutos com a LLM quando acionado pelo módulo `ml`; validar a resposta e tratar falhas do provedor |

Os módulos `ml` e `assistant` não persistem o ticket final e não acessam diretamente PostgreSQL ou MongoDB para essa finalidade. O módulo `assistant` registra o consumo de tokens para auditoria/logs, conforme especificado abaixo.

## 2. Fluxo completo de classificação

1. O paciente envia o formulário pela rota `POST /triage/submit`.
2. O módulo `triage` recebe os dados validados e chama o fluxo interno de classificação.
3. O módulo `ml` recebe os dados brutos do formulário.
4. O módulo `ml` aplica o pipeline de Feature Engineering usando os artefatos pré-treinados.
5. O modelo executa `model.predict_proba(X_final)`.
6. O módulo `ml` obtém a maior probabilidade e aplica o limiar de confiança de **90%**:
   - **Confiança maior ou igual a 90%:** aceita a classificação do ML e retorna o resultado sem chamar a IA.
   - **Confiança abaixo de 90%:** chama internamente `POST /assistant/classify`, repassando exclusivamente os dados brutos do formulário.
7. Se acionado, o módulo `assistant` solicita à LLM uma classificação estruturada, valida a resposta e retorna o resultado ao módulo `ml`.
8. O módulo `ml` devolve o resultado final ao módulo `triage`.
9. O módulo `triage` monta o documento do ticket, define o status inicial `WAITING` e persiste o registro na coleção `tickets` do MongoDB.

<CodeBlock language="mermaid" editable>
flowchart TD
    A["Paciente envia sintomas"] --> B["POST /triage/submit"]
    B --> C["Módulo triage"]
    C --> D["Módulo ML: feature engineering"]
    D --> E["model.predict_proba"]
    E --> F{"Maior probabilidade >= 90%?"}
    F -->|Sim| G["Aceita classificação ML"]
    F -->|Não| H["POST /assistant/classify"]
    H --> I["LLM: classificação estruturada"]
    I --> J["Validação Pydantic"]
    J --> K["Resultado da IA"]
    G --> L["Resultado final da classificação"]
    K --> L
    L --> M["Módulo triage persiste ticket"]
    M --> N["MongoDB: status WAITING"]
</CodeBlock>

## 3. Dados de entrada compartilhados

Os dois módulos recebem os dados brutos do formulário de triagem:

| Campo | Descrição / uso |
|---|---|
| `perceived_severity` | Gravidade percebida pelo paciente; o schema da submissão documenta escala de 1 a 10 |
| `symptom_duration_hours` | Duração dos sintomas em horas |
| `primary_symptoms` | Lista de sintomas selecionados pelo paciente |
| `description` | Descrição textual livre dos sintomas |

**Regra importante:** ao acionar o fallback, o módulo `ml` deve repassar os dados brutos originais do formulário. Não deve enviar à IA os vetores transformados, a matriz `X_final` ou features derivadas do pipeline de ML.

A lista de sintomas e as regras completas de validação do payload pertencem ao contrato do módulo `triage`; não redefinir esses contratos neste módulo.

## 4. Módulo ML

### 4.1 Função interna — `Predict ML`

- **Finalidade:** executar a classificação inicial por Machine Learning e decidir se o resultado tem confiança suficiente ou se deve ser usado o fallback de IA.
- **Autenticação:** Token JWT de serviço para chamadas internas. A rota não deve ser chamada diretamente pelo navegador do paciente.
- **Dependências:** artefatos de ML pré-carregados em memória.

### 4.2 Pipeline de Feature Engineering

O módulo aplica os artefatos pré-treinados nesta ordem lógica:

| Campo de entrada | Transformação |
|---|---|
| `perceived_severity` | `MinMaxScaler` — normalização |
| `symptom_duration_hours` | `StandardScaler` — padronização |
| `primary_symptoms` | `MultiLabelBinarizer` — binarização multilabel |
| `description` | `TfidfVectorizer` — vetorização textual |

As features transformadas devem ser concatenadas em uma única matriz `X_final`, utilizada na inferência:

```python
model.predict_proba(X_final)
```

### 4.3 Regra de decisão

O limiar de confiança é **90% (0.90)**, aplicado à maior probabilidade retornada pelo modelo.

- `max_probability >= 0.90`: concluir a classificação com a especialidade e a urgência previstas pelo ML.
- `max_probability < 0.90`: acionar internamente `POST /assistant/classify`, enviando os dados brutos do formulário.

Não arredondar a probabilidade antes de aplicar o limiar de decisão.

### 4.4 Retorno do módulo ML

O resultado disponibilizado ao chamador deve conter:

- `assigned_specialty`
- `urgency_level`
- `confidence_score`
- `processed_by`: `ML_XGBOOST` ou `AGENT_LLM`
- justificativa, quando a classificação tiver vindo da LLM
- `token_consumption`, quando aplicável ao resultado do fallback

A especificação original não define o schema Pydantic completo nem os tipos de todos os campos de resposta. Não inventar esses contratos: consultar os schemas efetivamente implementados antes de alterá-los.

### 4.5 Ciclo de vida dos artefatos

- Carregar scalers, binarizer, vectorizer e modelo uma única vez durante a inicialização da aplicação (por exemplo, no evento `startup` do FastAPI).
- Reutilizar os artefatos carregados em memória nas requisições.
- Não recarregar os arquivos de modelo a cada chamada de `POST /ml/predict`.

### 4.6 Persistência e acesso a bancos

- O módulo ML não acessa MongoDB nem PostgreSQL diretamente.
- Recebe dados, processa e retorna a classificação.
- A persistência do ticket pertence ao módulo `triage`.

## 5. Módulo de IA generativa (fallback)

### 5.1 Função interna — `Predict IA`

- **Finalidade:** classificar os sintomas quando o modelo ML retorna confiança abaixo de 90%.
- **Dependências:** cliente do provedor de LLM (Gemini/OpenAI) e gerenciador de resiliência/retry.
- **Chamada:** feita internamente pelo módulo `ml`, não diretamente pelo frontend.

### 5.2 Recepção e preparação dos dados

A rota recebe o contexto bruto completo:

- `perceived_severity`
- `symptom_duration_hours`
- `primary_symptoms`
- `description`

O serviço constrói um system prompt que instrui a LLM a atuar como médico triador, avaliar os sintomas e determinar a especialidade e a urgência. As variáveis do paciente são incluídas como contexto da classificação.

### 5.3 Resposta estruturada

- A chamada ao provedor deve exigir resposta estruturada estrita conforme o schema Pydantic `LLMClassificationSchema`.
- Validar rigorosamente o JSON retornado pela LLM antes de repassar o resultado.
- Nunca confiar ou repassar texto bruto da LLM sem validação pelo schema.
- Registrar a quantidade de tokens consumidos para auditoria de custo/logs.

### 5.4 Resiliência e fallback em caso de falha do provedor

Falhas de comunicação com o provedor, incluindo timeout ou rate limit, devem acionar até **3 retentativas automáticas**.

Se todas as tentativas falharem, retornar uma classificação segura para que o ticket do paciente não seja perdido:

```json
{
  "assigned_specialty": "CLINICA_GERAL",
  "urgency_level": "MEDIA"
}
```

O registro de `token_consumption` é obrigatório também quando ocorrer fallback por erro, caso alguma chamada parcial tenha consumido tokens.

**Distinção importante entre os dois fallbacks:**
- **Fallback por baixa confiança do ML:** é o fluxo normal de encaminhamento para a rota `/assistant/classify`.
- **Fallback por falha da LLM:** é a classificação segura `CLINICA_GERAL` + `MEDIA`, usada somente se o provedor continuar falhando após as retentativas.

A especificação de origem não define um valor de `confidence_score`, `llm_justification` ou `processed_by` específico para o caso de falha definitiva do provedor. Não presumir esses valores; verificar o contrato implementado antes de modificar o comportamento.

### 5.5 Persistência e acesso a bancos

- O módulo assistant não persiste o ticket final.
- Retorna a classificação ao módulo ML.
- O módulo ML retorna o resultado ao módulo `triage`.
- O módulo `triage` é responsável pela persistência do ticket.
- O registro de consumo de tokens para auditoria/logs deve ser mantido conforme a implementação do projeto; a especificação original menciona MongoDB para esse registro, embora o ticket final seja persistido pelo módulo `triage`.

## 6. Contrato de integração entre os módulos

| Origem | Destino | Dados / operação |
|---|---|---|
| `triage` | `ml` | Dados brutos do formulário de sintomas |
| `ml` | `assistant` | Dados brutos originais, somente se a maior probabilidade do ML for inferior a 90% |
| `assistant` | `ml` | Classificação validada pelo `LLMClassificationSchema`, justificativa e consumo de tokens, conforme retorno disponível |
| `ml` | `triage` | Resultado final da classificação |
| `triage` | MongoDB | Persiste o ticket com `triage_result` e status inicial `WAITING` |

### Estrutura conceitual do resultado persistido

O módulo `triage` utiliza o resultado da classificação para preencher `triage_result`. A estrutura documentada para o ticket inclui:

```json
{
  "triage_result": {
    "assigned_specialty": "CLINICA_GERAL",
    "urgency_level": "ALTA",
    "confidence_score": 0.94,
    "processed_by": "ML_XGBOOST",
    "llm_justification": null,
    "token_consumption": 0
  },
  "status": "WAITING"
}
```

Os valores acima são ilustrativos. O resultado real deve refletir a classificação retornada pelo fluxo ML/IA. Campos não fornecidos em determinado caminho de execução não devem ser inventados; seguir os schemas e modelos efetivamente definidos no código.

## 7. Regras de segurança e implementação

- As rotas `/ml/predict` e `/assistant/classify` são internas e protegidas por autenticação de serviço/JWT interno.
- Não expor essas rotas como funcionalidades diretamente acessíveis pelo frontend.
- O módulo `triage` deve continuar sendo o ponto de entrada da submissão do paciente e o responsável pela persistência.
- Não confiar em texto livre retornado pela LLM: validar a resposta com `LLMClassificationSchema`.
- Encaminhar ao fallback somente os dados brutos necessários à classificação.
- Não permitir que os módulos ML/assistant passem a persistir ou modificar diretamente o ticket final.
- Manter o carregamento dos artefatos ML fora do ciclo de requisição.
- Preservar o limite de confiança de 90% como regra de roteamento, salvo alteração explícita do requisito.

## 8. Fora do escopo deste módulo

- Formulário de triagem e autenticação do paciente — pertencem ao módulo `triage`/`auth`.
- Persistência do ticket final — pertence ao módulo `triage`.
- Kanban, fila e gerenciamento de atendimentos pelo médico — pertencem aos módulos de triagem/dashboard médico.
- Frontend próprio para ML ou IA — não existe neste desenho.
- Definição de novos níveis de urgência, especialidades ou contratos de API não descritos aqui — não inferir sem consultar o código e os schemas atuais.

## 9. Orientações para o agente de IA codificador

Antes de implementar ou alterar este fluxo:

1. Identificar os routers, services, schemas Pydantic e dependências reais dos módulos `triage`, `ml` e `assistant`.
2. Conferir os nomes e tipos exatos dos campos dos schemas implementados, especialmente `TriageSubmitRequest`, `LLMClassificationSchema` e o retorno da classificação.
3. Preservar a separação de responsabilidades: `triage` orquestra a submissão e persiste; `ml` classifica e decide o fallback; `assistant` executa a classificação via LLM.
4. Garantir testes para os dois caminhos do ML: confiança `>= 0.90` e confiança `< 0.90`.
5. Garantir testes para resposta LLM válida, resposta estruturada inválida, timeout/rate limit, retentativas e fallback seguro após falha definitiva.
6. Verificar que o ticket continua sendo persistido pelo módulo `triage` mesmo quando a LLM falha.
7. Não inventar campos, comportamentos ou rotas ausentes nesta especificação. Quando houver divergência entre este documento e o código atual, apontar a divergência antes de fazer mudanças que alterem contratos.

