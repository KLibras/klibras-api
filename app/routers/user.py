import logging
from typing import List
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    Request,
    Response,
    Body,
    BackgroundTasks,
)
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.services import user_service
from app.schemas.user import UserCreate, UserRead
from app.schemas.token import Token
from app.dependencies import get_current_user, get_db 
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_subject_from_token,
)
from app.core.config import settings
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(
    user_in: UserCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Lida com o registro de usuário.
    Valida se e-mail/nome de usuário são únicos, cria o usuário e
    coloca na fila um e-mail de boas-vindas para ser enviado em segundo plano.
    """
    logger.info("Solicitação de registro para o e-mail: %s", user_in.email)

    usuario_existente = await user_service.get_user_by_email_or_username(
        db, email=user_in.email, username=user_in.username
    )
    
    if usuario_existente is not None: 
        logger.warning(f"O registro falhou para {user_in.email}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

    usuario = await user_service.register_user(db=db, user_in=user_in)
 
    if usuario is None:
        logger.error("A criação de usuário falhou inesperadamente para %s.", user_in.email)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Falha ao criar usuário.")
    
    background_tasks.add_task(user_service.run_welcome_email_task, str(usuario.email))

    logger.info("Usuário %s registrado com sucesso. E-mail de boas-vindas na fila.", usuario.email)
    return usuario


@router.post("/login", response_model=Token)
async def login(
    request: Request,
    db: AsyncSession = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    """
    Autentica um usuário e retorna os tokens de acesso e de atualização (refresh) JWT no corpo da resposta.
    """
    logger.info("Tentativa de login para o usuário: %s", form_data.username)
    usuario = await user_service.authenticate_user(
        db, email=form_data.username, password=form_data.password
    )
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    lembrar_me = request.query_params.get("rememberMe", "false").lower() == "true"
    access_token = create_access_token(data={"sub": str(usuario.email)})
    refresh_token = create_refresh_token(
        data={"sub": str(usuario.email)}, remember_me=lembrar_me
    )

    logger.info("Login bem-sucedido para o usuário: %s", usuario.email)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/refresh", response_model=Token)
async def refresh_token(
    db: AsyncSession = Depends(get_db),
    refresh_token: str = Body(..., embed=True),
):
    """
    Emite um novo token de acesso usando um token de atualizaÃ§Ã£o vÃ¡lido.
    """
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de atualização não encontrado no corpo do request.",
        )
    try:
        email = get_subject_from_token(refresh_token)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token de atualização inválido"
        )

    usuario = await user_service.get_user_by_email(db, email=email)
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário associado ao token não encontrado.",
        )

    novo_access_token = create_access_token(data={"sub": str(usuario.email)})
    logger.info("Novo token de acesso emitido para o usuário %s via token de atualização.", usuario.email)
    return {
        "access_token": novo_access_token,
        "refresh_token": refresh_token, 
        "token_type": "bearer"
    }

@router.get(
    "/leaderboard", 
    response_model=List[UserRead], 
    status_code=200,
    summary="Pega o ranking"
)
async def get_leaderboard(
    db: AsyncSession = Depends(get_db)
):
    """
    Busca a lista do ranking em ordem decrescente
    """
    
    leaderboard_data = await user_service.get_users_leaderboard(db)
    
    logger.info("Buscando o ranking.")

    return leaderboard_data

@router.get("/users/me", response_model=UserRead)
async def current_user(current_user: User = Depends(get_current_user)):
    """
    Procura o usuário autenticado atualmente
    """
    return current_user