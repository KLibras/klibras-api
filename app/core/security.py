"""
Define funções de segurança da api, criação do token, validação, renovação.
"""



import logging
from typing import Any
from datetime import datetime, timedelta, timezone

from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def get_password_hash(password: str) -> str:
    """Cria o hash de uma senha em texto plano usando o algoritmo configurado."""
    logger.debug("Hashing a senha.")
    return pwd_context.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """Verifica se uma senha em texto plano corresponde à sua versão com hash."""
    logger.debug("Verificando a senha.")
    result = pwd_context.verify(password, hashed_password)
    logger.debug("Resultado da verificação da senha: %s", result)
    return result


def create_token(data: dict, minutes: int) -> str:
    """Gera um JSON Web Token (JWT) com um tempo de expiração definido."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    to_encode = data.copy()
    to_encode.update({"exp": expire})
    logger.debug("Criando um token com expiração em: %s", expire.isoformat())
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    logger.info("Token criado com sucesso.")
    return encoded_jwt


def create_access_token(data: dict) -> str:
    """Gera um token de acesso de curta duração para sessões de usuário."""
    logger.info("Criando um token de sucesso.")
    return create_token(data, settings.access_token_lifetime)


def create_refresh_token(data: dict, remember_me: bool = False) -> str:
    """Gera um token de atualização com duração configurável."""
    minutes = (
        settings.long_refresh_token_lifetime
        if remember_me
        else settings.short_refresh_token_lifetime
    )
    logger.info("Criando um refresh token. %s", remember_me)
    return create_token(data, minutes)


def get_subject_from_token(token: str) -> str:
    """Extrai a declaração 'sub' (subject) de um JWT, validando sua estrutura."""
    try:
        payload: dict[str, Any] = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        subject = payload.get("sub")
        if not isinstance(subject, str):
            logger.error("Erro ao retirar o subject to token.")
            raise ValueError("Subject não encontrado")
        logger.info("Usuário extraido do token corretamente.")
        return subject
    except JWTError as e:
        logger.error("Falhou ao decodificar o token: %s", str(e))
        raise ValueError("Token Inválido")