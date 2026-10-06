"""Script standalone para treinamento offline do pipeline de triagem (ML).

Lê o dataset de dados reais em backend/app/classification/data/triage_training.csv
(ou o arquivo apontado via --data) e gera os artefatos em backend/app/classification/ml/artifacts/:
- severity_scaler.joblib (MinMaxScaler)
- duration_scaler.joblib (StandardScaler)
- symptoms_binarizer.joblib (MultiLabelBinarizer)
- description_vectorizer.joblib (TfidfVectorizer)
- label_encoder.joblib (LabelEncoder)
- model.json (XGBClassifier nativo)
"""

import argparse
import logging
from pathlib import Path
import sys
from typing import Any

import joblib
import pandas as pd
from scipy.sparse import hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import (
    LabelEncoder,
    MinMaxScaler,
    MultiLabelBinarizer,
    StandardScaler,
)
from xgboost import XGBClassifier

# Garante acesso aos pacotes internos da aplicação
CURRENT_FILE = Path(__file__).resolve()
CLASSIFICATION_DIR = CURRENT_FILE.parents[1]
BACKEND_DIR = CLASSIFICATION_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent

for path in [str(PROJECT_ROOT), str(BACKEND_DIR)]:
    if path not in sys.path:
        sys.path.insert(0, path)

from app.triage.constants import PRIMARY_SYMPTOMS  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(message)s",
)
logger = logging.getLogger(__name__)

DEFAULT_DATA_PATH = CLASSIFICATION_DIR / "data" / "triage_training.csv"
DEFAULT_ARTIFACTS_DIR = CURRENT_FILE.parent / "artifacts"
REQUIRED_COLUMNS = [
    "perceived_severity",
    "symptom_duration_hours",
    "primary_symptoms",
    "description",
    "assigned_specialty",
]
MIN_SAMPLES_FOR_EVALUATION = 20

SPECIALTY_MAP = {
    "clínica geral": "CLINICA_GERAL",
    "clinica geral": "CLINICA_GERAL",
    "cardiologia": "CARDIOLOGIA",
    "dermatologia": "DERMATOLOGIA",
    "otorrinolaringologia": "OTORRINOLARINGOLOGIA",
    "pneumologia": "PNEUMOLOGIA",
}

SYMPTOM_REPLACEMENTS = {
    "DOR_DE_CABACA": "DOR_DE_CABECA",
    "CANSACO": "CANSAÇO",
}


def _derive_urgency(severity: float) -> str:
    """Deriva o nível de urgência a partir da severidade percebida quando não explicitado."""
    if severity <= 3:
        return "BAIXA"
    if severity <= 6:
        return "MEDIA"
    if severity <= 8:
        return "ALTA"
    return "EMERGENCIA"


def load_dataset(data_path: str | Path | None = None) -> pd.DataFrame:
    """Carrega e higieniza dataset de treino a partir de arquivo CSV."""
    target_path = Path(data_path).resolve() if data_path else DEFAULT_DATA_PATH.resolve()

    if not target_path.exists():
        raise FileNotFoundError(f"Arquivo de dados de treino não encontrado: {target_path}")

    logger.info("Carregando dataset de dados a partir de %s", target_path)
    df = pd.read_csv(target_path)

    missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_cols:
        raise ValueError(
            f"Dataset inválido. Colunas obrigatórias ausentes: {', '.join(missing_cols)}"
        )

    # Normalização de severidade e duração
    df["perceived_severity"] = pd.to_numeric(df["perceived_severity"], errors="coerce").fillna(5.0)
    df["symptom_duration_hours"] = pd.to_numeric(df["symptom_duration_hours"], errors="coerce").fillna(24.0)
    df["description"] = df["description"].fillna("").astype(str)

    # Normalização de especialidade
    def _normalize_specialty(spec: Any) -> str:
        s = str(spec).strip().lower()
        return SPECIALTY_MAP.get(s, str(spec).strip().upper().replace(" ", "_"))

    df["assigned_specialty"] = df["assigned_specialty"].apply(_normalize_specialty)

    # Deriva urgency_level caso a coluna não exista no CSV
    if "urgency_level" not in df.columns:
        logger.info("Coluna 'urgency_level' não encontrada no CSV. Derivando conforme severidade percebida.")
        df["urgency_level"] = df["perceived_severity"].apply(_derive_urgency)
    else:
        df["urgency_level"] = df["urgency_level"].fillna("MEDIA").astype(str).str.strip().str.upper()

    # Normalização de sintomas primários para lista de strings padronizadas
    def _normalize_symptoms(symptoms: Any) -> list[str]:
        if isinstance(symptoms, list):
            raw_list = [str(s).strip() for s in symptoms]
        elif isinstance(symptoms, str):
            delimiter = "|" if "|" in symptoms else ","
            raw_list = [s.strip() for s in symptoms.split(delimiter) if s.strip()]
        else:
            raw_list = []
        return [SYMPTOM_REPLACEMENTS.get(item, item) for item in raw_list]

    df["primary_symptoms"] = df["primary_symptoms"].apply(_normalize_symptoms)

    logger.info("Dataset carregado com sucesso contendo %d registros.", len(df))
    return df


