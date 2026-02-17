from pydantic import BaseModel as PydanticBaseModel
from dataclasses import dataclass

@dataclass(frozen=True)
class PatientVitals(PydanticBaseModel):
    age: int
    cholesterol: float
    heart_rate: int

    def __post_init__(self):
        if self.age <= 0 or self.age > 150:
            raise ValueError("Age must be between 1 and 150")
        if self.cholesterol <= 0 or self.cholesterol > 20:
            raise ValueError("Cholesterol must be between 0 and 20 mmol/L")
        if self.heart_rate <= 0 or self.heart_rate > 300:
            raise ValueError("Heart rate must be between 1 and 300 bpm")

@dataclass(frozen=True)
class RiskAssessment(PydanticBaseModel):
    risk_level: str
    probability: float

    def __post_init__(self):
        if self.risk_level not in ("Low", "High"):
            raise ValueError("Risk level must be 'Low' or 'High'")
        if not 0.0 <= self.probability <= 1.0:
            raise ValueError("Probability must be between 0.0 and 1.0")