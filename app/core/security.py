import logging
from typing import Any
from datetime import datetime, timedelta, timezone

from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# Configura o logger a nível de aplicação
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Inicializa o contexto de hashing de senha com o esquema bcrypt.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Define o esquema de obtenção de token OAuth2 para endpoints seguros.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def get_password_hash(password: str) -> str:
    """Cria o hash de uma senha em texto plano usando o algoritmo configurado.

    Args:
        password (str): A senha em texto plano a ser criptografada.

    Returns:
        str: A senha criptografada.
    """
    logger.debug("Hashing password.")
    return pwd_context.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """Verifica se uma senha em texto plano corresponde à sua versão com hash.

    Args:
        password (str): A senha em texto plano.
        hashed_password (str): A senha com hash para comparação.

    Returns:
        bool: True se a senha corresponder, False caso contrário.
    """
    logger.debug("Verifying password.")
    result = pwd_context.verify(password, hashed_password)
    logger.debug("Password verification result: %s", result)
    return result


def create_token(data: dict, minutes: int) -> str:
    """Gera um JSON Web Token (JWT) com um tempo de expiração definido.

    Args:
        data (dict): Os dados (payload) a serem incluídos no token.
        minutes (int): O tempo de validade do token em minutos.

    Returns:
        str: O token JWT codificado.
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    to_encode = data.copy()
    to_encode.update({"exp": expire})
    logger.debug("Creating token with expiration: %s", expire.isoformat())
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    logger.info("Token created successfully.")
    return encoded_jwt


def create_access_token(data: dict) -> str:
    """Gera um token de acesso de curta duração para sessões de usuário.

    Args:
        data (dict): Os dados (payload) para o token.

    Returns:
        str: O token de acesso JWT.
    """
    logger.info("Creating access token.")
    return create_token(data, settings.access_token_lifetime)


def create_refresh_token(data: dict, remember_me: bool = False) -> str:
    """Gera um token de atualização com duração configurável.

    Args:
        data (dict): Os dados (payload) para o token.
        remember_me (bool, optional): Se True, gera um token de longa duração.
                                      O padrão é False.

    Returns:
        str: O token de atualização JWT.
    """
    minutes = (
        settings.long_refresh_token_lifetime
        if remember_me
        else settings.short_refresh_token_lifetime
    )
    logger.info("Creating refresh token. Remember me: %s", remember_me)
    return create_token(data, minutes)


def get_subject_from_token(token: str) -> str:
    """Extrai a declaração 'sub' (subject) de um JWT, validando sua estrutura.

    Args:
        token (str): O token JWT a ser decodificado.

    Raises:
        ValueError: Se o token for inválido ou a declaração 'sub' estiver
                    ausente ou não for uma string.

    Returns:
        str: O valor da declaração 'sub' (geralmente o email ou ID do usuário).
    """
    try:
        logger.debug("Decoding token to extract subject.")
        payload: dict[str, Any] = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        subject = payload.get("sub")
        if not isinstance(subject, str):
            logger.error("Subject claim is missing or not a string.")
            raise ValueError("Subject not found or not a string")
        logger.info("Token subject extracted successfully.")
        return subject
    except JWTError as e:
        logger.error("Failed to decode token: %s", str(e))
        raise ValueError("Invalid token")
