import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app, get_db, Base
from app.schemas import UserCreate

# --- Configuração do Banco de Dados em Memória para Testes ---
# Usamos SQLite em memória para testes para não sujar o seu banco de dados principal (PostgreSQL)
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Sobrescreve a dependência do banco de dados para usar o banco de teste
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

# Cria as tabelas no banco de teste antes de iniciar os testes
Base.metadata.create_all(bind=engine)

# Inicia o cliente de teste
client = TestClient(app)


# --- Os Casos de Teste ---

def test_health_check():
    """Testa se a API está viva (Liveness)"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_readiness_check():
    """Testa se a conexão com o banco de dados (neste caso, o banco de teste) está funcionando"""
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "db": "ok"}

def test_create_user():
    """Testa a criação de um novo usuário via Signup"""
    response = client.post(
        "/signup",
        json={"username": "testuser", "email": "test@example.com", "password": "testpassword123"}
    )
    assert response.status_code == 200
    assert response.json() == {"message": "Usuário criado com sucesso"}

def test_create_existing_user():
    """Testa a regra de negócio que impede e-mails duplicados"""
    # Tenta criar o mesmo usuário novamente
    response = client.post(
        "/signup",
        json={"username": "testuser", "email": "test@example.com", "password": "testpassword123"}
    )
    assert response.status_code == 400
    assert response.json() == {"detail": "Email já cadastrado"}

def test_login_success():
    """Testa o login com credenciais válidas"""
    response = client.post(
        "/token",
        data={"username": "test@example.com", "password": "testpassword123"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"

def test_login_failure():
    """Testa o login com senha incorreta"""
    response = client.post(
        "/token",
        data={"username": "test@example.com", "password": "wrongpassword"}
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "Email ou senha incorretos"}

# Limpa o banco de testes após a execução (opcional, mas recomendado)
@pytest.fixture(autouse=True, scope="session")
def teardown():
    yield
    import os
    if os.path.exists("./test.db"):
        os.remove("./test.db")