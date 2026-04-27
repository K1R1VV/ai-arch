from abc import ABC, abstractmethod
from src.Application.DTOs.qa_dto import QA_Request, QA_Response

class IRagService(ABC):
    @abstractmethod
    def answer_question(self, request: QA_Request) -> QA_Response:
        pass
    @abstractmethod
    def clear_history(self, session_id: str) -> None:
        pass