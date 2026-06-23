import os
import uuid
import logging
import traceback
import shutil
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, status, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import create_engine, Column, Integer, String, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from passlib.context import CryptContext
from jose import jwt, JWTError

# Importação dos seus schemas
from app.schemas import (
    UserCreate, TaskCreate, TaskUpdate, 
    HealthResponse, UploadResponse, ReadyResponse
)

# ==========================================
# 1. Configurações e Variáveis de Ambiente
# ==========================================
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")
    
    database_url: Optional[str] = None
    postgres_user: str = "cloudtask"
    postgres_password: str = "cloudtask"
    postgres_host: str = "postgres"
    postgres_port: str = "5432"
    postgres_db: str = "cloudtask"
    
    secret_key: str = "uma_chave_secreta_muito_segura"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    storage_mode: str = "local" # ou "s3"
    local_uploads_dir: str = "uploads_dir"
    aws_region: str = "us-east-1"
    s3_bucket_name: Optional[str] = None

    @property
    def get_db_url(self) -> str:
        if self.database_url: return self.database_url
        return f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

settings = Settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# ==========================================
# 2. Banco de Dados e Segurança
# ==========================================
engine = create_engine(settings.get_db_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class UserDB(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)

class TaskDB(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    priority = Column(String)
    status = Column(String, default="pending")

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

def get_password_hash(password):
    return pwd_context.hash(password[:72])

# ==========================================
# 3. App e Middleware
# ==========================================
app = FastAPI(title="CloudTask AI SaaS")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 4. Rotas da API
# ==========================================

@app.get("/health", response_model=HealthResponse)
def health_check(): return {"status": "ok"}

@app.get("/health/ready", response_model=ReadyResponse)
def readiness_check(response: Response, db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ready", "db": "ok"}
    except Exception:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "not_ready", "db": "down"}

@app.post("/signup")
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    if db.query(UserDB).filter(UserDB.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email já cadastrado")
    new_user = UserDB(email=user.email, hashed_password=get_password_hash(user.password))
    db.add(new_user)
    db.commit()
    return {"message": "Usuário criado com sucesso"}

@app.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(UserDB).filter(UserDB.email == form_data.username).first()
    if not user or not pwd_context.verify(form_data.password[:72], user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")
    
    expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    token = jwt.encode({"sub": user.email, "exp": expire}, settings.secret_key, algorithm=settings.algorithm)
    return {"access_token": token, "token_type": "bearer"}

@app.get("/tasks")
def get_tasks(db: Session = Depends(get_db)): 
    return db.query(TaskDB).all()

@app.post("/tasks")
def create_task(task: TaskCreate, db: Session = Depends(get_db)):
    db_task = TaskDB(**task.model_dump())
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

@app.post("/uploads", response_model=UploadResponse)
def create_upload(file: UploadFile = File(...)):
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4().hex}{file_extension}"
    
    if settings.storage_mode == "local":
        file_path = os.path.join(settings.local_uploads_dir, unique_filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return UploadResponse(filename=unique_filename, url=f"/uploads_static/{unique_filename}", storage_mode="local")
    
    elif settings.storage_mode == "s3":
        import boto3
        try:
            s3_client = boto3.client('s3', region_name=settings.aws_region)
            s3_client.upload_fileobj(file.file, settings.s3_bucket_name, unique_filename)
            return UploadResponse(filename=unique_filename, url=f"https://{settings.s3_bucket_name}.s3.amazonaws.com/{unique_filename}", storage_mode="s3")
        except Exception as e:
            logging.error(f"Erro S3: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=str(e))
    
    raise HTTPException(status_code=500, detail="Modo de armazenamento inválido")

# ==========================================
# 5. Montagem do Frontend (STATIC)
# ==========================================
# 1. Definir caminhos absolutos robustos
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "static")
UPLOADS_DIR = os.path.join(BASE_DIR, settings.local_uploads_dir)

# 2. Garantir que as pastas existem
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)

# 3. Montar uploads
app.mount("/uploads_static", StaticFiles(directory=UPLOADS_DIR), name="uploads_static")

# 4. Montar Frontend (sempre por último)
if os.path.exists(STATIC_DIR):
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
else:
    logging.warning(f"Diretório estático não encontrado em: {STATIC_DIR}")