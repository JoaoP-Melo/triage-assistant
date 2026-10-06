"""Ponto central de classificação clínica (orquestração híbrida ML + IA).

Roteamento:
1. Executa o pipeline de Feature Engineering e o modelo XGBoost (app.classification.ml).
2. Se confidence_score >= 0.90: finaliza com a predição de ML.
3. Se confidence_score < 0.90: aciona o fallback via LLM (app.classification.ia).
"""

import logging
from typing import Any

from app.classification.ia.service import classify_with_llm
from app.classification.ml.service import predict_triage_ml
from app.triage.constants import PRIMARY_SYMPTOMS

logger = logging.getLogger(__name__)

__all__ = ["PRIMARY_SYMPTOMS", "predict_triage"]


def predict_triage(patient_input: dict[str, Any]) -> dict[str, Any]:
    """Orquestra a predição de especialidade e urgência da triagem do paciente."""
    try:
        ml_result = predict_triage_ml(patient_input)
        confidence = ml_result.get("confidence_score", 0.0)

        # Critério de corte de 90% (especificação 06-modulo-classification-ml)
        if confidence >= 0.90:
            logger.info("Classificação finalizada via ML com alta confiança: %.2f%%", confidence * 100)
            return ml_result

        logger.info(
            "Confiança do modelo ML (%.2f%%) abaixo de 90%%. Acionando fallback LLM.",
            confidence * 100,
        )
        return classify_with_llm(patient_input)

    except Exception as exc:
        logger.warning(
            "Falha durante a predição via ML (%s). Acionando fallback de resiliência via IA.",
            exc,
        )
        return classify_with_llm(patient_input)
