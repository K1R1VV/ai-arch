import uuid
import logging
from fastapi import HTTPException
from sentence_transformers import SentenceTransformer
from src.Application.DTOs.qa_dto import QA_Request, QA_Response
from src.Application.Interfaces.i_rag_service import IRagService
from src.Domain.Interfaces.i_llm_service import ILlmService
from src.Domain.Interfaces.i_vector_db_service import IVectorDbService

logger = logging.getLogger(__name__)

class RagService(IRagService):
    def __init__(self, llm_service: ILlmService, vector_db_service: IVectorDbService):
        self.llm_service = llm_service
        self.vector_db_service = vector_db_service
        self.embedding_model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')

    def answer_question(self, request: QA_Request) -> QA_Response:
        try:
            query_vector = self.embedding_model.encode(request.question).tolist()
            logger.info(f"Encoded question: {request.question[:50]}...")

            search_results = self.vector_db_service.search(query_vector=query_vector, limit=3)
            if not search_results:
                raise HTTPException(status_code=404, detail="Подходящие рецепты не найдены.")

            context_parts, used_recipes = [], []
            for hit in search_results:
                p = hit['payload']
                recipe_text = (
                    f"Название: {p.get('title')}\n"
                    f"Ингредиенты: {', '.join(p.get('ingredients', []))}\n"
                    f"Время: {p.get('cooking_time')}\n"
                    f"Сложность: {p.get('difficulty')}\n"
                    f"Шаги: {p.get('steps')}"
                )
                context_parts.append(recipe_text)
                used_recipes.append(p.get('title', 'Unknown'))

            context = "\n---\n".join(context_parts)

            if not request.session_id:
                request.session_id = str(uuid.uuid4())

            llm_answer = self.llm_service.get_llm_answer(request, context)
            return QA_Response(answer=llm_answer, session_id=request.session_id, used_recipes=used_recipes)
        except Exception as e:
            logger.error(f"Error in answer_question: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    def clear_history(self, session_id: str) -> None:
        try:
            self.llm_service.clear_history(session_id)
        except Exception as e:
            logger.error(f"Error clearing history: {e}")
            raise