import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.db.database_connection import Base
from app.dependencies import get_db


SQLALCHEMY_DATABASE_URL = "" # Mudar url para teste
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close() # type: ignore

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


def test_register_user():
    """
    Teste de registro
    """
    response = client.post(
        "/register",
        json={"email": "klibras@klibras.com", "username": "klibras", "password": "klibras", "role": "user"},
    )
    assert response.status_code == 201
    assert response.json()["email"] == "klibras@klibras.com"
    assert response.json()["username"] == "klibras"

def test_register_existing_user():
    """
    Teste de registro com um email existente
    """
    response = client.post(
        "/register",
        json={"email": "klibras@klibras.com", "username": "klibras", "password": "klibras", "role": "user"},
    )
    assert response.status_code == 400

def test_login():
    """
    Teste de login com credencial válidos
    """
    response = client.post(
        "/login",
        data={"username": "klibras@klibras.com", "password": "klibras"},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert "refresh_token" in response.json()
    assert response.json()["token_type"] == "bearer"

def test_login_invalid_credentials():
    """
    Teste de login com credenciais inválidas
    """
    response = client.post(
        "/login",
        data={"username": "klibras@klibras.com", "password": "senhaerrada"},
    )
    assert response.status_code == 401

def test_get_current_user():
    """
    Teste tenta obter o usuário que está logado atualmente
    """
    login_response = client.post(
        "/login",
        data={"username": "klibras@klibras.com", "password": "klibras"},
    )
    access_token = login_response.json()["access_token"]
    response = client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 200
    assert response.json()["email"] == "klibras@klibras.com"

def test_refresh_token():
    """
    Teste para tentar fazer o refresh do token
    """
    login_response = client.post(
        "/login",
        data={"username": "klibras@klibras.com", "password": "klibras"},
    )
    refresh_token = login_response.json()["refresh_token"]
    response = client.post(
        "/refresh",
        json={"refresh_token": refresh_token},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


def teardown_module(module):
    """
    Limpa o bd de teste depois do teste
    """
    Base.metadata.drop_all(bind=engine)