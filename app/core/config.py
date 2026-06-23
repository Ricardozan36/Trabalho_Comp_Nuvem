"""
Configuração central da aplicação, lida de variáveis de ambiente.

POR QUÊ um módulo de config (e não `os.getenv` espalhado pelo código):
    * Um único lugar valida e documenta TODAS as configurações.
    * O Pydantic converte tipos automaticamente (ex.: a string "true" do .env
      vira o booleano ``True``) e recusa valores inválidos no startup.
    * Nada de senha/segredo hardcoded — tudo vem do ambiente (.env local,
      Secret no Kubernetes em produção).

Como funciona:
    * :class:`Settings` lê, nesta ordem de prioridade:
        1. variáveis de ambiente do processo (ex.: as injetadas pelo Compose);
        2. o arquivo ``.env`` (apenas em desenvolvimento);
        3. os defaults definidos aqui.
    * :data:`settings` é uma instância única, importada por todo o app.

RISCO/CUIDADO:
    * O ``.env`` NUNCA é versionado (está no .gitignore). Só o ``.env.example``.
    * Em produção, ``SECRET_KEY`` e ``DATABASE_URL`` vêm de um Secret, não do .env.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações da aplicação (validadas pelo Pydantic).

    Cada atributo corresponde a uma variável de ambiente de mesmo nome em
    MAIÚSCULAS (ex.: ``app_env`` <- ``APP_ENV``). Os defaults permitem rodar
    em desenvolvimento sem configurar nada.
    """

    # --- Aplicação ---------------------------------------------------------
    app_env: Literal["development", "test", "staging", "production"] = Field(
        default="development",
        description="Ambiente de execução. Controla logs, HSTS, etc.",
    )
    app_name: str = Field(default="CloudTask AI SaaS")
    app_port: int = Field(default=8000, ge=1, le=65535)
    log_level: str = Field(default="INFO")

    # Chave usada para assinar os tokens JWT do login (Aula 12). Em produção,
    # gere com `python -c "import secrets; print(secrets.token_urlsafe(32))"`.
    secret_key: str = Field(default="change-me-please")

    # --- Autenticação (Aula 12) -------------------------------------------
    # Conta administrativa única da demo. O login (`POST /auth/login`) confere
    # estas credenciais e devolve um token JWT; as rotas de dados (/tasks,
    # /uploads, /events) exigem esse token. DEMO: senha fixa `admin#123` em
    # tudo (app, API, banco, servidores). Em produção: nunca senha fixa/no .env;
    # use um provedor de identidade (Cognito/OAuth) e segredos rotativos.
    admin_username: str = Field(default="admin")
    admin_password: str = Field(default="admin#123")
    # Validade do token em minutos.
    jwt_expire_minutes: int = Field(default=480)

    # --- Banco de dados ----------------------------------------------------
    # Mesmo formato local e no Amazon RDS — só muda o host/usuário/senha.
    database_url: str = Field(
        default="postgresql+psycopg2://cloudtask:cloudtask@db:5432/cloudtask",
    )

    # --- HTTPS / segurança de transporte -----------------------------------
    # force_https: liga o cabeçalho HSTS (e, se NÃO estiver atrás de proxy,
    #   também o redirect HTTP->HTTPS no próprio app).
    force_https: bool = Field(
        default=False,
        description="Em produção (atrás de ALB/HTTPS) deve ser true.",
    )
    # behind_proxy: indica que há um proxy/ALB na frente terminando o TLS.
    #   Quando true, o REDIRECT é responsabilidade do ALB, não do app.
    #   POR QUÊ: se o app também redirecionasse, as health probes internas
    #   (que chegam em HTTP) entrariam em loop -> pod marcado "unhealthy".
    behind_proxy: bool = Field(default=True)
    # --- Storage / Uploads (Aula 5 em diante) -------------------------------
    # `local`: salva arquivos em disco (LOCAL_UPLOADS_DIR).
    # `s3`   : envia para o bucket S3 configurado.
    # POR QUÊ permitir os dois modos: o aluno consegue completar a aula SEM AWS
    # (modo local) e só liga o S3 quando tiver as credenciais do Learner Lab.
    storage_mode: Literal["local", "s3"] = Field(default="local")
    local_uploads_dir: str = Field(default="./local_uploads")

    # Quando `storage_mode=s3`:
    aws_region: str = Field(default="us-east-1")
    s3_bucket_name: str = Field(default="cloudtask-ai-saas-uploads")
    # Endpoint customizado, útil para LocalStack (não usado no curso). Vazio = AWS real.
    s3_endpoint_url: str = Field(default="")
    # URL pré-assinada: tempo de validade (segundos) do link de download.
    s3_presigned_url_expires: int = Field(default=900, ge=60, le=86400)

    # --- Event store / logs (Aula 10 em diante) ----------------------------
    # `local`   : grava os eventos num arquivo JSON (LOCAL_EVENTS_FILE).
    # `dynamodb`: grava no Amazon DynamoDB (tabela DYNAMODB_TABLE_NAME).
    # POR QUÊ os dois modos (igual ao storage): o aluno completa a Aula 10 SEM
    # AWS (modo local) e liga o DynamoDB só quando tiver credenciais.
    event_store_mode: Literal["local", "dynamodb"] = Field(default="local")
    local_events_file: str = Field(default="./local_events/events.json")

    # Quando `event_store_mode=dynamodb`:
    dynamodb_table_name: str = Field(default="cloudtask-events")
    # Endpoint customizado p/ DynamoDB Local (Docker). Vazio = DynamoDB na AWS.
    dynamodb_endpoint_url: str = Field(default="")

    # Hosts aceitos pelo TrustedHostMiddleware. "*" = qualquer host (dev).
    #   Em produção, liste o domínio real para mitigar Host header spoofing.
    #
    # `Annotated[..., NoDecode]`: por padrão o pydantic-settings tenta fazer
    # JSON-decode do valor de campos do tipo lista (esperaria '["a","b"]').
    # Como no .env escrevemos uma lista SIMPLES separada por vírgula
    # (ex.: TRUSTED_HOSTS=api.exemplo.com,localhost), o JSON falharia em "*".
    # NoDecode desliga esse parse e deixa o nosso validator abaixo dividir o CSV.
    trusted_hosts: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["*"],
    )

    # Origens permitidas no CORS (Aula 12). O frontend roda em OUTRO servidor
    # (origem diferente), então o navegador só deixa ele chamar a API se a API
    # responder com os cabeçalhos CORS certos. Mesmo padrão CSV do trusted_hosts:
    # CORS_ORIGINS=http://meu-front:80,http://localhost:5173  (default "*" = libera
    # geral — ok em demo; em produção liste os domínios reais).
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["*"],
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # ignora variáveis extras do ambiente (ex.: PATH)
    )

    @field_validator("trusted_hosts", "cors_origins", mode="before")
    @classmethod
    def _split_hosts(cls, value: object) -> object:
        """Aceita TRUSTED_HOSTS / CORS_ORIGINS como CSV no .env.

        O .env só guarda texto; aqui transformamos "a,b,c" na lista ["a","b","c"].
        """
        if isinstance(value, str):
            return [h.strip() for h in value.split(",") if h.strip()]
        return value

    @property
    def is_production(self) -> bool:
        """Atalho legível para checar se estamos em produção."""
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    """Retorna a instância única de :class:`Settings` (cacheada).

    POR QUÊ ``lru_cache``: lê o ambiente/.env UMA vez e reutiliza, em vez de
    reconstruir a cada importação. Também facilita sobrescrever em testes.
    """
    return Settings()


# Instância global importada pelo restante da aplicação.
settings: Settings = get_settings()
