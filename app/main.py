from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pydantic_settings import BaseSettings
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker, Session
import boto3
import os

# ==========================================
# 1. Configurações (Ajustadas para K8s / ConfigMap / Secret)
# ==========================================
class Settings(BaseSettings):
    # Pode receber a URL inteira (via .env local) ou os pedaços (via K8s)
    database_url: str | None = None
    postgres_user: str | None = "cloudtask"
    postgres_password: str | None = "cloudtask"
    postgres_host: str | None = "postgres" # Nome do serviço no K8s
    postgres_port: str | None = "5432"
    postgres_db: str | None = "cloudtask"

    storage_mode: str = "local"
    local_uploads_dir: str = "./local_uploads"
    aws_region: str = "us-east-1"
    s3_bucket_name: str = "cloudtask-ai-saas-uploads"
    
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None

    class Config:
        env_file = ".env"
        extra = "ignore"

    @property
    def get_db_url(self) -> str:
        # Se recebeu a URL completa, usa ela. Se não, monta com as variáveis do K8s
        if self.database_url:
            return self.database_url
        return f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"


settings = Settings()

# ==========================================
# 2. Configuração do Banco de Dados
# ==========================================
engine = create_engine(settings.get_db_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class TaskDB(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    priority = Column(String)
    status = Column(String, default="pending")

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==========================================
# 3. Modelos Pydantic
# ==========================================
class TaskCreate(BaseModel):
    title: str
    priority: str
    status: str

class TaskUpdate(BaseModel):
    status: str

class TaskResponse(BaseModel):
    id: int
    title: str
    priority: str
    status: str

    class Config:
        from_attributes = True

# ==========================================
# 4. Inicialização do FastAPI
# ==========================================
app = FastAPI(title="CloudTask AI SaaS")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Rotas de Health Check exigidas pelo K8s ===

@app.get("/health")
def liveness_probe():
    """Usado pelo K8s para saber se o container travou"""
    return {"status": "alive"}

@app.get("/health/ready")
def readiness_probe():
    """Usado pelo K8s para saber se pode mandar tráfego de usuários para cá"""
    # Se chegamos aqui, é porque a API e o SQLAlchemy carregaram
    return {"status": "ready"}

# ==========================================
# 5. Rotas da API
# ==========================================
@app.get("/tasks", response_model=list[TaskResponse])
def get_tasks(db: Session = Depends(get_db)):
    return db.query(TaskDB).all()

@app.post("/tasks", response_model=TaskResponse)
def create_task(task: TaskCreate, db: Session = Depends(get_db)):
    db_task = TaskDB(title=task.title, priority=task.priority, status=task.status)
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

@app.put("/tasks/{task_id}", response_model=TaskResponse)
def update_task(task_id: int, task_update: TaskUpdate, db: Session = Depends(get_db)):
    db_task = db.query(TaskDB).filter(TaskDB.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    
    db_task.status = task_update.status
    db.commit()
    db.refresh(db_task)
    return db_task

@app.post("/uploads/")
async def upload_file(file: UploadFile = File(...)):
    if settings.storage_mode == "s3":
        try:
            s3_client = boto3.client(
                's3',
                region_name=settings.aws_region,
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key
            )
            s3_client.upload_fileobj(file.file, settings.s3_bucket_name, file.filename)
            return {"filename": file.filename, "message": f"Upload realizado com sucesso para o bucket {settings.s3_bucket_name}!"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erro ao enviar para S3: {str(e)}")
    else:
        os.makedirs(settings.local_uploads_dir, exist_ok=True)
        file_location = os.path.join(settings.local_uploads_dir, file.filename)
        with open(file_location, "wb+") as file_object:
            file_object.write(file.file.read())
        return {"filename": file.filename, "message": "Upload salvo localmente."}