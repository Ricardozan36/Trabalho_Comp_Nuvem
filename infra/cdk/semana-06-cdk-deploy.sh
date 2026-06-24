#!/usr/bin/env bash
# =============================================================================
# semana-06-cdk-deploy.sh — Semana 6 · Aula 11 — sobe/derruba as stacks CDK no AWS Academy (Learner Lab)
#                  SEM precisar de `cdk bootstrap`.
# -----------------------------------------------------------------------------
# POR QUÊ este script existe:
#   No Learner Lab o `cdk bootstrap`/`cdk deploy` falham — criar as IAM roles do
#   CDKToolkit é negado para a role da sessão (`voclabs`). A saída é separar:
#     1. o CDK só GERA o template  -> `cdk synth`  (não toca a AWS)
#     2. o CloudFormation IMPLANTA o template usando a LabRole -> `aws cloudformation deploy`
#   A LabRole confia em `cloudformation.amazonaws.com` (testado), então o CFN a
#   assume e cria S3/ECR/VPC. As stacks foram feitas SEM assets (sem Lambda),
#   então o template vai inline — nada precisa de bucket de bootstrap.
#
# USO (dentro de infra/cdk/, no devcontainer ou no AWS CloudShell):
#   pip install -r requirements.txt        # uma vez
#   ./semana-06-cdk-deploy.sh deploy                 # cria todas as stacks
#   ./semana-06-cdk-deploy.sh destroy                # apaga todas as stacks
#
# ⚠️ A ComputeStack (3 EC2) depende de Network e Database (a API lê o RDS). A
#    ordem abaixo já garante isso. Os EC2 são baratos, mas o RDS cobra por hora —
#    rode `destroy` ao terminar.
#
# Em CONTA PRÓPRIA também funciona: se não houver LabRole, o deploy roda sem
# `--role-arn` (usa suas credenciais). Ou use o `cdk deploy` normal.
# =============================================================================
set -euo pipefail

# Silencia o aviso barulhento de "Node 20 end-of-life" do jsii (cosmético).
export JSII_SILENCE_WARNING_DEPRECATED_NODE_VERSION=1

ACTION="${1:-deploy}"
REGION="${AWS_REGION:-us-east-1}"
# Ordem de DEPLOY (dependências primeiro): Network antes do Database (VPC);
# Events antes do Observability (alarme/dashboard usam a tabela).
STACKS=(
  CloudTaskNetwork
  CloudTaskStorage
  CloudTaskEcr
  CloudTaskEvents
  CloudTaskObservability
  CloudTaskDatabase
  CloudTaskCompute
)

ACCOUNT="$(aws sts get-caller-identity --query Account --output text)"
echo "==> Conta=${ACCOUNT}  Região=${REGION}  Ação=${ACTION}"

# Usa a LabRole como role de execução do CloudFormation, se ela existir.
ROLE_ARN="arn:aws:iam::${ACCOUNT}:role/LabRole"
ROLE_ARGS=()
if aws iam get-role --role-name LabRole >/dev/null 2>&1; then
  ROLE_ARGS=(--role-arn "${ROLE_ARN}")
  echo "==> Usando LabRole como execução do CloudFormation (Academy)."
else
  echo "==> LabRole não encontrada — deploy com as credenciais atuais (conta própria)."
fi

