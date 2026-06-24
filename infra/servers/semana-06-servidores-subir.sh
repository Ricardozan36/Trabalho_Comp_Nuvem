#!/usr/bin/env bash
# =============================================================================
# semana-06-servidores-subir.sh — Semana 6 · Aula 12 — sobe os 3 servidores
# (Edge/Caddy + API + Grafana) no AWS Academy, com HTTPS válido e Swagger com senha.
# -----------------------------------------------------------------------------
# Arquitetura (tudo só por HTTPS; o navegador só fala com o Edge):
#
#   navegador ──HTTPS──► EDGE (Caddy)  ──HTTP interno──►  API   (:8000, Docker)
#   (443)                <ip>.sslip.io  ├─ /api/*      ──►  Grafana (:3000)
#                        serve o SPA    └─ /grafana/*
#
#   * **Edge/Caddy** tem um **Elastic IP** e usa o hostname `<ip>.sslip.io`.
#     O Caddy obtém sozinho um **certificado válido** (Let's Encrypt, com
#     fallback ZeroSSL) — sem domínio próprio. Redireciona 80→443.
#   * **API** e **Grafana** NÃO ficam expostos à internet nas portas 8000/3000:
#     só o Edge os alcança (mesma security group). Acaba o "conteúdo misto" e o
#     acesso HTTP direto — tudo passa pelo Edge em HTTPS.
#   * **Swagger** (`/api/docs`, `/api/openapi.json`, `/api/redoc`) fica atrás de
#     **senha** (HTTP Basic no Caddy: admin / ADMIN_PASSWORD).
#
# USO (na raiz do repo, Learner Lab iniciado):
#   bash infra/servers/semana-06-servidores-subir.sh
# Derrubar:  bash infra/servers/semana-06-servidores-destruir.sh
#
# OBS sobre "cert válido sem domínio": usamos sslip.io (mapeia o IP no hostname)
# para o ACME validar. Se o Let's Encrypt/ZeroSSL estiver com rate-limit, o
# Caddy pode demorar ou cair num cert próprio (aviso no navegador) — nesse caso
# rode de novo mais tarde ou use um domínio real.
# =============================================================================
set -euo pipefail

REGION="${REGION:-us-east-1}"
KEY_NAME="${KEY_NAME:-vockey}"
PROFILE_NAME="${PROFILE_NAME:-LabInstanceProfile}"
SG_NAME="${SG_NAME:-cloudtask-demo-sg}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-admin#123}"
SECRET_KEY="${SECRET_KEY:-demo-troque-em-producao}"
TAG="cloudtask-demo"
HERE="$(cd "$(dirname "$0")" && pwd)"
FRONT_HTML="$HERE/../../frontend/index.html"

echo "==> Região: $REGION"

AMI=$(aws ec2 describe-images --region "$REGION" --owners amazon \
  --filters "Name=name,Values=al2023-ami-2023.*-kernel-6.1-x86_64" "Name=state,Values=available" \
  --query 'reverse(sort_by(Images,&CreationDate))[0].ImageId' --output text)
VPC=$(aws ec2 describe-vpcs --region "$REGION" --filters Name=isDefault,Values=true --query 'Vpcs[0].VpcId' --output text)
SUBNET=$(aws ec2 describe-subnets --region "$REGION" --filters Name=vpc-id,Values="$VPC" Name=default-for-az,Values=true --query 'Subnets[0].SubnetId' --output text)
echo "==> AMI: $AMI  VPC: $VPC  Subnet: $SUBNET"

# --- Security Group: 22/80/443 do mundo; 8000/3000 só DENTRO do grupo ---------
SG=$(aws ec2 describe-security-groups --region "$REGION" \
  --filters Name=group-name,Values="$SG_NAME" Name=vpc-id,Values="$VPC" \
  --query 'SecurityGroups[0].GroupId' --output text 2>/dev/null || echo "None")
if [ "$SG" = "None" ] || [ -z "$SG" ]; then
  SG=$(aws ec2 create-security-group --region "$REGION" --group-name "$SG_NAME" \
    --description "CloudTask demo (Aula 12)" --vpc-id "$VPC" --query 'GroupId' --output text)
  for p in 22 80 443; do
    aws ec2 authorize-security-group-ingress --region "$REGION" --group-id "$SG" \
      --protocol tcp --port "$p" --cidr 0.0.0.0/0 >/dev/null
  done
  # API/Grafana só acessíveis de dentro do grupo (o Edge alcança; o mundo não).
  for p in 8000 3000; do
    aws ec2 authorize-security-group-ingress --region "$REGION" --group-id "$SG" \
      --protocol tcp --port "$p" --source-group "$SG" >/dev/null
  done
  echo "==> SG criado: $SG"
