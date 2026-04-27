from abc import ABC, abstractmethod
from typing import List, Dict, Any

class IVectorDbService(ABC):
    @abstractmethod
    def search(self, query_vector: List[float], limit: int) -> List[dict]:
        pass