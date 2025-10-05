from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import user , recognition
# --- MODIFICADO: Importa a sessão e a função de dados iniciais ---
from app.db.database_connection import engine, Base, AsyncSessionLocal
from app.db.initial_data import create_initial_data 
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
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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

    # --- MODIFICADO: Adiciona a chamada para criar os dados iniciais ---
    logger.info("Verificando e populando dados iniciais...")
    async with AsyncSessionLocal() as session:
        await create_initial_data(session)


# Inclue o router de users.
app.include_router(user.router)
logger.info("Router de users incluído")


# Inclue o router do reconhecimento de sinais
app.include_router(recognition.router, prefix="/action", tags=["Action Recognition"])
logger.info("Action recognition router included")