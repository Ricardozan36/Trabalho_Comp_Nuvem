#!/usr/bin/env bash
# =============================================================================
# mostrar-links.sh — reimprime os LINKS (App/Swagger/Grafana) + o TOKEN do
# Swagger, quando você não anotou a saída do deploy.
# -----------------------------------------------------------------------------
# Funciona para os DOIS caminhos (CLI `semana-06-servidores-subir.sh` e
# `cdk deploy`): ambos marcam o Elastic IP com a tag `project=cloudtask-demo`,
# então achamos o host `<ip>.sslip.io` por ela — sem depender de outputs.
#
# USO (de qualquer pasta, com o Learner Lab iniciado):
#   bash infra/servers/mostrar-links.sh
# =============================================================================
set -euo pipefail

REGION="${REGION:-us-east-1}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-admin#123}"

EIP=$(aws ec2 describe-addresses --region "$REGION" \
  --filters Name=tag:project,Values=cloudtask-demo \
  --query 'Addresses[0].PublicIp' --output text 2>/dev/null || echo "None")

if [ "$EIP" = "None" ] || [ -z "$EIP" ]; then
  echo "Nenhum Elastic IP com tag project=cloudtask-demo encontrado."
  echo "A infra está no ar? Suba com:"
  echo "  bash infra/servers/semana-06-servidores-subir.sh    # caminho CLI"
  echo "  (ou) cd infra/cdk && ./semana-06-cdk-deploy.sh deploy   # caminho CDK"
  exit 1
fi

HOST="$(echo "$EIP" | tr '.' '-').sslip.io"
API_BASE="https://$HOST/api"

echo "============================================================"
echo "  CloudTask AI SaaS — serviços no ar"
echo "------------------------------------------------------------"
echo "  App (frontend):  https://$HOST/"
echo "  API (Swagger):   https://$HOST/api/docs   (admin / $ADMIN_PASSWORD)"
echo "  Grafana:         https://$HOST/grafana/   (admin / $ADMIN_PASSWORD)"
echo
TOKEN="$(curl -fsS -m 8 -X POST "$API_BASE/auth/login" \
  -H 'Content-Type: application/json' \
  -d "{\"username\":\"admin\",\"password\":\"$ADMIN_PASSWORD\"}" \
  | sed -E 's/.*"access_token":"([^"]+)".*/\1/' 2>/dev/null || true)"
if [ -n "$TOKEN" ]; then
  echo "  🔑 Token Bearer (JWT) — cole em 'Authorize' no Swagger:"
  echo
  echo "      $TOKEN"
  echo
  echo "  No Swagger (https://$HOST/api/docs): botão 'Authorize' → cole o token."
else
  echo "  ⏳ A API ainda não respondeu (boot/cert). Tente de novo em 1-2 min, ou:"
  echo "      curl -s -X POST $API_BASE/auth/login -H 'Content-Type: application/json' \\"
  echo "        -d '{\"username\":\"admin\",\"password\":\"$ADMIN_PASSWORD\"}'"
fi
echo "  Login do app/Grafana: admin / $ADMIN_PASSWORD"
echo "============================================================"