else
  echo "==> SG reaproveitado: $SG"
fi

udurl () { if command -v cygpath >/dev/null 2>&1; then echo "file://$(cygpath -m "$1")"; else echo "file://$1"; fi; }

run_instance () {  # $1=name $2=type $3=userdata-file -> ecoa InstanceId
  aws ec2 run-instances --region "$REGION" \
    --image-id "$AMI" --instance-type "$2" --key-name "$KEY_NAME" \
    --iam-instance-profile "Name=$PROFILE_NAME" \
    --security-group-ids "$SG" --subnet-id "$SUBNET" --associate-public-ip-address \
    --user-data "$(udurl "$3")" \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$1},{Key=project,Value=$TAG}]" \
    --query 'Instances[0].InstanceId' --output text
}
priv_ip () { aws ec2 describe-instances --region "$REGION" --instance-ids "$1" --query 'Reservations[0].Instances[0].PrivateIpAddress' --output text; }

# --- Elastic IP (define o hostname sslip.io ANTES de subir o Edge) ------------
EIP_ALLOC=$(aws ec2 allocate-address --region "$REGION" --domain vpc \
  --tag-specifications "ResourceType=elastic-ip,Tags=[{Key=project,Value=$TAG}]" \
  --query 'AllocationId' --output text)
EIP=$(aws ec2 describe-addresses --region "$REGION" --allocation-ids "$EIP_ALLOC" --query 'Addresses[0].PublicIp' --output text)
HOST="$(echo "$EIP" | tr '.' '-').sslip.io"
echo "==> Elastic IP: $EIP   Host HTTPS: $HOST"

# --- API ---------------------------------------------------------------------
UD_API="$(mktemp)"
{ echo '#!/bin/bash'; echo "export ADMIN_PASSWORD='$ADMIN_PASSWORD'"; echo "export SECRET_KEY='$SECRET_KEY'"; echo "export ROOT_PATH='/api'"; tail -n +2 "$HERE/userdata-api.sh"; } > "$UD_API"
API_ID=$(run_instance cloudtask-api t3.small "$UD_API")
echo "==> API: $API_ID"

# --- Grafana (subpath /grafana + dashboard como home) ------------------------
DASH_B64=$(base64 -w0 "$HERE/grafana-dashboard.json")
UD_GRAF="$(mktemp)"
{ echo '#!/bin/bash'; echo "export ADMIN_PASSWORD='$ADMIN_PASSWORD'"; echo "export REGION='$REGION'"; echo "export DASH_B64='$DASH_B64'"; echo "export ROOT_URL='https://$HOST/grafana/'"; tail -n +2 "$HERE/userdata-grafana.sh"; } > "$UD_GRAF"
GRAF_ID=$(run_instance cloudtask-grafana t3.small "$UD_GRAF")
echo "==> Grafana: $GRAF_ID"

aws ec2 wait instance-running --region "$REGION" --instance-ids "$API_ID" "$GRAF_ID"
API_IP=$(priv_ip "$API_ID"); GRAF_IP=$(priv_ip "$GRAF_ID")
echo "==> IPs privados — API: $API_IP  Grafana: $GRAF_IP"

