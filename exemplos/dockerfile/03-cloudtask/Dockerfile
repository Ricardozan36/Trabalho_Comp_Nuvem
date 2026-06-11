# =============================================================================
# Dockerfile — CloudTask AI SaaS (versão pronta para a Aula 2 / 3)
# -----------------------------------------------------------------------------
# Aplica boas práticas do exemplo "02-completo" e já está calibrado para a
# estrutura real do projeto (app/main.py + app/db, app/api, app/core, ...).
# Inclui dependências de sistema para PostgreSQL (psycopg2 binário cobre,
# mas deixamos libpq instalado para futuros casos com SQLAlchemy + asyncpg).
# =============================================================================


# ----- Stage 1: builder ------------------------------------------------------
FROM public.ecr.aws/docker/library/python:3.11-slim AS builder

WORKDIR /build

# Dependências de compilação (necessárias se trocar psycopg2-binary por psycopg2).
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential libpq-dev \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt


# ----- Stage 2: runtime ------------------------------------------------------
FROM public.ecr.aws/docker/library/python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/home/appuser/.local/bin:${PATH}" \
    APP_PORT=8000

# libpq5 é a runtime do PostgreSQL (necessária para psycopg2/asyncpg falarem com o DB).
RUN apt-get update \
 && apt-get install -y --no-install-recommends libpq5 \
 && rm -rf /var/lib/apt/lists/* \
 && groupadd --system --gid 1001 appgroup \
 && useradd  --system --uid 1001 --gid appgroup --home /home/appuser appuser \
 && mkdir -p /home/appuser/.local /app/local_uploads /app/local_events \
 && chown -R appuser:appgroup /home/appuser /app

WORKDIR /app

COPY --from=builder --chown=appuser:appgroup /root/.local /home/appuser/.local
COPY --chown=appuser:appgroup . .

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; \
      sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health').status == 200 else 1)"

# A porta vem da variável APP_PORT (definida no .env / docker-compose).
# `sh -c` permite expandir a variável no momento de iniciar.
ENTRYPOINT ["sh", "-c"]
CMD ["uvicorn app.main:app --host 0.0.0.0 --port ${APP_PORT}"]
