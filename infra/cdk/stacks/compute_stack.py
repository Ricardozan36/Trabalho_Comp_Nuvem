"""ComputeStack — 3 servidores EC2 (Edge/HTTPS + API + Grafana) — Aula 12.

A **7ª stack**: descreve como IaC os MESMOS três servidores que o caminho "CLI"
(``infra/servers/semana-06-servidores-subir.sh``) cria — agora versionado e
reproduzível com ``cdk deploy``. Mesma arquitetura **Edge/Caddy/HTTPS**:

    navegador ──HTTPS (cert válido)──► EDGE (Caddy)  ──HTTP interno──►  API  (:8000)
    (443)                              <ip>.sslip.io  ├─ /api/*      ──►  Grafana(:3000)
                                       serve o SPA    └─ /grafana/*

    * **Edge** (t3.small) — Caddy: serve o SPA, faz proxy ``/api``→API e
      ``/grafana``→Grafana, obtém **certificado válido** (ACME/Let's Encrypt via
      ``sslip.io`` + Elastic IP), redireciona 80→443 e protege o Swagger com
      **senha** (basic auth).
    * **API** (t3.small) — Docker; conecta no **RDS** (lê a senha no Secrets
      Manager). Só acessível pelo Edge (``/api``).
    * **Grafana** (t3.small) — datasource CloudWatch + dashboard como home, sob
      ``/grafana``. Só acessível pelo Edge.

POR QUÊ ``CfnInstance`` (L1) e não ``ec2.Instance`` (L2): o L2 cria uma IAM Role
+ InstanceProfile novos — **negado no Academy**. Reaproveitamos o
``LabInstanceProfile`` existente (zero IAM). Sem assets (HTML/dashboard embutidos
em base64) => nada de ``cdk bootstrap``.

Diferença vs. o script CLI (de propósito, "mais completo"): aqui a API conecta no
**RDS gerenciado** (não no Postgres local) e tudo roda na **VPC da NetworkStack**.
"""

from __future__ import annotations

import base64
import gzip
from pathlib import Path

from aws_cdk import CfnOutput, CfnTag, Fn, Stack
from aws_cdk import aws_ec2 as ec2
from constructs import Construct

# AMI Amazon Linux 2023 x86_64 (us-east-1). Troque com `ami_id=` se a região/data
# diferir (o script CLI resolve via describe-images).
DEFAULT_AMI = "ami-00948338a4aeec604"

_HERE = Path(__file__).resolve()
_INFRA = _HERE.parents[2]                 # .../infra
_REPO = _HERE.parents[3]                  # raiz do repositório
_SERVERS = _INFRA / "servers"
_FRONT_HTML = _REPO / "frontend" / "index.html"


def _body(path: Path) -> str:
    """Conteúdo de um user-data ``.sh`` SEM a linha do shebang (prefixamos nossos
    próprios ``export`` antes do corpo)."""
    return path.read_text(encoding="utf-8").split("\n", 1)[1]


# User-data do EDGE (Caddy). Construído com placeholders ``@@...@@`` (substituídos
# por valores/Tokens do CDK) para NÃO conflitar com o ``$`` do bash nem com as
# ``{ }`` da config do Caddy. O hash da senha do Swagger é gerado NA instância
# (``caddy hash-password``) e lido por env (``{$CLOUDTASK_HASH}``) — assim o ``$``
# do bcrypt não quebra nada.
_EDGE_TEMPLATE = """#!/bin/bash
set -xe
CADDY_VER=2.8.4
curl -fsSL "https://github.com/caddyserver/caddy/releases/download/v${CADDY_VER}/caddy_${CADDY_VER}_linux_amd64.tar.gz" -o /tmp/caddy.tgz
tar -xzf /tmp/caddy.tgz -C /usr/local/bin caddy
mkdir -p /etc/caddy /srv/cloudtask /var/lib/caddy
cat > /tmp/site.gz.b64 <<'B64'
@@HTMLB64@@
B64
base64 -d /tmp/site.gz.b64 | gunzip > /srv/cloudtask/index.html
sed -i 's#__API_BASE__#/api#' /srv/cloudtask/index.html
HASH=$(/usr/local/bin/caddy hash-password --plaintext '@@ADMINPW@@')
printf 'CLOUDTASK_HASH=%s\\n' "$HASH" > /etc/caddy/caddy.env
cat > /etc/caddy/Caddyfile <<'CADDY'
{
    email admin@cloudtask.app
}
@@HOST@@ {
    encode gzip
    handle_path /api/* {
        @docs path /docs /redoc /openapi.json
        basic_auth @docs {
            admin {$CLOUDTASK_HASH}
        }
        reverse_proxy @@APIIP@@:8000
    }
    handle /grafana/* {
        reverse_proxy @@GRAFIP@@:3000
    }
    handle {
        root * /srv/cloudtask
        try_files {path} /index.html
        file_server
    }
}
CADDY
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
"""


