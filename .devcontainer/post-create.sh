#!/usr/bin/env bash
# =============================================================================
# post-create.sh — roda UMA vez, após o devcontainer ser criado.
# -----------------------------------------------------------------------------
# Instala as ferramentas que não têm feature oficial confiável (eksctl e o
# AWS CDK) e ajusta as permissões das credenciais montadas do host.
#
# Roda como o usuário `appuser`, que tem sudo NOPASSWD apenas no target `dev`
# (ver Dockerfile). POR QUÊ sudo aqui: instalar binários em /usr/local/bin e
# pacotes npm globais exige escrita em diretórios do sistema.
# =============================================================================
set -euo pipefail

echo "==> [post-create] Ajustando dono das credenciais montadas (host -> container)..."
# Se a pasta foi criada pelo Docker como root (host não tinha ~/.aws ou ~/.kube),
# devolvemos a posse ao appuser para o AWS CLI / kubectl conseguirem ler/escrever.
# O '|| true' evita quebrar o build se a pasta não existir.
sudo mkdir -p /home/appuser/.aws /home/appuser/.kube
sudo chown -R appuser:appgroup /home/appuser/.aws /home/appuser/.kube || true
chmod 700 /home/appuser/.aws /home/appuser/.kube || true

echo "==> [post-create] Instalando eksctl..."
# Detecta a arquitetura para baixar o binário certo (amd64 x arm64).
ARCH_RAW="$(uname -m)"
case "${ARCH_RAW}" in
  x86_64)            ARCH="amd64" ;;
  aarch64 | arm64)   ARCH="arm64" ;;
  *)                 ARCH="amd64" ;;
esac
EKSCTL_URL="https://github.com/eksctl-io/eksctl/releases/latest/download/eksctl_$(uname -s)_${ARCH}.tar.gz"
curl -sSL "${EKSCTL_URL}" | sudo tar -xz -C /usr/local/bin
sudo chmod +x /usr/local/bin/eksctl

echo "==> [post-create] Instalando AWS CDK (npm global)..."
sudo npm install -g aws-cdk

echo "==> [post-create] Versões instaladas:"
# '|| true' para não abortar caso alguma ferramenta ainda não esteja no PATH.
python --version || true
aws --version    || true
kubectl version --client --output=yaml 2>/dev/null | head -3 || true
eksctl version   || true
node --version   || true
cdk --version    || true
docker --version || true

echo "==> [post-create] Pronto. Lembre: 'kind' (Aula 6) roda no HOST, não aqui."
