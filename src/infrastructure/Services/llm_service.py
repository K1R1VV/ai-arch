import os, logging, requests
from fastapi import HTTPException
from src.Domain.Interfaces.i_llm_service import ILlmService
from src.Application.DTOs.qa_dto import QA_Request

logger = logging.getLogger(__name__)

class LlmService(ILlmService):
    def __init__(self):
        self.API_KEY = os.getenv("OPENROUTER_API_KEY")
        self.MODEL = os.getenv("OPENROUTER_MODEL", "qwen/qwen-2.5-7b-instruct")
        self.URL = "https://openrouter.ai/api/v1/chat/completions"
        self.conversations = {}
        
        if not self.API_KEY:
            raise ValueError("OPENROUTER_API_KEY не задан в .env")

    def get_llm_answer(self, request: QA_Request, context: str) -> str:
        sid = request.session_id or 'default'
        self.conversations.setdefault(sid, [])
        history = self.conversations[sid]

        system_prompt = (
            "Ты — профессиональный шеф-повар. Отвечай ТОЛЬКО на основе предоставленных рецептов. "
            "Учитывай ингредиенты, время и сложность. "
            f"Контекст:\n{context}"
        )

        messages = [{"role": "system", "content": system_prompt}] 
        for msg in history[-6:]:
            messages.append({"role": msg["role"], "content": msg["text"]})
        
        messages.append({"role": "user", "content": request.question})

        payload = {
            "model": self.MODEL,
            "messages": messages,
            "temperature": 0.4,
            "max_tokens": 1000
        }
        
        headers = {
            "Authorization": f"Bearer {self.API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8000", 
            "X-Title": "RAG Chef Service"
        }

        try:
            resp = requests.post(self.URL, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            ans = data['choices'][0]['message']['content']
            history.extend([
                {"role": "user", "text": request.question}, 
                {"role": "assistant", "text": ans}
            ])
            return ans
        except Exception as e:
            logger.error(f"OpenRouter Error: {e}")
            raise HTTPException(status_code=500, detail=f"LLM Error: {e}")

    def clear_history(self, session_id: str) -> None:
        self.conversations.pop(session_id, None)