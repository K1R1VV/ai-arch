from abc import ABC, abstractmethod
from src.Application.DTOs.qa_dto import QA_Request

class ILlmService(ABC):
    @abstractmethod
    def get_llm_answer(self, request: QA_Request, context: str) -> str:
        pass
    @abstractmethod
    def clear_history(self, session_id: str) -> None:
        pass