case "${ACTION}" in
  deploy)
    # Garante as libs Python do CDK. O cdk.json roda `python3 app.py`; sem o
    # aws-cdk-lib instalado (ex.: container recém-recriado em que o post-create
    # não rodou), o synth falha com "No module named 'aws_cdk'". Instala de forma
    # idempotente (rápido se já existe).
    python3 -c "import aws_cdk" 2>/dev/null || {
      echo "==> instalando libs do CDK (aws-cdk-lib)..."
      # SEM --user: o pip escolhe o destino certo sozinho (em venv instala no
      # venv; como appuser sem venv cai em ~/.local; o --user fixo QUEBRA dentro
      # de um venv com "Can not perform a '--user' install").
      python3 -m pip install -q -r requirements.txt
    }
    echo "==> cdk synth (gera os templates em cdk.out/)..."
    cdk synth >/dev/null
    for s in "${STACKS[@]}"; do
      echo "==> deploy ${s}..."
      aws cloudformation deploy \
        --template-file "cdk.out/${s}.template.json" \
        --stack-name "${s}" \
        --capabilities CAPABILITY_IAM \
        --region "${REGION}" \
        "${ROLE_ARGS[@]}"
    done
    echo "==> Outputs:"
    for s in "${STACKS[@]}"; do
      aws cloudformation describe-stacks --stack-name "${s}" --region "${REGION}" \
        --query "Stacks[0].Outputs" --output table 2>/dev/null || true
    done

    # --- Resumo final: links dos serviços + token JWT para o Swagger ----------
    # Lê os Outputs da ComputeStack (os 3 EC2), espera a API responder (a 1a
    # build leva ~3-5 min) e faz login (admin/admin#123) para imprimir o token
    # Bearer que ativa as rotas protegidas no Swagger (botão Authorize).
    out() { aws cloudformation describe-stacks --stack-name CloudTaskCompute --region "${REGION}" \
      --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue | [0]" --output text 2>/dev/null || true; }
    FRONT_URL="$(out FrontendUrl)"; API_URL="$(out ApiUrl)"; GRAF_URL="$(out GrafanaUrl)"
    API_BASE="${API_URL%/docs}"   # de http://IP:8000/docs -> http://IP:8000

    echo
    echo "============================================================"
    echo "  CloudTask AI SaaS — serviços no ar"
    echo "------------------------------------------------------------"
    echo "  App (frontend):  ${FRONT_URL}"
    echo "  API (Swagger):   ${API_URL}"
    echo "  Grafana:         ${GRAF_URL}   (admin / admin#123)"
    echo
    echo "  Aguardando a API responder (1ª build do Docker leva ~3-5 min)..."
    TOKEN=""
    if [ -n "${API_BASE}" ] && [ "${API_BASE}" != "None" ]; then
      for _ in $(seq 1 28); do
        if curl -fsS -m 5 "${API_BASE}/health" >/dev/null 2>&1; then
          TOKEN="$(curl -fsS -m 8 -X POST "${API_BASE}/auth/login" \
            -H 'Content-Type: application/json' \
            -d '{"username":"admin","password":"admin#123"}' \
            | sed -E 's/.*"access_token":"([^"]+)".*/\1/' || true)"
          break
        fi
        sleep 15
      done
    fi
    echo
    if [ -n "${TOKEN}" ]; then
      echo "  🔑 Token Bearer (JWT) — cole em 'Authorize' no Swagger:"
      echo
      echo "      ${TOKEN}"
      echo
      echo "  No Swagger (${API_URL}): botão 'Authorize' → cole o token → Authorize."
      echo "  Aí as rotas protegidas (/tasks, /uploads, /events) passam a funcionar."
    else
      echo "  ⏳ A API ainda não respondeu. Assim que subir, pegue o token com:"
      echo
      echo "      curl -s -X POST ${API_BASE}/auth/login -H 'Content-Type: application/json' \\"
      echo "        -d '{\"username\":\"admin\",\"password\":\"admin#123\"}'"
    fi
    echo "  Login do app/Grafana: admin / admin#123"
    echo "============================================================"
    echo "✅ Stacks no ar. Ao terminar:  ./semana-06-cdk-deploy.sh destroy"
    ;;
  destroy)
    # Ordem INVERSA do deploy (dependentes primeiro): Database antes da Network
    # (RDS usa a VPC); Observability antes de Events (usa a tabela).
    REVERSE=(
      CloudTaskCompute
      CloudTaskDatabase
      CloudTaskObservability
      CloudTaskEvents
      CloudTaskEcr
      CloudTaskStorage
      CloudTaskNetwork
    )
    # SEQUENCIAL (deleta + espera CADA uma antes da próxima). POR QUÊ não disparar
    # tudo em paralelo: uma stack que EXPORTA algo só pode ser deletada depois que
    # quem IMPORTA já sumiu (ex.: Events exporta a tabela que a Observability
    # importa). Em paralelo, o delete da Events falha ("Cannot delete export ...
    # in use") e o stack volta para CREATE_COMPLETE — aí o `wait` fica preso para
    # sempre. Deletando em ordem inversa, uma de cada vez, isso não acontece.
    for s in "${REVERSE[@]}"; do
      # pula o que não existe (deploy parcial / já deletado)
      if ! aws cloudformation describe-stacks --stack-name "${s}" --region "${REGION}" >/dev/null 2>&1; then
        echo "    ${s}: (ausente, pulando)"
        continue
      fi
      echo "==> delete ${s}..."
      aws cloudformation delete-stack --stack-name "${s}" --region "${REGION}" 2>/dev/null || true
      aws cloudformation wait stack-delete-complete --stack-name "${s}" --region "${REGION}" 2>/dev/null \
        && echo "    ${s}: deletado" \
        || echo "    ${s}: ⚠️ não deletou (ver: aws cloudformation describe-stack-events --stack-name ${s})"
    done
    echo "🔥 Stacks removidas."
    ;;
  *)
    echo "Uso: ./semana-06-cdk-deploy.sh [deploy|destroy]"; exit 1 ;;
esac
