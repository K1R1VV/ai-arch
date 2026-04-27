import pytest
from unittest.mock import Mock, patch
from src.Domain.Interfaces.i_llm_service import ILlmService
from src.Domain.Interfaces.i_vector_db_service import IVectorDbService
from src.Application.Services.rag_service import RagService
from src.Application.DTOs.qa_dto import QA_Request

@pytest.fixture
def mock_llm_service():
    service = Mock(spec=ILlmService)
    service.get_llm_answer.return_value = "Ответ от тестовой LLM"
    service.clear_history.return_value = None
    return service

@pytest.fixture
def mock_vector_db_service():
    service = Mock(spec=IVectorDbService)
    service.search.return_value = [
        {"id": 1, "score": 0.9, "payload": {"text": "Тестовый рецепт", "title": "Борщ"}}
    ]
    return service

@pytest.fixture
def rag_service(mock_llm_service, mock_vector_db_service):
    with patch('src.Application.Services.rag_service.SentenceTransformer'):
        return RagService(mock_llm_service, mock_vector_db_service)

@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from main import app
    with TestClient(app) as c:
        yield c