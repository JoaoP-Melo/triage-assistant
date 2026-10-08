"""Script de teste e validação da inferência via Machine Learning (XGBoost).

Carrega os artefatos gerados pelo treinamento em backend/app/classification/ml/artifacts/
e executa a predição para um caso clínico de exemplo, exibindo os detalhes no terminal.

Pode ser executado diretamente:
    python backend/app/classification/ml/test_predict.py
ou via pytest:
    pytest backend/app/classification/ml/test_predict.py
"""

from pathlib import Path
import sys
from typing import Any

# Garante a resolução correta dos imports do backend independentemente do diretório de execução
CURRENT_FILE = Path(__file__).resolve()
ML_DIR = CURRENT_FILE.parent
CLASSIFICATION_DIR = ML_DIR.parent
BACKEND_DIR = CLASSIFICATION_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent

for path in [str(PROJECT_ROOT), str(BACKEND_DIR)]:
    if path not in sys.path:
        sys.path.insert(0, path)

from app.classification.ml.service import (  # noqa: E402
    get_ml_artifacts,
    predict_triage_ml,
)


def run_prediction_test(sample: dict[str, Any] | None = None) -> dict[str, Any]:
    """Carrega os artefatos de ML, executa a predição para o caso de teste e imprime os resultados."""
    if sample is None:
        sample = {
            "perceived_severity": 8.0,
            "symptom_duration_hours": 3.0,
            "primary_symptoms": ["DOR_NO_PEITO", "FALTA_DE_AR"],
            "description": "Paciente relata dor intensa no peito com irradiação e falta de ar iniciada há 3 horas.",
        }

    print("=" * 60)
    print("      TESTE DE INFERENCIA DO MODELO DE TRIAGEM (ML)       ")
    print("=" * 60)

    # 1. Carregamento dos artefatos
    print("\n[1/3] Carregando artefatos de ML...")
    artifacts = get_ml_artifacts()
    classes = artifacts["label_encoder"].classes_

    print(" Artefatos carregados com sucesso!")
    print(f" - Quantidade de classes mapeadas: {len(classes)}")
    print(f" - Classes disponiveis: {', '.join(classes[:5])}... (+ {len(classes) - 5} outras)")

    # 2. Dados de entrada do paciente
    print("\n[2/3] Dados do caso clinico de teste:")
    print(f" - Severidade percebida (0-10): {sample['perceived_severity']}")
    print(f" - Duracao dos sintomas: {sample['symptom_duration_hours']} horas")
    print(f" - Sintomas primarios: {', '.join(sample['primary_symptoms'])}")
    print(f" - Descricao: \"{sample['description']}\"")

    # 3. Execução da predição
    print("\n[3/3] Executando predicao...")
    result = predict_triage_ml(sample)

    print("\n" + "-" * 60)
    print(" RESULTADO DA PREDICAO:")
    print("-" * 60)
    print(f" * Especialidade Recomendada : {result['assigned_specialty']}")
    print(f" * Nivel de Urgencia         : {result['urgency_level']}")
    print(f" * Grau de Confianca         : {result['confidence_score']:.2%}")
    print(f" * Processado por            : {result['processed_by']}")
    print("-" * 60)

    return result


def test_ml_prediction() -> None:
    """Função de teste compatível com o executor pytest."""
    sample = {
        "perceived_severity": 7.0,
        "symptom_duration_hours": 12.0,
        "primary_symptoms": ["FEBRE_ALTA", "DOR_DE_CABECA"],
        "description": "Febre alta contínua com dor de cabeça forte.",
    }
    result = run_prediction_test(sample)

    assert isinstance(result, dict)
    assert "assigned_specialty" in result
    assert "urgency_level" in result
    assert "confidence_score" in result
    assert 0.0 <= result["confidence_score"] <= 1.0
    assert result["processed_by"] == "ML_XGBOOST"


if __name__ == "__main__":
    run_prediction_test()
