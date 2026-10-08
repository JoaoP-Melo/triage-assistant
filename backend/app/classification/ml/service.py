"""Serviço de predição de triagem via Machine Learning (XGBoost)."""

import logging
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from scipy.sparse import hstack
from xgboost import XGBClassifier

from app.classification.ia.service import classify_with_llm

logger = logging.getLogger(__name__)

ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"

__all__ = ["get_ml_artifacts", "predict_triage_ml", "classify_with_llm"]

# Cache em memória para carregar os artefatos apenas uma vez
_ML_ARTIFACTS: dict[str, Any] | None = None


def get_ml_artifacts() -> dict[str, Any]:
    """Carrega os artefatos pré-treinados do disco e armazena em memória."""
    global _ML_ARTIFACTS
    if _ML_ARTIFACTS is not None:
        return _ML_ARTIFACTS

    severity_scaler_path = ARTIFACTS_DIR / "severity_scaler.joblib"
    duration_scaler_path = ARTIFACTS_DIR / "duration_scaler.joblib"
    symptoms_binarizer_path = ARTIFACTS_DIR / "symptoms_binarizer.joblib"
    description_vectorizer_path = ARTIFACTS_DIR / "description_vectorizer.joblib"
    label_encoder_path = ARTIFACTS_DIR / "label_encoder.joblib"
    model_json_path = ARTIFACTS_DIR / "model.json"

    for path in [
        severity_scaler_path,
        duration_scaler_path,
        symptoms_binarizer_path,
        description_vectorizer_path,
        label_encoder_path,
        model_json_path,
    ]:
        if not path.exists():
            raise FileNotFoundError(
                f"Artefato de ML não encontrado em {path}. Execute o script train.py primeiro."
            )

    logger.info("Carregando artefatos de ML a partir de %s", ARTIFACTS_DIR)
    severity_scaler = joblib.load(severity_scaler_path)
    duration_scaler = joblib.load(duration_scaler_path)
    symptoms_binarizer = joblib.load(symptoms_binarizer_path)
    description_vectorizer = joblib.load(description_vectorizer_path)
    label_encoder = joblib.load(label_encoder_path)

    model = XGBClassifier()
    model.load_model(str(model_json_path))

    _ML_ARTIFACTS = {
        "severity_scaler": severity_scaler,
        "duration_scaler": duration_scaler,
        "symptoms_binarizer": symptoms_binarizer,
        "description_vectorizer": description_vectorizer,
        "label_encoder": label_encoder,
        "model": model,
    }
    return _ML_ARTIFACTS


def predict_triage_ml(patient_input: dict[str, Any]) -> dict[str, Any]:
    """Executa a inferência de Machine Learning nos dados submetidos pelo paciente."""
    artifacts = get_ml_artifacts()

    perceived_severity = float(patient_input.get("perceived_severity", 5.0))
    symptom_duration_hours = float(patient_input.get("symptom_duration_hours", 24.0))
    primary_symptoms = patient_input.get("primary_symptoms", [])
    description = str(patient_input.get("description", ""))

    severity_feat = artifacts["severity_scaler"].transform([[perceived_severity]])
    duration_feat = artifacts["duration_scaler"].transform([[symptom_duration_hours]])
    symptoms_feat = artifacts["symptoms_binarizer"].transform([primary_symptoms])
    description_feat = artifacts["description_vectorizer"].transform([description])

    x_final = hstack([severity_feat, duration_feat, symptoms_feat, description_feat]).tocsr()

    probabilities = artifacts["model"].predict_proba(x_final)[0]
    best_idx = int(np.argmax(probabilities))
    confidence_score = float(probabilities[best_idx])

    combined_label: str = artifacts["label_encoder"].inverse_transform([best_idx])[0]
    if "|" in combined_label:
        assigned_specialty, urgency_level = combined_label.split("|", 1)
    else:
        assigned_specialty, urgency_level = combined_label, "MEDIA"

    return {
        "assigned_specialty": assigned_specialty,
        "urgency_level": urgency_level,
        "confidence_score": confidence_score,
        "processed_by": "ML_XGBOOST",
        "llm_justification": None,
        "token_consumption": 0,
    }
