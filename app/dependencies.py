from collections.abc import AsyncGenerator
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import get_subject_from_token
from app.db.database_connection import AsyncSessionLocal
from app.models.user import User
from app.services import user_service

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Função assincrona que providencia uma sessão com o banco de dados

    Yields:
        AsyncSession: Sessão assincrona com o banco de dados
    """
    async with AsyncSessionLocal() as session:
        yield session


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    """
    Dependencia para pegar o usuário atual que está usando a instância
    """
    try:
        email = get_subject_from_token(token)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticação inválida",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await user_service.get_user_by_email(db, email=email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user