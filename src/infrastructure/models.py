from src.domain.interfaces import IHealthClassifier
from src.domain.entities import PatientVitals, RiskAssessment

class ThresholdMockModel(IHealthClassifier):
    def __init__(self, cholesterol_threshold: float = 6.0, age_threshold: int = 60):
        self._cholesterol_threshold = cholesterol_threshold
        self._age_threshold = age_threshold
    
    def assess(self, vitals: PatientVitals) -> RiskAssessment:
        is_high_risk = (
            vitals.cholesterol > self._cholesterol_threshold or
            vitals.age > self._age_threshold
        )

        risk_level = "High" if is_high_risk else "Low"

        cholesterol_factor = max(0.0, (vitals.cholesterol - self._cholesterol_threshold) / 2.0)
        age_factor = max(0.0, (vitals.age - self._age_threshold) / 20.0)
        probability = min(0.95, 0.7 + max(cholesterol_factor, age_factor)) if is_high_risk else 0.85

        return RiskAssessment(risk_level=risk_level, probability=round(probability, 2))