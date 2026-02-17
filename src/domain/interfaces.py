from abc import ABC, abstractmethod
from src.domain.entities import PatientVitals, RiskAssessment

class IHealthClassifier(ABC):
    """Абстрактный интерфейс модели ИИ."""
    
    @abstractmethod
    def assess(self, vitals: PatientVitals) -> RiskAssessment:
        """Метод для выполнения предсказания."""
        pass