# --- Edge (Caddy: TLS + SPA + proxy) -----------------------------------------
HTML_B64=$(gzip -c "$FRONT_HTML" | base64 -w0)
UD_EDGE="$(mktemp)"
cat > "$UD_EDGE" <<EDGE
#!/bin/bash
set -xe
CADDY_VER=2.8.4
curl -fsSL "https://github.com/caddyserver/caddy/releases/download/v\${CADDY_VER}/caddy_\${CADDY_VER}_linux_amd64.tar.gz" -o /tmp/caddy.tgz
tar -xzf /tmp/caddy.tgz -C /usr/local/bin caddy
mkdir -p /etc/caddy /srv/cloudtask /var/lib/caddy
# SPA (embutido, gzip+base64) com a base da API = /api (mesma origem)
cat > /tmp/site.gz.b64 <<'B64'
$HTML_B64
B64
base64 -d /tmp/site.gz.b64 | gunzip > /srv/cloudtask/index.html
sed -i 's#__API_BASE__#/api#' /srv/cloudtask/index.html
# senha do Swagger (bcrypt gerado aqui; vai por env p/ o '\$' do hash não quebrar)
HASH=\$(/usr/local/bin/caddy hash-password --plaintext '$ADMIN_PASSWORD')
printf 'CLOUDTASK_HASH=%s\n' "\$HASH" > /etc/caddy/caddy.env
cat > /etc/caddy/Caddyfile <<'CADDY'
{
    # E-mail de contato do ACME. PRECISA de um TLD real e NÃO-reservado:
    # ".local" e "example.com" são RECUSADOS pelo Let's Encrypt (forbidden/invalid
    # public suffix) e forçam o fallback lento p/ ZeroSSL. ".app" passa.
    email admin@cloudtask.app
}
__HOST__ {
    encode gzip
    handle_path /api/* {
        @docs path /docs /redoc /openapi.json
        basic_auth @docs {
            admin {\$CLOUDTASK_HASH}
        }
        reverse_proxy __APIIP__:8000
    }
    handle /grafana/* {
        reverse_proxy __GRAFIP__:3000
    }
    handle {
        root * /srv/cloudtask
        try_files {path} /index.html
        file_server
    }
}
CADDY
sed -i "s#__HOST__#$HOST#; s#__APIIP__#$API_IP#; s#__GRAFIP__#$GRAF_IP#" /etc/caddy/Caddyfile
cat > /etc/systemd/system/caddy.service <<'UNIT'
[Unit]
Description=Caddy
After=network-online.target
Wants=network-online.target
[Service]
EnvironmentFile=/etc/caddy/caddy.env
ExecStart=/usr/local/bin/caddy run --config /etc/caddy/Caddyfile
Restart=on-failure
LimitNOFILE=1048576
[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable --now caddy
echo "edge up"
EDGE
EDGE_ID=$(run_instance cloudtask-edge t3.small "$UD_EDGE")
echo "==> Edge: $EDGE_ID (associando Elastic IP...)"
aws ec2 wait instance-running --region "$REGION" --instance-ids "$EDGE_ID"
aws ec2 associate-address --region "$REGION" --instance-id "$EDGE_ID" --allocation-id "$EIP_ALLOC" >/dev/null

rm -f "$UD_API" "$UD_GRAF" "$UD_EDGE"

# --- Resumo final: links dos serviços + token JWT para o Swagger -------------
# Espera a API responder pelo Edge (cert ACME + 1ª build do Docker) e faz login
# (admin/ADMIN_PASSWORD) para imprimir o token Bearer que ativa as rotas
# protegidas no botão 'Authorize' do Swagger.
API_BASE="https://$HOST/api"
echo
echo "============================================================"
echo "  CloudTask AI SaaS — serviços no ar"
echo "------------------------------------------------------------"
echo "  App (frontend):  https://$HOST/"
echo "  API (Swagger):   https://$HOST/api/docs   (admin / $ADMIN_PASSWORD)"
echo "  Grafana:         https://$HOST/grafana/   (admin / $ADMIN_PASSWORD)"
echo
echo "  Aguardando a API responder (cert ACME + 1ª build do Docker, ~3-5 min)..."
TOKEN=""
for _ in $(seq 1 32); do
  if curl -fsS -m 6 "$API_BASE/health" >/dev/null 2>&1; then
    TOKEN="$(curl -fsS -m 8 -X POST "$API_BASE/auth/login" \
      -H 'Content-Type: application/json' \
      -d "{\"username\":\"admin\",\"password\":\"$ADMIN_PASSWORD\"}" \
      | sed -E 's/.*"access_token":"([^"]+)".*/\1/' || true)"
    break
  fi
  sleep 15
done
echo
if [ -n "$TOKEN" ]; then
  echo "  🔑 Token Bearer (JWT) — cole em 'Authorize' no Swagger:"
  echo
  echo "      $TOKEN"
  echo
  echo "  No Swagger (https://$HOST/api/docs): botão 'Authorize' → cole o token → Authorize."
  echo "  Aí as rotas protegidas (/tasks, /uploads, /events) passam a funcionar."
else
  echo "  ⏳ A API ainda não respondeu. Quando subir, pegue o token com:"
  echo
  echo "      curl -s -X POST $API_BASE/auth/login -H 'Content-Type: application/json' \\"
  echo "        -d '{\"username\":\"admin\",\"password\":\"$ADMIN_PASSWORD\"}'"
fi
echo "  Login do app/Grafana: admin / $ADMIN_PASSWORD"
echo "  (HTTP redireciona p/ HTTPS; API/Grafana não ficam expostos direto.)"
echo "============================================================"
