#!/bin/bash
# =============================================================================
# user-data do servidor de API (EC2) — Aula 12
# -----------------------------------------------------------------------------
# Sobe a API CloudTask num EC2 Amazon Linux 2023:
#   * instala Docker + git;
#   * clona o repositório (branch da Semana 6);
#   * sobe um PostgreSQL e a API em containers, na mesma rede Docker;
#   * a API fica exposta na porta 8000.
#
# POR QUÊ Postgres em container aqui: este é o caminho "rápido/barato" do script
# CLI (VPC default, sem RDS). No caminho CDK de produção, o mesmo user-data
# recebe DATABASE_URL apontando para o RDS (ver ComputeStack) e NÃO sobe o
# container de banco. Tudo é controlado pelas variáveis abaixo.
#
# Variáveis que o lançador injeta no topo deste script (export ...):
#   ADMIN_PASSWORD   senha do admin da API/app   (default admin#123)
#   SECRET_KEY       chave de assinatura do JWT   (TROCAR em produção)
#   DATABASE_URL     se vier preenchida, usa esse banco (ex.: RDS) e NÃO sobe o
#                    container `db`. Se vazia, sobe Postgres local em container.
#   REPO_URL / BRANCH  origem do código.
# =============================================================================
set -xe

: "${ADMIN_PASSWORD:=admin#123}"
: "${SECRET_KEY:=demo-troque-em-producao}"
: "${REPO_URL:=https://github.com/N-CPUninter/Computa-o-em-Nuvem---Projeto-exemplo-CloudTask-AI-SaaS.git}"
: "${BRANCH:=semana-06-cdk-final}"
: "${DATABASE_URL:=}"
: "${ROOT_PATH:=}"   # atrás do proxy: "/api" (Swagger gera URLs com o prefixo)

dnf update -y
dnf install -y docker git
systemctl enable --now docker

cd /opt
git clone --depth 1 -b "$BRANCH" "$REPO_URL" app
cd app

docker network create cloudtask || true

# Banco: usa RDS (DATABASE_URL externa) OU sobe Postgres local em container.
if [ -z "$DATABASE_URL" ]; then
  docker run -d --name db --network cloudtask --restart unless-stopped \
    -e POSTGRES_USER=cloudtask -e POSTGRES_PASSWORD=cloudtask -e POSTGRES_DB=cloudtask \
    -v pgdata:/var/lib/postgresql/data postgres:16
  DATABASE_URL="postgresql+psycopg2://cloudtask:cloudtask@db:5432/cloudtask"
  # espera o banco aceitar conexões
  for i in $(seq 1 30); do
    docker exec db pg_isready -U cloudtask && break
    sleep 2
  done
fi

# Imagem da API (target prod do Dockerfile do repo).
docker build -t cloudtask-api:prod --target prod .

docker run -d --name api --network cloudtask --restart unless-stopped \
  -p 8000:8000 \
  -e APP_ENV=production \
  -e LOG_LEVEL=INFO \
  -e DATABASE_URL="$DATABASE_URL" \
  -e SECRET_KEY="$SECRET_KEY" \
  -e ADMIN_USERNAME=admin \
  -e ADMIN_PASSWORD="$ADMIN_PASSWORD" \
  -e STORAGE_MODE=local \
  -e CORS_ORIGINS='*' \
  -e ROOT_PATH="$ROOT_PATH" \
  cloudtask-api:prod

echo "API up on :8000"
