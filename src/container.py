import punq
from src.Application.Interfaces.i_rag_service import IRagService
from src.Application.Services.rag_service import RagService
from src.Domain.Interfaces.i_llm_service import ILlmService
from src.Domain.Interfaces.i_vector_db_service import IVectorDbService
from src.Infrastructure.Services.llm_service import LlmService
from src.Infrastructure.Services.vector_db_service import VectorDbService

container = punq.Container()
container.register(ILlmService, LlmService, scope=punq.Scope.singleton)
container.register(IVectorDbService, VectorDbService, scope=punq.Scope.singleton)
container.register(IRagService, RagService, scope=punq.Scope.singleton)