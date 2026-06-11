# =============================================================================
# Dockerfile — CloudTask AI SaaS (Aula 1: dev e prod)
# -----------------------------------------------------------------------------
# Mesmo Dockerfile gera duas imagens via `--target`:
#   - dev  : usado pelo devcontainer do VS Code. Inclui debugpy, ruff, etc.
#            O código é montado por volume → hot-reload.
#   - prod : imagem enxuta para futuro deploy em ECR/EKS. Código embutido.
#
# Comandos:
#   docker build --target dev  -t cloudtask-api:dev  .
#   docker build --target prod -t cloudtask-api:prod .
#
# Em aulas futuras adicionamos um target `test` para o CI.
# =============================================================================


# ---------- Estágio comum: runtime mínimo ----------------------------------
FROM public.ecr.aws/docker/library/python:3.11-slim AS base

# Variáveis úteis ao Python rodando em container.
# PYTHONDONTWRITEBYTECODE → não cria .pyc dentro do container.
# PYTHONUNBUFFERED        → logs do print/loguer aparecem na hora.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/home/appuser/.local/bin:${PATH}" \
    APP_PORT=8000

# tini = init mínimo (PID 1). Garante shutdown limpo no Docker e no Kubernetes.
#
# O GRUPO tem o MESMO nome do usuário (appuser), seguindo a convenção dos
# devcontainers. POR QUÊ: a feature common-utils (que instala o oh-my-zsh)
# roda `chown ${USER}:${USER}` — se o grupo tivesse outro nome, o build
# falharia com "chown: invalid group: appuser:appuser".
RUN apt-get update \
 && apt-get install -y --no-install-recommends tini \
 && rm -rf /var/lib/apt/lists/* \
 && groupadd --system --gid 1001 appuser \
 && useradd  --system --uid 1001 --gid appuser --home /home/appuser appuser \
 && mkdir -p /app /home/appuser/.local \
 && chown -R appuser:appuser /app /home/appuser

WORKDIR /app

# Comando default em todos os targets — substituído nos finais.
ENTRYPOINT ["/usr/bin/tini", "--"]


# ---------- Builders: instalam dependências em camadas --------------------
# Cadeia de builders, cada um herdando do anterior e somando dependências:
#   builder-prod -> builder-test -> builder-dev
# POR QUÊ em cadeia: evita reinstalar o que já foi instalado e mantém o cache.
# Cada estágio copia o requirements PRIMEIRO e instala — assim, enquanto o
# requirements não muda, a camada de instalação é reaproveitada (build rápido).
# ---------------------------------------------------------------------------
FROM base AS builder-prod
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# builder-test = prod + ferramentas de teste (pytest, httpx, cobertura).
FROM builder-prod AS builder-test
COPY requirements-test.txt .
RUN pip install --no-cache-dir --user -r requirements-test.txt

# builder-dev = test + ferramentas de dev (debugpy, ruff, mypy...).
FROM builder-test AS builder-dev
COPY requirements-dev.txt .
RUN pip install --no-cache-dir --user -r requirements-dev.txt


# ---------- Target final: PROD ---------------------------------------------
# Imagem que vai (no futuro) para o Amazon ECR e roda no EKS.
# Não tem ferramentas de dev/teste; só o necessário em runtime.
# ---------------------------------------------------------------------------
FROM base AS prod

COPY --from=builder-prod --chown=appuser:appuser /root/.local /home/appuser/.local
COPY --chown=appuser:appuser app/ /app/app/

USER appuser
EXPOSE 8000

# HEALTHCHECK nativo do Docker; usado também por orquestradores.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; \
      sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health').status == 200 else 1)"

# --proxy-headers + --forwarded-allow-ips: faz o uvicorn confiar no cabeçalho
# X-Forwarded-Proto enviado pelo ALB/proxy. POR QUÊ: sem isso, o app acha que
# tudo é HTTP e pode gerar URLs/redirects errados. "*" confia em qualquer proxy
# — aceitável porque, em produção, só o ALB fala com o pod (rede privada).
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${APP_PORT} --proxy-headers --forwarded-allow-ips='*'"]


# ---------- Target final: TEST ---------------------------------------------
# Imagem usada para rodar a suíte de testes (pytest) de forma isolada — no CI
# (futuro) e localmente via docker-compose.test.yml.
# Inclui as libs de teste (de builder-test) e EMBUTE o código + a pasta tests/
# (sem volume), garantindo reprodutibilidade: o que está na imagem é o que é
# testado.
# ---------------------------------------------------------------------------
FROM base AS test

COPY --from=builder-test --chown=appuser:appuser /root/.local /home/appuser/.local
COPY --chown=appuser:appuser app/          /app/app/
COPY --chown=appuser:appuser tests/        /app/tests/
COPY --chown=appuser:appuser pyproject.toml /app/pyproject.toml

USER appuser

# Comando padrão: roda a suíte. O CI/compose pode sobrescrever com flags.
CMD ["pytest", "-q"]


# ---------- Target final: DEV ----------------------------------------------
# Imagem usada pelo devcontainer do VS Code.
# NÃO copia o código: ele vem por volume montado pelo devcontainer/compose,
# permitindo hot-reload (uvicorn --reload) e debug remoto (debugpy na 5678).
#
# Ferramentas de nuvem (AWS CLI, kubectl, eksctl, Node/CDK, docker CLI) NÃO são
# instaladas aqui: o devcontainer.json as adiciona via "features" oficiais.
# POR QUÊ features e não RUN no Dockerfile: as features já tratam versão,
# arquitetura (amd64/arm64) e integração (ex.: docker-outside-of-docker alinha
# o grupo do socket). Menos código para manter e mais portável.
# ---------------------------------------------------------------------------
FROM base AS dev

# `sudo` SOMENTE no target dev (nunca no prod). POR QUÊ: o devcontainer roda
# como usuário não-root `appuser`; o post-create script (instalar eksctl,
# `npm i -g aws-cdk`) precisa escrever em /usr/local.
# IMPACTO: conveniência de desenvolvimento. RISCO: sudo numa imagem de produção
# aumenta a superfície de ataque — por isso ele fica fora do target `prod`.
#
# Também instalamos Node.js + npm AQUI (não via feature do devcontainer).
# POR QUÊ: a feature oficial de Node usa nvm + `source`, que falha no shell
# padrão (dash) do Debian trixie. O Node do apt é estável e suficiente para o
# AWS CDK (Aula 11). O `cdk` em si é instalado no post-create via npm.
#
# Ferramentas auxiliares úteis no devcontainer:
#   postgresql-client  -> dá o `psql` para inspecionar o banco
#   netcat-openbsd     -> dá o `nc` para testar conectividade (host:porta)
#   iputils-ping       -> ping
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      sudo nodejs npm \
      postgresql-client netcat-openbsd iputils-ping \
 && rm -rf /var/lib/apt/lists/* \
 && echo "appuser ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/appuser \
 && chmod 0440 /etc/sudoers.d/appuser

COPY --from=builder-dev --chown=appuser:appuser /root/.local /home/appuser/.local

USER appuser

# 8000: API.  5678: debugpy (Attach do VS Code).
EXPOSE 8000 5678

# Em dev também usamos --proxy-headers (caso rode atrás de um proxy local com
# mkcert) e --reload para hot-reload.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${APP_PORT} --reload --proxy-headers --forwarded-allow-ips='*'"]
