from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, status, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from pydantic_settings import BaseSettings
from sqlalchemy import create_engine, Column, Integer, String, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta
import shutil
import uuid
import os

# Importações dos seus Schemas
from app.schemas import (
    UserCreate, TaskCreate, TaskUpdate, TaskEdit, 
    HealthResponse, UploadResponse, DownloadUrlResponse, ReadyResponse, RootResponse
)

# ==========================================
# 1. Configurações e Autenticação
# ==========================================
class Settings(BaseSettings):
    database_url: str | None = None
    postgres_user: str | None = "cloudtask"
    postgres_password: str | None = "cloudtask"
    postgres_host: str | None = "postgres"
    postgres_port: str | None = "5432"
    postgres_db: str | None = "cloudtask"
    
    secret_key: str = "uma_chave_secreta_muito_segura_para_desenvolvimento"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Novas configurações para Upload (Local e Futuramente AWS S3)
    storage_mode: str = "local"  # Mude para "s3" quando for para a AWS
    local_uploads_dir: str = "uploads_dir"
    aws_region: str | None = "us-east-1"
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    s3_bucket_name: str | None = None

    @property
    def get_db_url(self) -> str:
        if self.database_url: return self.database_url
        return f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

settings = Settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Configuração do Cadeado (Security)
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

# Validador de Usuário Logado
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(UserDB).filter(UserDB.email == email).first()
    if user is None:
        raise credentials_exception
    return user

# ==========================================
# 3. Inicialização e Rotas
# ==========================================
app = FastAPI(title="CloudTask AI SaaS")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# Prepara o diretório de uploads local e serve os arquivos estáticos
os.makedirs(settings.local_uploads_dir, exist_ok=True)
app.mount("/uploads_static", StaticFiles(directory=settings.local_uploads_dir), name="uploads_static")

# Health Checks
@app.get("/health", response_model=HealthResponse)
def health_check():
    return {"status": "ok"}

@app.get("/health/ready", response_model=ReadyResponse)
def readiness_check(response: Response, db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ready", "db": "ok"}
    except Exception:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "not_ready", "db": "down"}

# Auth
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
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email ou senha incorretos")
    access_token = jwt.encode({"sub": user.email, "exp": datetime.utcnow() + timedelta(minutes=30)}, settings.secret_key, algorithm=settings.algorithm)
    return {"access_token": access_token, "token_type": "bearer"}

# CRUD Tarefas (Desbloqueadas temporariamente para os testes/integração inicial)

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

@app.put("/tasks/{task_id}")
def update_task(task_id: int, task_update: TaskUpdate, db: Session = Depends(get_db)):
    db_task = db.query(TaskDB).filter(TaskDB.id == task_id).first()
    if not db_task: raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    db_task.status = task_update.status
    db.commit()
    return db_task

@app.put("/tasks/{task_id}/edit")
def edit_task(task_id: int, task_edit: TaskEdit, db: Session = Depends(get_db)):
    db_task = db.query(TaskDB).filter(TaskDB.id == task_id).first()
    if not db_task: raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    db_task.title = task_edit.title
    db_task.priority = task_edit.priority
    db.commit()
    return db_task

# ==========================================
# 4. Upload de Arquivos
# ==========================================
@app.post("/uploads", response_model=UploadResponse)
def create_upload(file: UploadFile = File(...)):
    """Recebe um arquivo e armazena (localmente ou no S3)."""
    
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4().hex}{file_extension}"
    
    if settings.storage_mode == "local":
        file_path = os.path.join(settings.local_uploads_dir, unique_filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        return UploadResponse(
            filename=unique_filename,
            url=f"/uploads_static/{unique_filename}",
            storage_mode="local"
        )
    
    elif settings.storage_mode == "s3":
        # Estrutura pronta para a integração Boto3 na Semana 4
        import boto3
        s3_client = boto3.client(
            's3',
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key
        )
        s3_client.upload_fileobj(file.file, settings.s3_bucket_name, unique_filename)
        
        return UploadResponse(
            filename=unique_filename,
            url=f"https://{settings.s3_bucket_name}.s3.amazonaws.com/{unique_filename}",
            storage_mode="s3"
        )