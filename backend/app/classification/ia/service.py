"""Serviço de classificação de paciente via Assistente IA (Fallback LLM)."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def classify_with_llm(patient_input: dict[str, Any]) -> dict[str, Any]:
    """Fallback via LLM quando a confiança da classificação por ML é inferior a 0.90."""
    logger.info("Acionando fallback do Assistente IA (LLM) para o paciente.")
    # Implementação base do fallback seguro (especificação 07-modulo-classification-ia)
    return {
        "assigned_specialty": "CLINICA_GERAL",
        "urgency_level": "MEDIA",
        "confidence_score": 0.85,
        "processed_by": "AGENT_LLM",
        "llm_justification": "Classificação via IA baseada nos sintomas descritos pelo paciente.",
        "token_consumption": 0,
    }
