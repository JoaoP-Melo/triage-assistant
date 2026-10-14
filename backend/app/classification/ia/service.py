"""Serviço de classificação de paciente via Assistente IA (Groq / OpenAI API).

Implementa o fallback inteligente e classificação clínica assistida por IA
quando a confiança do modelo de Machine Learning for inferior a 0.90,
ou em cenários de alta complexidade/ambiguidade clínica.
"""

import json
import logging
import os
import time
from typing import Any

from dotenv import load_dotenv
from openai import APIConnectionError, APIError, OpenAI, RateLimitError
from pydantic import BaseModel, Field, ValidationError

load_dotenv()

logger = logging.getLogger(__name__)

# Configurações do provedor de IA (Groq via biblioteca OpenAI)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL")
MAX_RETRIES = 3

VALID_SPECIALTIES = {
    "CLINICA_GERAL",
    "CARDIOLOGIA",
    "DERMATOLOGIA",
    "OTORRINOLARINGOLOGIA",
    "PNEUMOLOGIA",
}

VALID_URGENCIES = {
    "BAIXA",
    "MEDIA",
    "ALTA",
    "EMERGENCIA",
}

SPECIALTY_ALIASES = {
    "clinica geral": "CLINICA_GERAL",
    "clínica geral": "CLINICA_GERAL",
    "clinica_geral": "CLINICA_GERAL",
    "clinica": "CLINICA_GERAL",
    "cardiologia": "CARDIOLOGIA",
    "cardio": "CARDIOLOGIA",
    "dermatologia": "DERMATOLOGIA",
    "dermato": "DERMATOLOGIA",
    "otorrinolaringologia": "OTORRINOLARINGOLOGIA",
    "otorrino": "OTORRINOLARINGOLOGIA",
    "pneumologia": "PNEUMOLOGIA",
    "pneumo": "PNEUMOLOGIA",
}

URGENCY_ALIASES = {
    "baixa": "BAIXA",
    "media": "MEDIA",
    "média": "MEDIA",
    "alta": "ALTA",
    "emergencia": "EMERGENCIA",
    "emergência": "EMERGENCIA",
}

CLINICAL_SYSTEM_PROMPT = """Você é um Médico Especialista em Triagem Clínica e Medicina de Urgência/Emergência em um sistema hospitalar inteligente (Protocolo de Acolhimento com Classificação de Risco).

SEU PAPEL:
Avaliar as informações clínicas e queixas relatadas pelo paciente para determinar:
1. A especialidade médica mais indicada para o primeiro atendimento.
2. O nível de prioridade clínica/urgência para atendimento.
3. Um score de confiança diagnóstica na sua avaliação.
4. Uma justificativa médica técnica, concisa e objetiva em português.

DIRETRIZES DE ESPECIALIDADES PERMITIDAS (escolha EXATAMENTE uma das 5 opções):
- CLINICA_GERAL: Sintomas sistêmicos inespecíficos, viroses, febre sem foco grave definido, mal-estar difuso, náuseas, diarreia, dores musculares generalizadas.
- CARDIOLOGIA: Dor no peito/precordial/retroesternal (aperto ou pontada), palpitações, taquicardia, tontura ou desmaio associado a queixa cardiovascular, sudorese fria associada a desconforto torácico.
- DERMATOLOGIA: Queixas cutâneas, prurido (coceira), manchas na pele, erupções, vermelhidão, lesões e inchaços localizados na derme sem comprometimento respiratório.
- OTORRINOLARINGOLOGIA: Dor de garganta, dor de ouvido (otalgia), congestão nasal, coriza, espirros, sinusite, queixas restritas às vias aéreas superiores.
- PNEUMOLOGIA: Falta de ar (dispneia), chiado no peito (sibilância), tosse persistente/produtiva com cansaço respiratório, dor ventilatório-dependente.

DIRETRIZES DE NÍVEL DE URGÊNCIA (escolha EXATAMENTE um dos 4 níveis):
- BAIXA: Sintomas leves, evolução estável há dias (> 48h), sem sinais de piora rápida ou risco à vida (ex: coriza leve, coceira localizada, espirros).
- MEDIA: Desconforto moderado que prejudica atividades diárias, sintomas agudos requerendo avaliação médica no mesmo dia, sem instabilidade hemodinâmica.
- ALTA: Dor intensa (severidade >= 7), febre persistente, sintomas com rápida progressão (< 12h) e potencial risco de complicação se não atendido rapidamente.
- EMERGENCIA: Risco imediato à vida ou falência orgânica iminente (ex: dor torácica aguda em aperto com irradiação, dispneia grave com cianose, choque anafilático, confusão mental súbita).

FORMATO OBRIGATÓRIO DE SAÍDA (retorne EXCLUSIVAMENTE um objeto JSON válido no seguinte formato):
{
  "assigned_specialty": "CLINICA_GERAL | CARDIOLOGIA | DERMATOLOGIA | OTORRINOLARINGOLOGIA | PNEUMOLOGIA",
  "urgency_level": "BAIXA | MEDIA | ALTA | EMERGENCIA",
  "confidence_score": 0.95,
  "llm_justification": "Explicação clínica detalhando o raciocínio médico que sustentou a especialidade e a urgência."
}
"""


