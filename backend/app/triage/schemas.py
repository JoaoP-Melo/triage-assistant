from datetime import datetime
from pydantic import BaseModel, Field, field_validator

from app.triage.constants import PRIMARY_SYMPTOMS


class TriageSubmitRequest(BaseModel):
    perceived_severity: int = Field(
        ...,
        ge=1,
        le=10,
        description="Severidade percebida de 1 a 10.",
    )
    symptom_duration_hours: float = Field(
        ...,
        gt=0,
        description="Duração dos sintomas em horas (positivo).",
    )
    primary_symptoms: list[str] = Field(
        ...,
        description="Exatamente 3 sintomas primários únicos pertencentes à lista permitida.",
    )
    description: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Descrição detalhada em texto livre.",
    )

    @field_validator("primary_symptoms")
    @classmethod
    def validate_primary_symptoms(cls, symptoms: list[str]) -> list[str]:
        if len(symptoms) != 3:
            raise ValueError("primary_symptoms deve conter exatamente 3 itens.")

        unique_symptoms = set(symptoms)
        if len(unique_symptoms) != 3:
            raise ValueError("primary_symptoms deve conter 3 sintomas únicos.")

        invalid = [s for s in symptoms if s not in PRIMARY_SYMPTOMS]
        if invalid:
            raise ValueError(
                f"Sintoma(s) inválido(s): {', '.join(invalid)}. Os permitidos são: {', '.join(PRIMARY_SYMPTOMS)}"
            )

        return symptoms


class TriageSubmitResponse(BaseModel):
    ticket_id: str
    assigned_specialty: str
    urgency_level: str
    status: str
    created_at: datetime


class PatientInputQueueItem(BaseModel):
    perceived_severity: int = Field(..., description="Severidade percebida de 1 a 10")
    symptom_duration_hours: float = Field(..., description="Duração dos sintomas em horas")
    primary_symptoms: list[str] = Field(..., description="Sintomas primários informados")
    description: str = Field(..., description="Descrição detalhada dos sintomas")


class TriageQueueItem(BaseModel):
    ticket_id: str
    assigned_specialty: str
    urgency_level: str
    status: str
    created_at: datetime
    patient_input: PatientInputQueueItem


class TriageQueueResponse(BaseModel):
    items: list[TriageQueueItem]
    total: int


class TriageFinishResponse(BaseModel):
    ticket_id: str
    status: str