class ComputeStack(Stack):
    """Edge (Caddy/HTTPS) + API + Grafana na VPC da NetworkStack."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        vpc: ec2.IVpc,
        ami_id: str = DEFAULT_AMI,
        admin_password: str = "admin#123",
        secret_key: str = "demo-troque-em-producao",
        db: object | None = None,
        db_secret_name: str | None = None,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # --- Security group: 22/80/443 abertos ao mundo; 8000 (API) e 3000
        #     (Grafana) só DENTRO do grupo (o Edge alcança; o mundo não). --------
        sg = ec2.SecurityGroup(
            self,
            "DemoSg",
            vpc=vpc,
            allow_all_outbound=True,
            description="CloudTask demo (Aula 12): edge 22/80/443; api/grafana internos",
        )
        for port in (22, 80, 443):
            sg.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(port))
        # 8000/3000 só DENTRO do grupo (o Edge alcança a API/Grafana). POR QUÊ um
        # CfnSecurityGroupIngress SEPARADO (e não sg.add_ingress_rule com a própria
        # SG como peer): a auto-referência INLINE faz a SG citar o próprio GroupId
        # DENTRO dela mesma -> "Circular dependency" no CloudFormation. Numa regra
        # à parte, a referência fica numa direção só.
        for port in (8000, 3000):
            ec2.CfnSecurityGroupIngress(
                self,
                f"SelfIngress{port}",
                group_id=sg.security_group_id,
                ip_protocol="tcp",
                from_port=port,
                to_port=port,
                source_security_group_id=sg.security_group_id,
                description="interno (Edge para API e Grafana)",
            )

        subnet_id = vpc.public_subnets[0].subnet_id

        def make(name: str, itype: str, script: str) -> ec2.CfnInstance:
            return ec2.CfnInstance(
                self,
                name,
                image_id=ami_id,
                instance_type=itype,
                key_name="vockey",
                iam_instance_profile="LabInstanceProfile",
                subnet_id=subnet_id,
                security_group_ids=[sg.security_group_id],
                user_data=Fn.base64(script),
                tags=[
                    CfnTag(key="Name", value=name),
                    CfnTag(key="project", value="cloudtask-demo"),
                ],
            )

        # --- Elastic IP + hostname sslip.io ---------------------------------
        # O hostname `<ip-com-tracos>.sslip.io` resolve para o IP do Edge — dá um
        # NOME para o ACME validar (cert válido) sem domínio próprio. Montado a
        # partir do IP do EIP: troca '.' por '-' e concatena '.sslip.io'.
        eip = ec2.CfnEIP(self, "EdgeEip", domain="vpc",
                         tags=[CfnTag(key="project", value="cloudtask-demo")])
        host = Fn.join("", [Fn.join("-", Fn.split(".", eip.ref)), ".sslip.io"])

        # --- API (Docker; conecta no RDS) -----------------------------------
        api_head = (
            "#!/bin/bash\n"
            f"export ADMIN_PASSWORD='{admin_password}'\n"
            f"export SECRET_KEY='{secret_key}'\n"
            "export ROOT_PATH='/api'\n"   # API atrás do proxy em /api (Swagger Server)
        )
        if db_secret_name:
            # Lê a credencial do RDS no Secrets Manager (a instância usa a LabRole,
            # que tem secretsmanager:GetSecretValue) e monta a DATABASE_URL. Com
            # ela setada, o userdata-api.sh conecta no RDS (não sobe Postgres local).
            api_head += (
                "dnf install -y jq\n"
                f"SEC=$(aws secretsmanager get-secret-value --secret-id {db_secret_name} "
                "--query SecretString --output text)\n"
                'export DATABASE_URL="postgresql+psycopg2://'
                '$(echo "$SEC"|jq -r .username):$(echo "$SEC"|jq -r .password)@'
                '$(echo "$SEC"|jq -r .host):$(echo "$SEC"|jq -r .port)/'
                '$(echo "$SEC"|jq -r .dbname)"\n'
            )
        api = make("cloudtask-api", "t3.small", api_head + _body(_SERVERS / "userdata-api.sh"))

        # Se há RDS, libera 5432 no SG do RDS a partir do SG dos EC2.
        # POR QUÊ um CfnSecurityGroupIngress AQUI (e não
        # ``db.connections.allow_default_port_from(sg)``): aquele método criaria a
        # regra DENTRO da DatabaseStack referenciando ESTA ComputeStack — e como
        # a Compute também depende da Database (VPC/SG do RDS), vira dependência
        # CIRCULAR. No deploy em ordem fixa (Database antes de Compute) isso
        # falha com "No export named CloudTaskCompute:...DemoSg...". Criando a
        # regra aqui (a Compute já depende da Database), a referência fica numa
        # direção só e o deploy passa.
        if db is not None and hasattr(db, "connections"):
            ec2.CfnSecurityGroupIngress(
                self,
                "ApiToRds",
                group_id=db.connections.security_groups[0].security_group_id,
                ip_protocol="tcp",
                from_port=5432,
                to_port=5432,
                source_security_group_id=sg.security_group_id,
                description="API EC2 para RDS 5432",
            )

        # --- Grafana (subpath /grafana + dashboard como home) ---------------
        dash_b64 = base64.b64encode(
            (_SERVERS / "grafana-dashboard.json").read_bytes()
        ).decode()
        graf_head = (
            "#!/bin/bash\n"
            f"export ADMIN_PASSWORD='{admin_password}'\n"
            f"export REGION='{self.region}'\n"
            f"export DASH_B64='{dash_b64}'\n"
            + Fn.join("", ["export ROOT_URL='https://", host, "/grafana/'\n"])
        )
        graf = make(
            "cloudtask-grafana", "t3.small",
            graf_head + _body(_SERVERS / "userdata-grafana.sh"),
        )

        # --- Edge (Caddy: TLS + SPA + proxy) --------------------------------
        html_b64 = base64.b64encode(
            gzip.compress(_FRONT_HTML.read_bytes(), mtime=0)  # mtime=0 => synth estável
        ).decode()
        edge_script = (
            _EDGE_TEMPLATE
            .replace("@@HTMLB64@@", html_b64)
            .replace("@@ADMINPW@@", admin_password)
            .replace("@@HOST@@", host)
            .replace("@@APIIP@@", api.attr_private_ip)
            .replace("@@GRAFIP@@", graf.attr_private_ip)
        )
        edge = make("cloudtask-edge", "t3.small", edge_script)

        # Associa o Elastic IP ao Edge (o hostname sslip.io aponta para ele).
        ec2.CfnEIPAssociation(self, "EdgeEipAssoc",
                              allocation_id=eip.attr_allocation_id,
                              instance_id=edge.ref)

        # --- Saídas (links HTTPS prontos) -----------------------------------
        CfnOutput(self, "FrontendUrl", value=Fn.join("", ["https://", host, "/"]),
                  description="Abra este link (SPA). Login: admin / admin#123")
        CfnOutput(self, "ApiUrl", value=Fn.join("", ["https://", host, "/api/docs"]),
                  description="Swagger da API (com senha: admin / admin#123)")
        CfnOutput(self, "GrafanaUrl", value=Fn.join("", ["https://", host, "/grafana/"]),
                  description="Grafana (admin / admin#123)")
