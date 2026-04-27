from src.Application.DTOs.qa_dto import QA_Request, QA_Response

def test_qa_request_creation():
    req = QA_Request(question="Как приготовить борщ?", session_id="123")
    assert req.question == "Как приготовить борщ?"
    assert req.session_id == "123"

def test_qa_response_creation():
    resp = QA_Response(answer="Сварите свеклу", session_id="123", used_recipes=["Борщ"])
    assert resp.answer == "Сварите свеклу"
    assert "Борщ" in resp.used_recipes