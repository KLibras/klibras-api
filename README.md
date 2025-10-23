<div align="center">

# KLibras API

### Plataforma de Reconhecimento de Linguagem de Sinais Brasileira

[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.4-009688.svg)](https://fastapi.tiangolo.com/)
[![TensorFlow](https://img.shields.io/badge/TensorFlow-CPU-FF6F00.svg)](https://www.tensorflow.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**API REST para reconhecimento de Libras em tempo real, com inteligência artificial e visão computacional**

[Características](#características) • [Início Rápido](#início-rápido) • [Documentação da API](#documentação-da-api) • [Arquitetura](#arquitetura) • [Contribuindo](#contribuindo)

</div>

---

## Visão Geral

A KLibras API é uma API REST de alta performance, desenvolvida para reconhecimento de Linguagem Brasileira de Sinais (Libras) em tempo real. Construída com FastAPI e alimentada por TensorFlow e MediaPipe, oferece reconhecimento preciso de gestos, rastreamento de progresso do usuário e recursos de gamificação para aplicações de aprendizado de linguagem de sinais.

### Por que KLibras?

- **Alta Performance**: Arquitetura assíncrona com RabbitMQ para processamento escalável de vídeos
- **Inteligência Artificial**: Modelos avançados de machine learning com detecção de pose e mãos via MediaPipe
- **Segurança Corporativa**: Autenticação JWT com integração OAuth2 (Google Sign-In)
- **Rastreamento de Progresso**: Sistema completo de acompanhamento com pontos e rankings
- **Cloud Native**: Pronto para Docker com configuração de deploy para produção
- **Escalável**: Processamento assíncrono com fila de mensagens para altas cargas

---

## Características

### Inteligência Artificial e Visão Computacional
- **Reconhecimento de Sinais em Tempo Real**: Processa vídeos e identifica gestos de Libras com limite de confiança superior a 75%
- **Arquitetura Multi-Modelo**: Combina TensorFlow, MediaPipe Pose e detecção de landmarks das mãos
- **Análise de Sequência de Ações**: Processa sequências de 100 frames para reconhecimento preciso de gestos
- **Processamento em Lote**: Fila de jobs assíncronos baseada em RabbitMQ para lidar com múltiplas requisições

### Gerenciamento de Usuários
- **Autenticação OAuth2**: Tokens JWT com suporte a access e refresh token
- **Integração com Google Sign-In**: Autenticação perfeita com contas Google
- **Perfis de Usuário**: Gerenciamento completo de dados do usuário com rastreamento de progresso
- **Controle de Acesso Baseado em Funções**: Suporte para diferentes papéis e permissões de usuário

### Plataforma de Aprendizado
- **Sistema de Módulos**: Módulos de aprendizado organizados com sinais associados
- **Rastreamento de Progresso**: Acompanha módulos concluídos e sinais conhecidos
- **Gamificação**: Sistema de pontos e rankings em leaderboard
- **Biblioteca de Sinais**: Base de dados abrangente de sinais de Libras com referências em vídeo

### Experiência do Desenvolvedor
- **API RESTful**: Endpoints limpos e intuitivos seguindo princípios REST
- **OpenAPI/Swagger**: Documentação interativa da API gerada automaticamente
- **Operações Assíncronas**: Suporte a long-polling para atualizações de status em tempo real
- **Health Checks**: Endpoints de monitoramento integrados
- **Suporte CORS**: Compartilhamento de recursos entre origens configurável

---

## Início Rápido

### Pré-requisitos

- **Python 3.11+**
- **Docker & Docker Compose**
- **PostgreSQL** (ou banco de dados assíncrono compatível)
- **RabbitMQ** (para processamento assíncrono de vídeos)

### Arquivos de Modelo Necessários

Certifique-se de que os seguintes arquivos de modelo estejam no diretório raiz:
- `asl_action_recognizer.h5` - Modelo de reconhecimento de ações TensorFlow
- `pose_landmarker_lite.task` - Modelo de detecção de pose MediaPipe
- `hand_landmarker.task` - Modelo de landmarks das mãos MediaPipe
- `asl_model.tflite` - Modelo TensorFlow Lite

### Configuração

#### 1. Clone o Repositório

```bash
git clone https://github.com/KLibras/klibras-api.git
cd klibras-api
```

#### 2. Configure as Variáveis de Ambiente

Crie um arquivo `.env` na raiz do projeto:

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:password@postgres:5432/klibras

# Security
SECRET_KEY=sua-chave-secreta-aqui-use-um-hash-seguro
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080

# Google OAuth (opcional)
GOOGLE_CLIENT_ID=seu-google-client-id

# RabbitMQ
RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/

# Application
DEBUG=False
```

#### 3. Execute com Docker Compose

```bash
# Inicie todos os serviços (API, PostgreSQL, RabbitMQ)
docker-compose up -d

# Veja os logs
docker-compose logs -f api

# Pare os serviços
docker-compose down

# Pare e remova volumes (limpa o banco de dados)
docker-compose down -v
```

#### 4. Acesse a Aplicação

- **API Base**: `http://localhost:8000`
- **Documentação Interativa (Swagger)**: `http://localhost:8000/docs`
- **Documentação Alternativa (ReDoc)**: `http://localhost:8000/redoc`
- **Health Check**: `http://localhost:8000/health`

---

## Documentação da API

### Base URL
```
http://localhost:8000
```

### Autenticação

Todas as rotas protegidas requerem um token JWT no header:
```
Authorization: Bearer {seu_access_token}
```

### Endpoints Principais

#### Autenticação

**Login**
```http
POST /login
Content-Type: application/x-www-form-urlencoded

username=usuario@example.com&password=suasenha
```

Resposta:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

**Registrar Usuário**
```http
POST /register
Content-Type: application/json

{
  "email": "usuario@example.com",
  "username": "NomeUsuario",
  "password": "senha123"
}
```

**Atualizar Token**
```http
POST /refresh
Content-Type: application/json

{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

#### Reconhecimento de Sinais

**Enviar Vídeo para Reconhecimento**
```http
POST /check_action
Authorization: Bearer {access_token}
Content-Type: multipart/form-data

expected_action: obrigado
video: @video_sinal.mp4
```

Resposta:
```json
{
  "jobId": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending"
}
```

**Obter Resultado do Reconhecimento**
```http
GET /results/{job_id}?wait=true
Authorization: Bearer {access_token}
```

Resposta:
```json
{
  "action_found": true,
  "predicted_action": "obrigado",
  "confidence": "99.10%",
  "expected_action": "obrigado",
  "is_match": true
}
```

#### Usuário

**Obter Perfil do Usuário**
```http
GET /users/me
Authorization: Bearer {access_token}
```

Resposta:
```json
{
  "id": 1,
  "email": "usuario@example.com",
  "username": "NomeUsuario",
  "points": 150,
  "signs_count": 15
}
```

**Obter Sinais Conhecidos**
```http
GET /users/me/signs
Authorization: Bearer {access_token}
```

**Adicionar Sinal Conhecido**
```http
POST /users/me/signs/{sign_id}
Authorization: Bearer {access_token}
```

**Obter Módulos Concluídos**
```http
GET /users/me/modules
Authorization: Bearer {access_token}
```

**Marcar Módulo como Concluído**
```http
POST /users/me/modules/{module_id}
Authorization: Bearer {access_token}
```

#### Ranking e Módulos

**Obter Ranking (Leaderboard)**
```http
GET /leaderboard
```

Resposta:
```json
[
  {
    "id": 1,
    "username": "MelhorAprendiz",
    "points": 500,
    "signs_count": 50
  }
]
```

**Obter Módulo por Nome**
```http
GET /get_module/{nome_modulo}
Authorization: Bearer {access_token}
```

---

## Arquitetura

### Stack Tecnológico

| Componente | Tecnologia |
|-----------|-----------|
| **Framework** | FastAPI 0.115.4 |
| **Linguagem** | Python 3.11 |
| **IA/ML** | TensorFlow, MediaPipe |
| **Banco de Dados** | PostgreSQL (async via asyncpg) |
| **ORM** | SQLAlchemy 2.0 (async) |
| **Fila de Mensagens** | RabbitMQ (aio-pika) |
| **Autenticação** | JWT (python-jose), OAuth2 |
| **Servidor** | Gunicorn + Uvicorn workers |
| **Containerização** | Docker |

### Estrutura do Projeto

```
klibras-api/
├── app/
│   ├── main.py                 # Ponto de entrada da aplicação
│   ├── core/
│   │   ├── config.py          # Gerenciamento de configuração
│   │   └── security.py        # Autenticação e segurança
│   ├── routers/
│   │   ├── user.py            # Endpoints de usuário
│   │   └── recognition.py     # Endpoints de reconhecimento
│   ├── services/
│   │   ├── user_service.py    # Lógica de negócio de usuários
│   │   └── recognition_service.py  # Lógica de processamento IA
│   ├── models/                # Modelos SQLAlchemy
│   ├── schemas/               # Schemas Pydantic
│   ├── db/
│   │   ├── database_connection.py
│   │   └── initial_data.py    # Seed do banco de dados
│   └── dependencies.py        # Injeção de dependências
├── alembic/                   # Migrações do banco de dados
├── requirements.txt           # Dependências Python
├── Dockerfile                 # Configuração Docker
├── docker-compose.yml         # Orquestração de containers
└── alembic.ini               # Configuração Alembic
```

### Fluxo do Sistema

1. **Cliente** envia requisição HTTP para a API
2. **FastAPI** valida autenticação JWT
3. Para vídeos: enviado para **RabbitMQ Queue**
4. **Recognition Service** processa o vídeo:
   - Extrai features com **MediaPipe**
   - Faz predição com modelo **TensorFlow**
5. Resultado salvo no **PostgreSQL**
6. Cliente consulta resultado via endpoint

---

## Desenvolvimento Local

### Sem Docker

```bash
# Criar ambiente virtual
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Instalar dependências
pip install -r requirements.txt

# Configurar banco de dados
alembic upgrade head

# Executar servidor de desenvolvimento
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Migrações do Banco de Dados

```bash
# Criar nova migração
alembic revision --autogenerate -m "Descrição da mudança"

# Aplicar migrações
alembic upgrade head

# Reverter última migração
alembic downgrade -1
```

---

## Testes

```bash
# Executar testes
pytest

# Com cobertura
pytest --cov=app --cov-report=html

# Teste específico
pytest tests/test_user.py -v
```

---

## Deploy em Produção

### Build da Imagem

```bash
docker build -t klibras-api:latest .
```

### Executar em Produção

```bash
docker run -d \
  -p 8000:8000 \
  -e DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db \
  -e SECRET_KEY=sua-chave-secreta \
  -e RABBITMQ_URL=amqp://user:pass@host:5672/ \
  --name klibras-api \
  klibras-api:latest
```

### Health Check

```bash
curl http://localhost:8000/health
# Resposta: {"status": "ok"}
```

---

## Contribuindo

Contribuições são bem-vindas! Por favor, siga estes passos:

1. Faça fork do repositório
2. Crie uma branch para sua feature (`git checkout -b feature/nova-funcionalidade`)
3. Commit suas mudanças (`git commit -m 'Adiciona nova funcionalidade'`)
4. Push para a branch (`git push origin feature/nova-funcionalidade`)
5. Abra um Pull Request

### Diretrizes de Desenvolvimento

- Siga o guia de estilo PEP 8
- Escreva testes unitários para novas funcionalidades
- Atualize a documentação conforme necessário
- Use type hints em todas as funções
- Execute formatadores antes de commitar:

```bash
# Formatar código
black app/

# Lint
flake8 app/

# Type checking
mypy app/
```

---

## Licença

Este projeto está licenciado sob a Licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.

---

## Suporte

- **Issues**: [GitHub Issues](https://github.com/KLibras/klibras-api/issues)
- **Discussões**: [GitHub Discussions](https://github.com/KLibras/klibras-api/discussions)

---

<div align="center">

**Feito para a comunidade brasileira de Linguagem de Sinais**

[Reportar Bug](https://github.com/KLibras/klibras-api/issues) • [Solicitar Funcionalidade](https://github.com/KLibras/klibras-api/issues)

</div>