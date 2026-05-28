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
    app_env: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Ambiente de execução. Controla logs, HSTS, etc.",
    )
    app_name: str = Field(default="CloudTask AI SaaS")
    app_port: int = Field(default=8000, ge=1, le=65535)
    log_level: str = Field(default="INFO")

    # Chave usada para assinar tokens/sessões no futuro. Em produção, gere com
    # `python -c "import secrets; print(secrets.token_urlsafe(32))"`.
    secret_key: str = Field(default="change-me-please")

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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # ignora variáveis extras do ambiente (ex.: PATH)
    )

    @field_validator("trusted_hosts", mode="before")
    @classmethod
    def _split_hosts(cls, value: object) -> object:
        """Aceita TRUSTED_HOSTS como CSV no .env (ex.: "api.exemplo.com,localhost").

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
