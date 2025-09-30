import logging
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc, or_
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status

from app.models.user import User
from app.schemas.user import UserCreate
from app.core.security import get_password_hash, verify_password
# from app.services.smtp_service import send_welcome_email

logger = logging.getLogger(__name__)

async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """Procura e retorna um usuário pelo email."""
    logger.debug("Buscando usuário pelo email: %s", email)
    result = await db.execute(select(User).where(User.email == email))
    return result.scalars().first()


async def get_user_by_email_or_username(db: AsyncSession, email: str, username: str) -> User | None:
    """Procura e retorna um usuário pelo email ou username."""
    logger.debug("Procurando um usuário pelo email (%s) ou username (%s)", email, username)
    result = await db.execute(
        select(User).where(or_(User.email == email, User.username == username))
    )
    return result.scalars().first()


async def register_user(db: AsyncSession, user_in: UserCreate) -> User:
    """
    Registra um usuário no banco de dados.
    """
    hashed_password = get_password_hash(user_in.password)
    

    db_user = User(
        email=user_in.email,
        username=user_in.username,
        password=hashed_password,
        role=user_in.role 
    )
    
    db.add(db_user)
    
    try:
        await db.commit()
        await db.refresh(db_user)
        logger.info("Usuário %s criado no banco de dados.", user_in.email)
        return db_user
    except IntegrityError:
    
        await db.rollback()
        logger.error(
            "DB IntegrityError na criação do usuário com email %s ou username %s", 
            user_in.email, user_in.username
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Um usuário com esse email ou username já existe.",
        )

async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None:
    """
    Autentica o usuário pelo email e senha
    Se for autenticado corretamente retorna o usuário, caso não retorna NADA.
    """
    logger.info("Tentando autenticar usuário com email : %s", email)
    user = await get_user_by_email(db, email)
    
    if not user:
        logger.warning("Autenticação falhou, não existe usuário com esse email %s", email)
        return None

   
    if not verify_password(password, str(user.password)):
        logger.warning("Autenticação falhou, email ou senha incorretos.%s", email)
        return None
    
    logger.info("Usuário %s autenticado com sucesso.", email)
    return user



async def get_users_leaderboard(db:AsyncSession) -> List[User]: 
    logger.info("Tentando pegar o ranking dos usuários")
    stmt = select(User).order_by(desc(User.points))

    result = await db.execute(stmt)
    leaderboard = result.scalars().all()

    return list(leaderboard)



#async def run_welcome_email_task(user_email: str):
 #   """Wrapper pra rodar a tarefa de mandar o email em segundo plano"""
  #  await send_welcome_email(user_email=user_email)
   # logger.info("Email de boas-vindas enviado para %s", user_email)
