#!/usr/bin/env bash
# =============================================================================
# semana-06-servidores-destruir.sh — Semana 6 · Aula 12 — termina os 3 EC2 da demo e apaga o security group.
# Encontra tudo pela tag project=cloudtask-demo (criada pelo semana-06-servidores-subir.sh).
# =============================================================================
set -euo pipefail
REGION="${REGION:-us-east-1}"
SG_NAME="${SG_NAME:-cloudtask-demo-sg}"

IDS=$(aws ec2 describe-instances --region "$REGION" \
  --filters Name=tag:project,Values=cloudtask-demo \
            Name=instance-state-name,Values=pending,running,stopping,stopped \
  --query 'Reservations[].Instances[].InstanceId' --output text)

if [ -n "$IDS" ]; then
  echo "==> Terminando: $IDS"
  aws ec2 terminate-instances --region "$REGION" --instance-ids $IDS >/dev/null
  aws ec2 wait instance-terminated --region "$REGION" --instance-ids $IDS
  echo "==> Instâncias terminadas."
else
  echo "==> Nenhuma instância com tag project=cloudtask-demo."
fi

# Elastic IPs da demo (libera para não cobrar EIP ocioso).
for alloc in $(aws ec2 describe-addresses --region "$REGION" \
    --filters Name=tag:project,Values=cloudtask-demo \
    --query 'Addresses[].AllocationId' --output text); do
  aws ec2 release-address --region "$REGION" --allocation-id "$alloc" && echo "==> EIP $alloc liberado."
done

# O SG só pode ser apagado depois que as instâncias somem.
SG=$(aws ec2 describe-security-groups --region "$REGION" \
  --filters Name=group-name,Values="$SG_NAME" \
  --query 'SecurityGroups[0].GroupId' --output text 2>/dev/null || echo "None")
if [ "$SG" != "None" ] && [ -n "$SG" ]; then
  aws ec2 delete-security-group --region "$REGION" --group-id "$SG" && echo "==> SG $SG apagado." || \
    echo "!! Não consegui apagar o SG agora (tente de novo em 1 min)."
fi
echo "==> Limpeza concluída."
