import os
from dotenv import load_dotenv

load_dotenv()

def get_env_variable(name: str) -> str:
    """Recupera o valor de uma variável de ambiente.

    Levanta um EnvironmentError se a variável não estiver definida, garantindo
    que configurações críticas estejam sempre presentes em tempo de execução.

    Args:
        name (str): O nome da variável de ambiente a ser recuperada.

    Returns:
        str: O valor da variável de ambiente.

    Raises:
        EnvironmentError: Se a variável de ambiente especificada não for encontrada.
    """
    value = os.environ.get(name)
    if value is None:
        raise EnvironmentError(f"Missing required environment variable: {name}")
    return value

class Settings:
    """Agrupa as configurações da aplicação carregadas a partir de variáveis de ambiente.

    Esta classe encapsula todos os parâmetros de configuração necessários para a aplicação.
    Ela garante que todas as variáveis de ambiente necessárias sejam carregadas na inicialização
    e fornece um ponto de acesso centralizado para as configurações.
    """
    database_url: str = get_env_variable("DATABASE_URL")
    allowed_origins: list[str] = get_env_variable("ALLOWED_ORIGINS").split(",")
    secret_key: str = get_env_variable("SECRET_KEY")
    algorithm: str = get_env_variable("ALGORITHM")
    access_token_lifetime: int = int(get_env_variable("ACCESS_TOKEN_LIFETIME"))
    long_refresh_token_lifetime: int = int(get_env_variable("LONG_REFRESH_TOKEN_LIFETIME"))
    short_refresh_token_lifetime: int = int(get_env_variable("SHORT_REFRESH_TOKEN_LIFETIME"))
    google_client_id: str = get_env_variable("GOOGLE_CLIENT_ID")
    rabbitmq_url: str = get_env_variable("RABBITMQ_URL")


settings = Settings()