def _transform_features(
    df: pd.DataFrame,
    severity_scaler: MinMaxScaler,
    duration_scaler: StandardScaler,
    symptoms_binarizer: MultiLabelBinarizer,
    description_vectorizer: TfidfVectorizer,
) -> Any:
    """Aplica as transformações de feature engineering gerando a matriz X_final esparsa."""
    severity_features = severity_scaler.transform(df[["perceived_severity"]].values.astype(float))
    duration_features = duration_scaler.transform(df[["symptom_duration_hours"]].values.astype(float))
    symptoms_features = symptoms_binarizer.transform(df["primary_symptoms"].tolist())
    description_features = description_vectorizer.transform(df["description"].tolist())

    return hstack([
        severity_features,
        duration_features,
        symptoms_features,
        description_features,
    ]).tocsr()


def fit_pipeline(
    df: pd.DataFrame,
    primary_symptoms: list[str] = PRIMARY_SYMPTOMS,
    random_state: int = 42,
) -> dict[str, Any]:
    """Ajusta o pipeline completo de Feature Engineering e treina o XGBClassifier."""
    logger.info("Ajustando scalers, binarizer e vectorizer no dataset...")
    severity_scaler = MinMaxScaler()
    severity_features = severity_scaler.fit_transform(df[["perceived_severity"]].values.astype(float))

    duration_scaler = StandardScaler()
    duration_features = duration_scaler.fit_transform(df[["symptom_duration_hours"]].values.astype(float))

    symptoms_binarizer = MultiLabelBinarizer(classes=primary_symptoms)
    symptoms_features = symptoms_binarizer.fit_transform(df["primary_symptoms"].tolist())

    description_vectorizer = TfidfVectorizer()
    description_features = description_vectorizer.fit_transform(df["description"].tolist())

    x_final = hstack([
        severity_features,
        duration_features,
        symptoms_features,
        description_features,
    ]).tocsr()

    target_combined = df["assigned_specialty"].astype(str) + "|" + df["urgency_level"].astype(str)
    label_encoder = LabelEncoder()
    y_final = label_encoder.fit_transform(target_combined)

    num_classes = len(label_encoder.classes_)
    logger.info("Treinando XGBClassifier com %d classes e random_state=%d...", num_classes, random_state)

    model = XGBClassifier(
        objective="multi:softprob",
        num_class=num_classes,
        random_state=random_state,
        eval_metric="mlogloss",
    )
    model.fit(x_final, y_final)

    return {
        "severity_scaler": severity_scaler,
        "duration_scaler": duration_scaler,
        "symptoms_binarizer": symptoms_binarizer,
        "description_vectorizer": description_vectorizer,
        "label_encoder": label_encoder,
        "model": model,
        "X_final": x_final,
        "y_final": y_final,
    }


