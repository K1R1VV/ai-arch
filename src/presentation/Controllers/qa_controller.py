from fastapi import APIRouter, Depends
from src.Application.DTOs.qa_dto import QA_Request, QA_Response
from src.Application.Interfaces.i_rag_service import IRagService
from src.container import container

router = APIRouter()

def get_rag_service() -> IRagService:
    return container.resolve(IRagService)

@router.post("/qa", response_model=QA_Response)
def answer_question(request: QA_Request, rag_service: IRagService = Depends(get_rag_service)):
    return rag_service.answer_question(request)

@router.get("/clear_history/{session_id}", status_code=204)
def clear_history(session_id: str, rag_service: IRagService = Depends(get_rag_service)):
    rag_service.clear_history(session_id)
    return {}