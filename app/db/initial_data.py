import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.sign import Sign
from app.models.module import Module

logger = logging.getLogger(__name__)

async def create_initial_data(db: AsyncSession):
    """
    Verifica e cria os dados iniciais (módulos e sinais) se o banco estiver vazio.
    """
    # 1. Verifica se já existem módulos para evitar duplicatas
    result = await db.execute(select(Module).limit(1))
    if result.scalars().first():
        logger.info("Dados iniciais já existem. Ignorando a criação.")
        return

    logger.info("Criando dados iniciais para Sinais e Módulos...")

    try:
        # 2. Crie os objetos de Sinais (Signs)
        sign_bom_dia = Sign(
            name="Bom dia",
            desc="",
            videoUrl="",
            pontos=10
        )
        sign_obrigado = Sign(
            name="Obrigado",
            desc="",
            videoUrl="",
            pontos=10
        )
        sign_tudo_bem = Sign(
            name="Tudo bem?",
            desc="",
            videoUrl="",
            pontos=15
        )
        sign_qual_seu_nome= Sign(
            name="Tudo bem?",
            desc="",
            videoUrl="",
            pontos=15
        )
        

        db.add_all([sign_bom_dia, sign_obrigado, sign_tudo_bem, sign_qual_seu_nome])
        await db.flush() # Usa flush para obter os IDs antes do commit

        # 3. Crie os Módulos e associe os Sinais a eles
        module_cumprimentos = Module(
            name="introducao",
            signs=[sign_bom_dia, sign_obrigado, sign_tudo_bem, sign_qual_seu_nome]
        )
        
        db.add(module_cumprimentos)

        
        await db.commit()
        logger.info("Dados iniciais criados com sucesso! 🌱")

    except Exception as e:
        logger.error("Falha ao criar dados iniciais: %s", e)
        await db.rollback()