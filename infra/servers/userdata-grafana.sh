#!/bin/bash
# =============================================================================
# user-data do servidor Grafana (EC2) — Aula 12
# -----------------------------------------------------------------------------
# Sobe o Grafana OSS num EC2 Amazon Linux 2023, já provisionado com:
#   * datasource CloudWatch (autenticação `default` = role do próprio EC2, via
#     IMDS — nada de chave fixa). É por isso que o EC2 usa o LabInstanceProfile;
#   * um dashboard útil (CPU/Rede dos EC2, DynamoDB, RDS) carregado por arquivo.
#   * senha do admin = admin#123.
#
# Acesso: http://<IP-PUBLICO>:3000  (admin / admin#123)
#
# Variáveis injetadas pelo lançador:
#   ADMIN_PASSWORD   senha do admin do Grafana (default admin#123)
#   REGION           região das métricas (default us-east-1)
#   DASH_B64         dashboard json (base64). Se vazio, sobe sem dashboard
#                    pré-carregado (datasource CloudWatch continua disponível).
#   ROOT_URL         se setada (ex.: https://host/grafana/), serve o Grafana sob
#                    subcaminho (atrás do proxy HTTPS do Edge).
# =============================================================================
set -xe

: "${ADMIN_PASSWORD:=admin#123}"
: "${REGION:=us-east-1}"
: "${DASH_B64:=}"
: "${ROOT_URL:=}"

# Repositório oficial do Grafana (RPM).
cat > /etc/yum.repos.d/grafana.repo <<'REPO'
[grafana]
name=grafana
baseurl=https://rpm.grafana.com
repo_gpgcheck=1
enabled=1
gpgcheck=1
gpgkey=https://rpm.grafana.com/gpg.key
sslverify=1
sslcacert=/etc/pki/tls/certs/ca-bundle.crt
REPO
dnf install -y grafana

# --- Datasource CloudWatch (auth pela role do EC2) ---------------------------
mkdir -p /etc/grafana/provisioning/datasources /etc/grafana/provisioning/dashboards /var/lib/grafana/dashboards
cat > /etc/grafana/provisioning/datasources/cloudwatch.yml <<YML
apiVersion: 1
datasources:
  - name: CloudWatch
    uid: cloudwatch
    type: cloudwatch
    isDefault: true
    jsonData:
      authType: default
      defaultRegion: ${REGION}
YML

# --- Provider que carrega dashboards de arquivo ------------------------------
cat > /etc/grafana/provisioning/dashboards/cloudtask.yml <<'YML'
apiVersion: 1
providers:
  - name: CloudTask
    folder: CloudTask
    type: file
    allowUiUpdates: true
    options:
      path: /var/lib/grafana/dashboards
YML

# Dashboard pré-carregado (vem embutido em base64; mesma ideia do HTML do front).
if [ -n "$DASH_B64" ]; then
  echo "$DASH_B64" | base64 -d > /var/lib/grafana/dashboards/cloudtask.json
fi
chown -R grafana:grafana /var/lib/grafana/dashboards

# Senha do admin via variável de ambiente (NÃO via grafana.ini): no .ini o
# caractere '#' inicia comentário e truncaria "admin#123" em "admin". O systemd
# lê /etc/sysconfig/grafana-server como EnvironmentFile, onde o '#' é literal.
echo "GF_SECURITY_ADMIN_PASSWORD=${ADMIN_PASSWORD}" >> /etc/sysconfig/grafana-server

# Dashboard provisionado vira a HOME -> abre já mostrando um painel pronto
# (resolve "não aparece nenhum dashboard").
echo "GF_DASHBOARDS_DEFAULT_HOME_DASHBOARD_PATH=/var/lib/grafana/dashboards/cloudtask.json" >> /etc/sysconfig/grafana-server

# Atrás do proxy HTTPS do Edge: serve sob /grafana/ com a URL pública correta.
if [ -n "$ROOT_URL" ]; then
  echo "GF_SERVER_ROOT_URL=${ROOT_URL}"        >> /etc/sysconfig/grafana-server
  echo "GF_SERVER_SERVE_FROM_SUB_PATH=true"    >> /etc/sysconfig/grafana-server
fi

systemctl enable --now grafana-server
echo "Grafana up on :3000 (admin / ${ADMIN_PASSWORD})"
