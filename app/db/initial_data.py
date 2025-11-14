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
        desc="Este é um sinal composto por duas partes: <b>BOM</b> e <b>DIA</b>.<br><br>" \
            "<b>BOM:</b> Com a palma virada para você, junte as pontas dos dedos em frente à boca. Mova a mão para frente, abrindo e espalhando os dedos.<br>" \
            "<b>DIA:</b> Em seguida, com a mão em 'D' (indicador para cima, outros dedos em círculo com o polegar), faça um arco da direita para a esquerda, simbolizando o sol.",
        videoUrl="bom_dia",
        pontos=10
            )

        sign_obrigado = Sign(
            name="Obrigado",
            desc="Este sinal é realizado com as duas mãos.<br><br>" \
                "Posicione a mão esquerda tocando o queixo e a mão direita tocando a testa. Depois, mova <b>ambas as mãos</b> para a frente, em um gesto de oferecimento.",
            videoUrl="obrigado",
            pontos=10
        )

        sign_tudo_bem = Sign(
            name="Tudo bem?",
            desc="Este sinal é feito em duas partes, unindo <b>BOM</b> e o gesto de <b>JOIA</b>.<br><br>" \
                "<b>BOM:</b> Junte as pontas dos dedos em frente à boca com a palma para você, e então abra a mão para frente.<br>" \
                "<b>JOIA:</b> Logo em seguida, mude a configuração da mão para o sinal de 'joia' (polegar para cima).",
            videoUrl="tudo_bem",
            pontos=15
        )

        sign_qual_seu_nome = Sign(
            name="Qual seu nome?",
            desc="O sinal para 'Qual seu nome?' é feito da seguinte forma:<br><br>" \
                "Com a mão direita, levante os dedos <b>indicador e médio</b>. Faça um movimento de meia-lua com a mão, da esquerda para a direita.",
            videoUrl="qual_seu_nome",
            pontos=15
        )

        

	db.add_all([sign_obrigado, sign_bom_dia, sign_tudo_bem, sign_qual_seu_nome])
        await db.flush() # Usa flush para obter os IDs antes do commit

        # 3. Crie os Módulos e associe os Sinais a eles
        module_cumprimentos = Module(
            name="introducao",
            signs=[sign_obrigado, sign_tudo_bem, sign_qual_seu_nome, sign_bom_dia]
        )
        
        db.add(module_cumprimentos)

        
        await db.commit()
        logger.info("Dados iniciais criados com sucesso! 🌱")

    except Exception as e:
        logger.error("Falha ao criar dados iniciais: %s", e)
        await db.rollback()
