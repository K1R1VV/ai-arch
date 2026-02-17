import json
import logging
from typing import Dict
from src.domain.interfaces import IHealthClassifier
from src.domain.entities import PatientVitals, RiskAssessment


logger = logging.getLogger(__name__)

class DiagnosticService:
    _FEATURE_STATS = {
        "age": {"mean": 45.0, "std": 15.0},
        "cholesterol": {"mean": 5.0, "std": 1.2},
        "heart_rate": {"mean": 75.0, "std": 12.0}
    }

    def __init__(self, classifier: IHealthClassifier):
        self._classifier = classifier

    def _standatize(self, vitals: PatientVitals) -> Dict[str, float]:
        standardized = {
            "age": (vitals.age - self._FEATURE_STATS["age"]["mean"]) / self._FEATURE_STATS["age"]["std"],
            "cholesterol": (vitals.cholesterol - self._FEATURE_STATS["cholesterol"]["mean"]) / self._FEATURE_STATS["cholesterol"]["std"],
            "heart_rate": (vitals.heart_rate - self._FEATURE_STATS["heart_rate"]["mean"]) / self._FEATURE_STATS["heart_rate"]["std"]
        }
        logger.debug(f"Standardized features: {standardized}")
        return standardized

    def assess_risk(self, vitals: PatientVitals) -> RiskAssessment:
        _ = self._standatize(vitals)

        return self._classifier.assess(vitals)
    
    def generate_report(self, vitals: PatientVitals, assessment: RiskAssessment) -> str:
        report = {
            "patient": {
                "age": vitals.age,
                "cholesterol_mmol_l": vitals.cholesterol,
                "heart_rate_bpm": vitals.heart_rate
            },
            "risk_assessment": {
                "level": assessment.risk_level,
                "probability": assessment.probability,
                "interpretation": "Повышенный риск сердечно-сосудистых заболеваний" 
                    if assessment.risk_level == "High" 
                    else "Низкий риск при текущих показателях"
            },
            "recommendation": "Рекомендуется консультация кардиолога" 
                if assessment.risk_level == "High" 
                else "Регулярный профилактический осмотр"
        }
        return json.dumps(report, ensure_ascii=False, indent=2)