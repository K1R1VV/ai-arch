from pydantic import BaseModel
from typing import Optional, List

class QA_Request(BaseModel):
    question: str
    session_id: Optional[str] = None

class QA_Response(BaseModel):
    answer: str
    session_id: str
    used_recipes: Optional[List[str]] = []