def evaluate(
    df: pd.DataFrame,
    primary_symptoms: list[str] = PRIMARY_SYMPTOMS,
    random_state: int = 42,
) -> float | None:
    """Executa split treino/teste e loga accuracy se o dataset for grande o suficiente."""
    sample_count = len(df)
    if sample_count < MIN_SAMPLES_FOR_EVALUATION:
        logger.warning(
            "Dataset pequeno demais (%d amostras < mínimo de %d). "
            "Pulando split treino/teste e avaliação para evitar distorção estatística.",
            sample_count,
            MIN_SAMPLES_FOR_EVALUATION,
        )
        return None

    logger.info("Executando split treino/teste (80%% treino / 20%% teste)...")
    target_combined = df["assigned_specialty"].astype(str) + "|" + df["urgency_level"].astype(str)

    class_counts = target_combined.value_counts()
    can_stratify = (class_counts >= 2).all()
    stratify = target_combined if can_stratify else None

    train_df, test_df = train_test_split(
        df,
        test_size=0.2,
        random_state=random_state,
        stratify=stratify,
    )

    artifacts = fit_pipeline(train_df, primary_symptoms=primary_symptoms, random_state=random_state)

    x_test = _transform_features(
        test_df,
        severity_scaler=artifacts["severity_scaler"],
        duration_scaler=artifacts["duration_scaler"],
        symptoms_binarizer=artifacts["symptoms_binarizer"],
        description_vectorizer=artifacts["description_vectorizer"],
    )

    y_test_combined = test_df["assigned_specialty"].astype(str) + "|" + test_df["urgency_level"].astype(str)
    label_encoder: LabelEncoder = artifacts["label_encoder"]

    known_classes = set(label_encoder.classes_)
    valid_mask = y_test_combined.isin(known_classes)
    if not valid_mask.all():
        logger.warning("Algumas classes no teste não estavam presentes no conjunto de treino e serão desconsideradas.")
        test_df = test_df[valid_mask]
        x_test = x_test[valid_mask.values]
        y_test_combined = y_test_combined[valid_mask]

    y_test = label_encoder.transform(y_test_combined)
    y_pred = artifacts["model"].predict(x_test)

    accuracy = float(accuracy_score(y_test, y_pred))
    logger.info(
        "Resultado da avaliação — Accuracy no conjunto de teste: %.4f (%.2f%%)",
        accuracy,
        accuracy * 100,
    )
    return accuracy


def export_artifacts(artifacts: dict[str, Any], output_dir: Path | str) -> None:
    """Exporta os artefatos de pré-processamento e o modelo treinado em formato nativo."""
    out_path = Path(output_dir).resolve()
    out_path.mkdir(parents=True, exist_ok=True)
    logger.info("Salvando artefatos em %s", out_path)

    joblib.dump(artifacts["severity_scaler"], out_path / "severity_scaler.joblib")
    joblib.dump(artifacts["duration_scaler"], out_path / "duration_scaler.joblib")
    joblib.dump(artifacts["symptoms_binarizer"], out_path / "symptoms_binarizer.joblib")
    joblib.dump(artifacts["description_vectorizer"], out_path / "description_vectorizer.joblib")
    joblib.dump(artifacts["label_encoder"], out_path / "label_encoder.joblib")

    model_json_path = out_path / "model.json"
    artifacts["model"].save_model(str(model_json_path))

    logger.info("Artefatos exportados com sucesso em %s:", out_path)
    logger.info(" - severity_scaler.joblib")
    logger.info(" - duration_scaler.joblib")
    logger.info(" - symptoms_binarizer.joblib")
    logger.info(" - description_vectorizer.joblib")
    logger.info(" - label_encoder.joblib")
    logger.info(" - model.json")


def main(argv: list[str] | None = None) -> None:
    """Ponto de entrada do script CLI de treinamento offline."""
    parser = argparse.ArgumentParser(
        description="Treinamento offline do modelo de triagem clínica (XGBoost + scikit-learn)."
    )
    parser.add_argument(
        "--data",
        type=str,
        default=str(DEFAULT_DATA_PATH),
        help=f"Caminho do arquivo CSV de treino. Padrão: {DEFAULT_DATA_PATH}",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(DEFAULT_ARTIFACTS_DIR),
        help=f"Diretório para salvar os artefatos gerados. Padrão: {DEFAULT_ARTIFACTS_DIR}",
    )
    parser.add_argument(
        "--random-state",
        type=int,
        default=42,
        help="Semente para reprodutibilidade aleatória (default: 42).",
    )

    args = parser.parse_args(argv)

    logger.info("=== Início do Processo de Treinamento Offline de ML ===")
    df = load_dataset(args.data)

    evaluate(df, primary_symptoms=PRIMARY_SYMPTOMS, random_state=args.random_state)

    logger.info("Treinando pipeline final nos dados completos...")
    artifacts = fit_pipeline(df, primary_symptoms=PRIMARY_SYMPTOMS, random_state=args.random_state)

    export_artifacts(artifacts, output_dir=args.output_dir)
    logger.info("=== Treinamento e Exportação Concluídos com Sucesso ===")


if __name__ == "__main__":
    main()
