from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, EmailStr

# --- Schemas de Uso Geral ---
class HealthResponse(BaseModel):
    status: Literal["ok"] = Field(default="ok")
    model_config = ConfigDict(json_schema_extra={"examples": [{"status": "ok"}]})

class UploadResponse(BaseModel):
    filename: str
    url: str
    storage_mode: Literal["local", "s3"]

class DownloadUrlResponse(BaseModel):
    url: str
    expires_in: int | None = None
    storage_mode: Literal["local", "s3"]

class ReadyResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    db: Literal["ok", "down"]

class RootResponse(BaseModel):
    name: str
    version: str
    docs: str

# --- Schemas de Usuário e Tarefas ---
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str = Field(..., min_length=6)

class TaskCreate(BaseModel):
    title: str
    priority: str

class TaskUpdate(BaseModel):
    status: str

class TaskEdit(BaseModel):
    title: str
    priority: str