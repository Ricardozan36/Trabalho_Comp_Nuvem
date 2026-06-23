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
      python3 -m pip install -q --user -r requirements.txt
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
    for s in "${REVERSE[@]}"; do
      echo "==> delete ${s}..."
      aws cloudformation delete-stack --stack-name "${s}" --region "${REGION}" 2>/dev/null || true
    done
    for s in "${REVERSE[@]}"; do
      aws cloudformation wait stack-delete-complete --stack-name "${s}" --region "${REGION}" 2>/dev/null \
        && echo "    ${s}: deletado" || true
    done
    echo "🔥 Stacks removidas."
    ;;
  *)
    echo "Uso: ./semana-06-cdk-deploy.sh [deploy|destroy]"; exit 1 ;;
esac
