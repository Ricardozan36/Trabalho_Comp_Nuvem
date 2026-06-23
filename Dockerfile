# ---------- Estágio comum: runtime mínimo ----------------------------------
FROM public.ecr.aws/docker/library/python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/home/appuser/.local/bin:${PATH}" \
    APP_PORT=8000

RUN apt-get update \
 && apt-get install -y --no-install-recommends tini \
 && rm -rf /var/lib/apt/lists/* \
 && groupadd --system --gid 1001 appuser \
 && useradd  --system --uid 1001 --gid appuser --home /home/appuser appuser \
 && mkdir -p /app /home/appuser/.local \
 && chown -R appuser:appuser /app /home/appuser

WORKDIR /app
ENTRYPOINT ["/usr/bin/tini", "--"]

# ---------- Builders: instalam dependências --------------------
FROM base AS builder-prod
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM builder-prod AS builder-test
COPY requirements-test.txt .
RUN pip install --no-cache-dir --user -r requirements-test.txt

FROM builder-test AS builder-dev
COPY requirements-dev.txt .
RUN pip install --no-cache-dir --user -r requirements-dev.txt

# ---------- Target final: PROD ---------------------------------------------
FROM base AS prod

COPY --from=builder-prod --chown=appuser:appuser /root/.local /home/appuser/.local

# 1. Copia o código e configurações (inclui app/ e static/)
COPY --chown=appuser:appuser . .

# 2. Copia EXPLICITAMENTE a pasta static para garantir que ela existe no destino
COPY --chown=appuser:appuser ./static/ /app/static/

USER appuser
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; \
     sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health').status == 200 else 1)"

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${APP_PORT} --proxy-headers --forwarded-allow-ips='*'"]

# ---------- Target final: TEST ---------------------------------------------
FROM base AS test
COPY --from=builder-test --chown=appuser:appuser /root/.local /home/appuser/.local
COPY --chown=appuser:appuser . .
USER appuser
CMD ["pytest", "-q"]

# ---------- Target final: DEV ----------------------------------------------
FROM base AS dev
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      sudo nodejs npm \
      postgresql-client netcat-openbsd iputils-ping \
 && rm -rf /var/lib/apt/lists/* \
 && echo "appuser ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/appuser \
 && chmod 0440 /etc/sudoers.d/appuser

COPY --from=builder-dev --chown=appuser:appuser /root/.local /home/appuser/.local
COPY --chown=appuser:appuser . .

USER appuser
EXPOSE 8000 5678

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${APP_PORT} --reload --proxy-headers --forwarded-allow-ips='*'"]