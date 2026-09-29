from typing import Any


def predict_triage(patient_input: dict[str, Any]) -> dict[str, Any]:
    """Stub temporário para predição de triagem via ML.

    # TODO: substituir por inferência real do modelo treinado (XGBoost).
    # Quando o modelo estiver treinado, caso o confidence_score seja inferior a 0.90,
    # esta função acionará internamente classify_with_llm de modules.assistente_ia.service.
    """
    return {
        "assigned_specialty": "CLINICA_GERAL",
        "urgency_level": "MEDIA",
        "confidence_score": 0.0,
        "processed_by": "ML_XGBOOST",  # ou "AGENT_LLM" no fallback futuro
    }
