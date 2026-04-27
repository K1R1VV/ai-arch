from src.Application.DTOs.qa_dto import QA_Request

def test_answer_question_success(rag_service, mock_llm_service, mock_vector_db_service):
    request = QA_Request(question="Рецепт борща?", session_id="test-session")
    response = rag_service.answer_question(request)
    
    assert response.answer == "Ответ от тестовой LLM"
    assert response.session_id == "test-session"
    mock_vector_db_service.search.assert_called_once()
    mock_llm_service.get_llm_answer.assert_called_once()

def test_clear_history(rag_service, mock_llm_service):
    rag_service.clear_history("test-session")
    mock_llm_service.clear_history.assert_called_once_with("test-session")