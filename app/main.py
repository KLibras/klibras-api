from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import user #, recognition
from app.db.database_connection import engine, Base
from app.core.config import settings
import logging

# Inicializa a instância do FastAPI
app = FastAPI()

# Configura como os logs serão mostrados
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Configura o CORS 
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,  # Lista de origens/ips liberados para fazer requests // Em produção deixa vazio senão vai bloquear os requests
    allow_credentials=True,
    allow_methods=["*"],  # Permite todos os metodos HTTP
    allow_headers=["*"],  # Permite todos os headers
)

@app.on_event("startup")
async def startup_event():
    """
    Event handler que carrega a aplicação na inicialização

    Cria todas as tabelas do banco de dados caso não tenham sido criadas
    """
    logger.info("Começando a aplicação, criando tabelas do banco de dados se não existirem")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Criação da tabelas ocorreu bem")

# Inclue o router de users.
app.include_router(user.router)
logger.info("Router de users incluído")


# Inclue o router do reconhecimento de sinais

#app.include_router(recognition.router, prefix="/action", tags=["Action Recognition"])
#logger.info("Action recognition router included")


