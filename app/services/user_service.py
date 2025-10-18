import logging
from typing import List
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc, or_
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status

from app.models.user import User
from app.models.module import Module
from app.models.sign import Sign
from app.schemas.user import UserCreate
from app.core.security import get_password_hash, verify_password

logger = logging.getLogger(__name__)

async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    logger.debug("Buscando usuário pelo email: %s", email)
    result = await db.execute(select(User).where(User.email == email))
    return result.scalars().first()

async def add_points(db: AsyncSession, username: str, points: int) -> bool:
    logger.debug("Tentando adicionar %d pontos ao usuário: %s", points, username)
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()

    if not user:
        logger.warning("Usuário '%s' não encontrado. Nenhum ponto foi adicionado.", username)
        return False

    try:
        user.points += points
        await db.commit()
        await db.refresh(user)
        
        logger.info(
            "Sucesso! %d pontos adicionados para '%s'. Novo total: %d",
            points,
            username,
            user.points
        )
        return True
    except Exception as e:
        logger.error(
            "Ocorreu um erro ao adicionar pontos para '%s': %s", username, e
        )
        await db.rollback()
        return False

async def get_user_by_email_or_username(db: AsyncSession, email: str, username: str) -> User | None:
    logger.debug("Procurando um usuário pelo email (%s) ou username (%s)", email, username)
    result = await db.execute(
        select(User).where(or_(User.email == email, User.username == username))
    )
    return result.scalars().first()

async def register_user(db: AsyncSession, user_in: UserCreate) -> User:
    hashed_password = get_password_hash(user_in.password)
    
    db_user = User(
        email=user_in.email,
        username=user_in.username,
        password=hashed_password,
        points=user_in.points,
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

async def add_completed_module_to_user(db: AsyncSession, user: User, module_id: int) -> User:
    result = await db.execute(
        select(Module)
        .options(selectinload(Module.signs))
        .filter(Module.id == module_id)
    )
    module_to_add = result.scalars().first()
    
    if not module_to_add:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Module with ID {module_id} not found."
        )
    
    result = await db.execute(
        select(User)
        .options(
            selectinload(User.completed_modules),
            selectinload(User.known_signs)
        )
        .filter(User.id == user.id)
    )
    db_user = result.scalars().first()
    
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )
    
    if module_to_add in db_user.completed_modules:
        logger.info(f"Module {module_id} already completed by user {user.id}")
        return db_user
    
    db_user.completed_modules.append(module_to_add)
    
    for sign in module_to_add.signs:
        if sign not in db_user.known_signs:
            db_user.known_signs.append(sign)
            db_user.points += sign.pontos
    
    await db.commit()
    await db.refresh(db_user)
    
    logger.info(f"Module {module_id} added to user {user.id}. New points: {db_user.points}")
    return db_user

async def add_known_sign_to_user(db: AsyncSession, user: User, sign_id: int) -> User:
    result = await db.execute(
        select(Sign).filter(Sign.id == sign_id)
    )
    sign_to_add = result.scalars().first()
    
    if not sign_to_add:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sign with ID {sign_id} not found."
        )
    
    result = await db.execute(
        select(User)
        .options(selectinload(User.known_signs))
        .filter(User.id == user.id)
    )
    db_user = result.scalars().first()
    
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )
    
    if sign_to_add in db_user.known_signs:
        logger.info(f"Sign {sign_id} already known by user {user.id}")
        return db_user
    
    db_user.known_signs.append(sign_to_add)
    db_user.points += sign_to_add.pontos
    
    await db.commit()
    await db.refresh(db_user)
    
    logger.info(f"Sign {sign_id} added to user {user.id}. New points: {db_user.points}")
    return db_user

async def get_user_known_signs(db: AsyncSession, user: User) -> List[Sign]:
    logger.debug("Buscando sinais conhecidos do usuário '%s'", user.username)
    result = await db.execute(
        select(User).options(selectinload(User.known_signs)).where(User.id == user.id)
    )
    user_with_signs = result.scalars().first()
    
    if not user_with_signs:
        return []
    
    return user_with_signs.known_signs

async def get_user_completed_modules(db: AsyncSession, user: User) -> List[Module]:
    logger.debug("Buscando módulos concluídos do usuário '%s'", user.username)
    result = await db.execute(
        select(User).options(selectinload(User.completed_modules)).where(User.id == user.id)
    )
    user_with_modules = result.scalars().first()
    
    if not user_with_modules:
        return []
    
    return user_with_modules.completed_modules
    
async def update_user_username(db: AsyncSession, user: User, new_username: str) -> User:
    logger.debug("Tentando atualizar username do usuário ID %d para '%s'", user.id, new_username)
    
    existing_user_result = await db.execute(select(User).where(User.username == new_username))
    if existing_user_result.scalars().first():
        logger.warning("Falha ao atualizar: username '%s' já está em uso.", new_username)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Este nome de usuário já está em uso.")
    
    user.username = new_username
    try:
        await db.commit()
        await db.refresh(user)
        logger.info("Username do usuário ID %d atualizado para '%s'", user.id, new_username)
        return user
    except Exception as e:
        await db.rollback()
        logger.error("Erro ao atualizar username do usuário ID %d: %s", user.id, e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Não foi possível atualizar o nome de usuário.")

async def update_user_password(db: AsyncSession, user: User, new_password: str) -> User:
    logger.debug("Atualizando a senha para o usuário '%s'", user.username)
    user.password = get_password_hash(new_password)
    try:
        await db.commit()
        await db.refresh(user)
        logger.info("Senha do usuário '%s' atualizada com sucesso.", user.username)
        return user
    except Exception as e:
        await db.rollback()
        logger.error("Erro ao atualizar a senha do usuário '%s': %s", user.username, e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Não foi possível atualizar a senha.")

async def get_modules(db: AsyncSession, name: str) -> Module | None:
    logger.debug("Buscando módulo pelo nome: %s", name)
    stmt = (
        select(Module)
        .options(selectinload(Module.signs)) 
        .where(Module.name == name)
    )
    result = await db.execute(stmt)
    module = result.scalars().first()

    if module:
        logger.info("Módulo '%s' encontrado com %d sinais.", name, len(module.signs))
    else:
        logger.warning("Módulo com nome '%s' não encontrado.", name)

    return module