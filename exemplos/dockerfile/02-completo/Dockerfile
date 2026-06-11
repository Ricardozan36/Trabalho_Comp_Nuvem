# =============================================================================
# Dockerfile didático — versão "completa e comentada"
# -----------------------------------------------------------------------------
# Mostra as técnicas mais usadas em Dockerfiles de aplicações Python/FastAPI:
#   - Multi-stage build (imagem final mais leve, sem ferramentas de build).
#   - Cache de dependências (camadas separadas para requirements e código).
#   - Usuário não-root (boa prática de segurança).
#   - Variáveis de ambiente úteis ao Python.
#   - HEALTHCHECK nativo do Docker.
#   - ENTRYPOINT + CMD (mais flexível que CMD sozinho).
# =============================================================================


# -----------------------------------------------------------------------------
# Stage 1: builder
# -----------------------------------------------------------------------------
# Usamos uma imagem maior só durante o build (tem compilador C, gcc, etc.)
# para instalar pacotes Python que precisam compilar dependências nativas
# (ex.: psycopg2, cryptography).
# -----------------------------------------------------------------------------
FROM public.ecr.aws/docker/library/python:3.11-slim AS builder

# Pasta-padrão dentro do container.
WORKDIR /build

# ARG = variável só de build, pode ser sobrescrita com --build-arg.
ARG PIP_DISABLE_PIP_VERSION_CHECK=1

# Instala dependências de sistema necessárias para compilar pacotes Python.
# `--no-install-recommends` evita instalar pacotes "sugeridos" desnecessários.
# `rm -rf /var/lib/apt/lists/*` enxuga a camada.
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential \
 && rm -rf /var/lib/apt/lists/*

# Copia só o requirements.txt PRIMEIRO. Isso aproveita o cache do Docker:
# enquanto requirements.txt não mudar, esta camada (com pip install) é
# reaproveitada — builds ficam muito mais rápidos.
COPY requirements.txt .

# `--user` instala os pacotes em /root/.local, fácil de copiar depois para
# o stage final sem trazer todo o pip + caches do sistema.
RUN pip install --no-cache-dir --user -r requirements.txt


# -----------------------------------------------------------------------------
# Stage 2: runtime (final)
# -----------------------------------------------------------------------------
# Imagem final fica enxuta: só Python + nosso código + libs já instaladas.
# -----------------------------------------------------------------------------
FROM public.ecr.aws/docker/library/python:3.11-slim AS runtime

# ----- variáveis de ambiente úteis ao Python ---------------------------------
# PYTHONDONTWRITEBYTECODE=1 → não cria arquivos .pyc no container.
# PYTHONUNBUFFERED=1        → logs do Python saem na hora (importante p/ Docker).
# PATH                      → garante que executáveis instalados via --user funcionem.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/home/appuser/.local/bin:${PATH}"

# ----- cria usuário não-root -------------------------------------------------
# Rodar como root dentro do container é risco de segurança. Criamos um usuário
# dedicado com UID/GID fixos para facilitar permissões em volumes montados.
RUN groupadd --system --gid 1001 appgroup \
 && useradd  --system --uid 1001 --gid appgroup --home /home/appuser appuser \
 && mkdir -p /home/appuser/.local \
 && chown -R appuser:appgroup /home/appuser

WORKDIR /app

# Copia as libs Python instaladas no stage builder para a home do usuário final.
COPY --from=builder --chown=appuser:appgroup /root/.local /home/appuser/.local

# Copia o código da aplicação. Use um .dockerignore robusto para não trazer
# .git, .venv, __pycache__, .env, etc.
COPY --chown=appuser:appgroup . .

# Troca para o usuário não-root.
USER appuser

# Porta exposta (documentação; ainda precisa de -p ao rodar).
EXPOSE 8000

# HEALTHCHECK nativo do Docker. O Docker marca o container como "unhealthy"
# se o comando falhar repetidas vezes. Útil em orquestradores que olham status.
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request,sys; \
      sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health').status == 200 else 1)"

# ENTRYPOINT define o "executável fixo" do container.
# CMD define os argumentos padrão — podem ser sobrescritos no `docker run ... <args>`.
ENTRYPOINT ["uvicorn"]
CMD ["app.main:app", "--host", "0.0.0.0", "--port", "8000"]