class LLMClassificationSchema(BaseModel):
    """Schema Pydantic de validação estrita da resposta da LLM."""

    assigned_specialty: str = Field(..., description="Especialidade médica de encaminhamento")
    urgency_level: str = Field(..., description="Nível de urgência da triagem")
    confidence_score: float = Field(default=0.85, ge=0.0, le=1.0, description="Nível de confiança da IA")
    llm_justification: str = Field(..., min_length=5, description="Justificativa clínica técnica")


def _get_safe_fallback(
    reason: str = "Classificação de contingência via IA baseada nos sintomas descritos pelo paciente.",
    token_consumption: int = 0,
) -> dict[str, Any]:
    """Retorna um resultado seguro de fallback quando a IA estiver inacessível."""
    return {
        "assigned_specialty": "CLINICA_GERAL",
        "urgency_level": "MEDIA",
        "confidence_score": 0.85,
        "processed_by": "AGENT_LLM",
        "llm_justification": reason,
        "token_consumption": token_consumption,
    }


def _normalize_specialty(specialty_raw: str) -> str:
    cleaned = specialty_raw.strip().lower()
    if cleaned in SPECIALTY_ALIASES:
        return SPECIALTY_ALIASES[cleaned]
    upper = specialty_raw.strip().upper().replace(" ", "_")
    if upper in VALID_SPECIALTIES:
        return upper
    return "CLINICA_GERAL"


def _normalize_urgency(urgency_raw: str) -> str:
    cleaned = urgency_raw.strip().lower()
    if cleaned in URGENCY_ALIASES:
        return URGENCY_ALIASES[cleaned]
    upper = urgency_raw.strip().upper()
    if upper in VALID_URGENCIES:
        return upper
    return "MEDIA"


