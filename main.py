import logging
from fastapi import FastAPI
from dotenv import load_dotenv
from src.Presentation.Controllers import qa_controller

logging.basicConfig(level=logging.INFO)
load_dotenv()

app = FastAPI(title="RAG Chef Service", description="Кулинарный RAG-ассистент (Вариант 10)")
app.include_router(qa_controller.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)