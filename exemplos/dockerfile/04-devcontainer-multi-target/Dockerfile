# =============================================================================
# Dockerfile multi-target — dev / test / prod
# -----------------------------------------------------------------------------
# Mesmo Dockerfile gera 3 imagens diferentes via `--target`:
#
#   docker build --target prod -t cloudtask-api:prod .
#   docker build --target test -t cloudtask-api:test .
#   docker build --target dev  -t cloudtask-api:dev  .
#
# Estratégia:
#   - `base`        : runtime mínimo (Python + libpq5 + usuário não-root).
#   - `builder-*`   : instalam dependências (prod, test, dev) em /root/.local
#                     usando build-essential que NÃO sai do estágio final.
#   - `prod`        : código copiado, sem ferramentas de teste/dev. É essa
#                     imagem que vai para o ECR e roda no EKS.
#   - `test`        : prod + libs de teste + pasta tests/. Usada no CI.
#   - `dev`         : test + libs de dev (debugpy, ipdb, ruff, etc.).
#                     NÃO copia o código: ele vem por volume montado pelo
#                     docker-compose.dev.yml / devcontainer.
# =============================================================================


# ---------- Estágio comum: runtime base ---------------------------------------
FROM public.ecr.aws/docker/library/python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/home/appuser/.local/bin:${PATH}" \
    APP_PORT=8000

# libpq5 é a runtime do PostgreSQL (psycopg2/asyncpg precisam dela).
# tini cuida de PID 1 / sinais — importante para Kubernetes encerrar pods bem.
RUN apt-get update \
 && apt-get install -y --no-install-recommends libpq5 tini \
 && rm -rf /var/lib/apt/lists/* \
 && groupadd --system --gid 1001 appgroup \
 && useradd  --system --uid 1001 --gid appgroup --home /home/appuser appuser \
 && mkdir -p /app /home/appuser/.local \
 && chown -R appuser:appgroup /app /home/appuser

WORKDIR /app


# ---------- Builders ---------------------------------------------------------
# Esses estágios instalam dependências em /root/.local.
# As ferramentas de compilação (build-essential, libpq-dev) ficam aqui e
# NÃO entram nas imagens finais (a final só faz COPY --from de /root/.local).
# -----------------------------------------------------------------------------
FROM base AS builder-prod
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential libpq-dev \
 && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM builder-prod AS builder-test
COPY requirements-test.txt .
RUN pip install --no-cache-dir --user -r requirements-test.txt

FROM builder-test AS builder-dev
COPY requirements-dev.txt .
RUN pip install --no-cache-dir --user -r requirements-dev.txt


# ---------- Target final: PROD ----------------------------------------------
# Imagem enxuta, sem ferramentas de teste/dev. É a que vai para o ECR / EKS.
# -----------------------------------------------------------------------------
FROM base AS prod

# Copia apenas as libs de produção (instaladas em /root/.local pelo builder).
COPY --from=builder-prod --chown=appuser:appgroup /root/.local /home/appuser/.local

# Copia somente o código necessário em produção.
COPY --chown=appuser:appgroup app/ /app/app/

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; \
      sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health').status == 200 else 1)"

# tini como init garante shutdown limpo e propagação correta de SIGTERM
# (essencial para o Kubernetes terminar pods sem deixar zumbis).
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${APP_PORT}"]


# ---------- Target final: TEST ----------------------------------------------
# Adiciona libs de teste e a pasta tests/. Usada pelo GitHub Actions.
# -----------------------------------------------------------------------------
FROM base AS test

COPY --from=builder-test --chown=appuser:appgroup /root/.local /home/appuser/.local
COPY --chown=appuser:appgroup app/   /app/app/
COPY --chown=appuser:appgroup tests/ /app/tests/

USER appuser

# Comando padrão: rodar a suíte. CI sobrescreve se quiser flags diferentes.
CMD ["pytest", "-q", "--maxfail=1", "--disable-warnings"]


# ---------- Target final: DEV -----------------------------------------------
# Inclui libs de dev (debugpy, ipdb, ruff...) MAS NÃO copia o código —
# ele será montado via volume pelo docker-compose.dev.yml ou devcontainer.
# Isso permite hot-reload (uvicorn --reload) e debug interativo no VS Code.
# -----------------------------------------------------------------------------
FROM base AS dev

COPY --from=builder-dev --chown=appuser:appgroup /root/.local /home/appuser/.local

USER appuser

# Porta extra para debugpy (debugger remoto do VS Code).
EXPOSE 5678 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${APP_PORT} --reload"]