def classify_with_llm(patient_input: dict[str, Any]) -> dict[str, Any]:
    """Classifica a triagem do paciente utilizando o modelo Groq via SDK da OpenAI.

    Executa até 3 tentativas de chamada resiliente com JSON estruturado e
    validação Pydantic. Caso o Groq não esteja configurado ou ocorra falha persistente,
    aciona o fallback seguro sem interromper o fluxo do sistema.
    """
    api_key = os.getenv("GROQ_API_KEY") or GROQ_API_KEY
    if not api_key or not api_key.strip():
        logger.warning(
            "GROQ_API_KEY não foi configurada no arquivo .env. Acionando fallback seguro padrão."
        )
        return _get_safe_fallback(
            reason="Chave GROQ_API_KEY não configurada no ambiente. Classificação direcionada para Clínica Geral (prioridade Média)."
        )

    model = os.getenv("GROQ_MODEL") or GROQ_MODEL

    client = OpenAI(
        api_key=api_key.strip(),
        timeout=15.0,
    )

    perceived_severity = patient_input.get("perceived_severity", 5)
    duration_hours = patient_input.get("symptom_duration_hours", 24)
    primary_symptoms = patient_input.get("primary_symptoms", [])
    description = patient_input.get("description", "")

    user_prompt = (
        f"Dados clínicos do paciente para triagem:\n"
        f"- Severidade percebida (1 a 10): {perceived_severity}\n"
        f"- Duração dos sintomas em horas: {duration_hours}\n"
        f"- Sintomas primários informados: {', '.join(primary_symptoms) if primary_symptoms else 'Nenhum'}\n"
        f"- Relato e descrição do paciente: \"{description}\"\n\n"
        f"Analise o quadro clínico e retorne a classificação em formato JSON estrito."
    )

    messages = [
        {"role": "system", "content": CLINICAL_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    total_tokens_consumed = 0

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(
                "Chamando modelo Groq (%s) via OpenAI SDK - tentativa %d/%d.",
                model,
                attempt,
                MAX_RETRIES,
            )

            response = client.chat.completions.create(
                model=model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=600,
            )

            if response.usage:
                total_tokens_consumed += response.usage.total_tokens

            content = response.choices[0].message.content or ""
            parsed_json = json.loads(content)

            # Valida e normaliza a saída da LLM via Pydantic
            validated = LLMClassificationSchema(**parsed_json)

            assigned_specialty = _normalize_specialty(validated.assigned_specialty)
            urgency_level = _normalize_urgency(validated.urgency_level)

            logger.info(
                "Classificação via Groq concluída com sucesso: especialidade=%s, urgência=%s, tokens=%d",
                assigned_specialty,
                urgency_level,
                total_tokens_consumed,
            )

            return {
                "assigned_specialty": assigned_specialty,
                "urgency_level": urgency_level,
                "confidence_score": round(float(validated.confidence_score), 2),
                "processed_by": "AGENT_LLM",
                "llm_justification": validated.llm_justification.strip(),
                "token_consumption": total_tokens_consumed,
            }

        except (RateLimitError, APIConnectionError) as net_err:
            logger.warning(
                "Erro de rede/rate-limit ao comunicar com Groq na tentativa %d/%d: %s",
                attempt,
                MAX_RETRIES,
                net_err,
            )
            if attempt < MAX_RETRIES:
                time.sleep(1.0 * attempt)
            else:
                return _get_safe_fallback(
                    reason=f"Falha de comunicação após {MAX_RETRIES} tentativas com o provedor Groq.",
                    token_consumption=total_tokens_consumed,
                )

        except (ValidationError, json.JSONDecodeError) as val_err:
            logger.warning(
                "Erro de validação do JSON da LLM na tentativa %d/%d: %s",
                attempt,
                MAX_RETRIES,
                val_err,
            )
            if attempt < MAX_RETRIES:
                time.sleep(0.5)
            else:
                return _get_safe_fallback(
                    reason="Resposta da IA em formato inválido; aplicado fallback seguro.",
                    token_consumption=total_tokens_consumed,
                )

        except APIError as api_err:
            logger.error("Erro na API da Groq/OpenAI: %s", api_err)
            return _get_safe_fallback(
                reason=f"Erro retornado pela API do provedor de IA: {api_err}",
                token_consumption=total_tokens_consumed,
            )

        except Exception as exc:
            logger.exception("Exceção inesperada durante a chamada de IA: %s", exc)
            return _get_safe_fallback(
                reason="Erro interno inesperado durante processamento com IA.",
                token_consumption=total_tokens_consumed,
            )

    return _get_safe_fallback(token_consumption=total_tokens_consumed)
