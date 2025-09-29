import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.config import settings

# Configura o logger pro top-level
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Log para ver se a inicialização do banco de dados foi correto
logger.info("Initializing database engine with URL: %s", settings.database_url)

# Cria uma engine do SQLAlchemy
engine = create_async_engine(settings.database_url, echo=True)
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Declara de onde as classes do ORM devem ser obtidas
Base = declarative_base()
