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
from pydantic import BaseModel

# Imports para a autenticação com Google
from google.oauth2 import id_token
from google.auth.transport import requests

from app.schemas.enums import UserRole
from app.services import user_service
# --- MODIFICADO: Importa os schemas necessários ---
from app.schemas.user import UserCreate, UserRead
from app.schemas.token import Token
from app.schemas.sign import SignRead
from app.schemas.module import ModuleRead, ModuleWithSigns
from app.dependencies import get_current_user, get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_subject_from_token,
)
# Importa as configurações centralizadas
from app.core.config import settings
from app.models.user import User
from app.models.sign import Sign
from app.models.module import Module

logger = logging.getLogger(__name__)
router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

# --- Modelos para receber o token do Google e dados de update ---
class GoogleToken(BaseModel):
    id_token: str

class UsernameUpdate(BaseModel):
    new_username: str

class PasswordUpdate(BaseModel):
    new_password: str

@router.post("/auth/google", response_model=Token)
async def google_auth(token: GoogleToken, db: AsyncSession = Depends(get_db)):
    """
    Lida com o login/registro de um usuário através de um Google ID Token.
    Se o usuário não existir, um novo é criado na base de dados.
    """
    try:
        
        idinfo = id_token.verify_oauth2_token(
            token.id_token, requests.Request(), settings.google_client_id
        )

        email = idinfo.get("email")
        if not email:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="E-mail não encontrado no token.")

        # Verifica se o usuário já existe na sua base de dados
        user = await user_service.get_user_by_email(db, email=email)

        if not user:
            logger.info("Usuário com e-mail %s não encontrado. Criando novo usuário.", email)
            # Lógica para criar um nome de usuário a partir do nome do Google
            google_name = idinfo.get("name", "")
            sanitized_username = google_name.replace(" ", "").lower()[:15]
            
            # Cria a estrutura do novo usuário
            user_in = UserCreate(
                email=email,
                username=sanitized_username,
                # Usa o 'sub' (ID único do Google) como senha
                password=idinfo.get("sub"),
                points=0,
                role=UserRole.USER
            )
            user = await user_service.register_user(db=db, user_in=user_in)

        # Se o usuário já existia ou foi criado com sucesso, gera os tokens da sua API
        logger.info("Gerando tokens para o usuário: %s", user.email)
        access_token = create_access_token(data={"sub": str(user.email)})
        refresh_token = create_refresh_token(data={"sub": str(user.email)})

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }

    except ValueError as e:
        logger.error("Erro de validação do token do Google: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token do Google inválido ou expirado.",
        )
    except Exception as e:
        logger.error("Um erro inesperado ocorreu durante a autenticação com Google: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ocorreu um erro: {e}",
        )


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
    
    # background_tasks.add_task(user_service.run_welcome_email_task, str(usuario.email))

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
    Emite um novo token de acesso usando um token de atualização válido.
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
    Retorna os dados do usuário autenticado atualmente.
    """
    return current_user


@router.post(
    "/users/me/modules/{module_id}",
    response_model=UserRead,
    summary="Adiciona um módulo como concluído para o usuário"
)
async def add_completed_module(
    module_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Marca um módulo como concluído para o usuário logado.
    Adiciona os sinais do módulo aos sinais conhecidos e atualiza os pontos.
    """
    updated_user = await user_service.add_completed_module_to_user(
        db=db, user=current_user, module_id=module_id
    )
    return updated_user

@router.post(
    "/users/me/signs/{sign_id}",
    response_model=UserRead,
    summary="Adiciona um sinal como conhecido para o usuário"
)
async def add_known_sign(
    sign_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Adiciona um único sinal à lista de sinais conhecidos do usuário logado
    e atualiza sua pontuação.
    """
    updated_user = await user_service.add_known_sign_to_user(
        db=db, user=current_user, sign_id=sign_id
    )
    return updated_user

@router.get(
    "/users/me/modules",
    response_model=List[ModuleRead],
    summary="Busca os módulos concluídos pelo usuário"
)
async def get_completed_modules(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retorna a lista de todos os módulos que o usuário logado já completou.
    """
    modules = await user_service.get_user_completed_modules(db=db, user=current_user)
    return modules

@router.get(
    "/users/me/signs",
    response_model=List[SignRead],
    summary="Busca os sinais conhecidos pelo usuário"
)
async def get_known_signs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retorna a lista de todos os sinais que o usuário logado conhece.
    """
    signs = await user_service.get_user_known_signs(db=db, user=current_user)
    return signs

@router.patch(
    "/users/me/username",
    response_model=UserRead,
    summary="Atualiza o nome de usuário"
)
async def update_username(
    username_update: UsernameUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Atualiza o nome de usuário (username) do usuário logado.
    """
    updated_user = await user_service.update_user_username(
        db=db, user=current_user, new_username=username_update.new_username
    )
    return updated_user

@router.patch(
    "/users/me/password",
    status_code=status.HTTP_200_OK,
    summary="Atualiza a senha do usuário"
)
async def update_password(
    password_update: PasswordUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Atualiza a senha do usuário logado.
    """
    await user_service.update_user_password(
        db=db, user=current_user, new_password=password_update.new_password
    )
    return {"message": "Senha atualizada com sucesso."}

@router.get(
    "/get_module/{name}",
    response_model=ModuleWithSigns, 
    summary="Obter um Módulo pelo Nome",
    description="Busca um módulo específico pelo seu nome e retorna seus detalhes junto com a lista de sinais associados.",
    tags=["Modules"] 
)
async def get_module_by_name(
    name: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user) 
):
    """
    Endpoint para buscar um módulo pelo nome.

    - **name**: O nome exato do módulo a ser buscado.
    - Retorna o módulo e seus sinais se encontrado.
    - Retorna um erro 404 Not Found se o módulo não existir.
    """
    # Chama a função do CRUD passando a sessão e o nome do módulo
    module = await user_service.get_modules(db=db, name=name)

    # Se a função retornar None, significa que o módulo não foi encontrado
    if not module:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Módulo com o nome '{name}' não encontrado."
        )
    return module
