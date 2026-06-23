# Prática 19 — Três servidores (API + Frontend + Grafana) na AWS (Aula 12)

> **Objetivo:** subir a aplicação completa como ela seria em produção: a **API**
> num servidor, o **frontend** (site) em outro e o **Grafana** (observabilidade)
> em um terceiro — cada um num EC2 separado. No fim você abre um **link externo
> real** no navegador, faz login e usa o app.
>
> **Quando:** Semana 6 / Aula 12.
>
> **Pré-req:** AWS Academy (Learner Lab) iniciado e credenciais no terminal
> (ver [`00-setup-inicial-e-aws-academy.md`](00-setup-inicial-e-aws-academy.md)).
> Conceitos por trás: [`../conceitos/aws-compute.md`](../conceitos/aws-compute.md),
> a IaC da [prática 18](18-cdk-iac.md) e os eventos/observabilidade da
> [prática 15](15-eventos-dynamodb.md).
>
> ⚠️ **Custo:** três EC2 pequenos (2× `t3.small` + 1× `t3.micro`) custam centavos
> por hora e **não usam NAT**. Se você também subir o RDS (caminho CDK), aí sim
> cobra mais — **destrua tudo ao terminar** (passo 6).

---

## 1. O desenho (um Edge HTTPS na frente de três servidores)

Até agora a API, o banco e os anexos rodavam juntos. Em produção a gente
**separa responsabilidades** e coloca **um único ponto seguro** (o *Edge*) na
frente — só ele fala com a internet, **em HTTPS com certificado válido**:

```text
   navegador ──HTTPS (cert válido)──► EDGE (Caddy)  ──HTTP interno──►  API  (:8000)
   (443)                              <ip>.sslip.io  ├─ /api/*      ──►  Grafana(:3000)
                                      serve o SPA    └─ /grafana/*        │
                                                                          └─► CloudWatch
```

* **Edge** — um **Caddy** que: serve o `frontend/index.html` (login + kanban +
  anexos), faz **proxy** `/api`→API e `/grafana`→Grafana, e obtém **sozinho um
  certificado válido** (HTTPS). Tem um **Elastic IP** + hostname `sslip.io`.
* **API** — a mesma imagem Docker das aulas anteriores, agora com **login por
  token (JWT)**. Usuário `admin`, senha `admin#123`. **Não** fica exposta à
  internet (porta 8000 só dentro do security group).
* **Grafana** — sobe já **provisionado**: datasource **CloudWatch** (sem chave
  fixa — usa a *role* do EC2) + um dashboard com gráficos, na home. Também só
  acessível pelo Edge (`/grafana`).

> Toda a parte de segurança (login/token, `/api` como Server, o **servidor de
> certificado**, Swagger com senha) está detalhada na
> [prática 21](21-seguranca-https-auth.md) e na teoria
> [`seguranca-aula12-auth-proxy-cert.md`](../conceitos/seguranca-aula12-auth-proxy-cert.md).

---

## 2. Segurança (o que mudou na API)

A API agora **exige token** nas rotas de dados. O fluxo:

1. `POST /auth/login` com `{"username":"admin","password":"admin#123"}` → devolve
   um `access_token`.
2. As chamadas a `/tasks`, `/uploads`, `/events` precisam do cabeçalho
   `Authorization: Bearer <token>` — sem ele, **401**.

A mesma senha `admin#123` é usada de propósito em tudo (banco, app, Grafana)
**só porque é uma demo**. Em produção: senhas diferentes, fortes e fora do
código (Secrets Manager, como o RDS já faz).

> 🔐 **Como seria em produção de verdade (e por que aqui é diferente):** o ideal
> é **não** autenticar dentro do próprio backend. Em produção colocaríamos um
> **servidor de autenticação separado** — por exemplo o **Authentik** — num
> servidor/host próprio (mais um EC2, ou um serviço gerenciado). Vantagens:
> centraliza login/usuários, fala OAuth2/OIDC, e — importante — **mantém a
> emissão/validação de credenciais e os certificados TLS isolados** do backend.
> Gerenciar certificado dentro de cada serviço aumenta a **superfície de
> exposição** (um vazamento no backend levaria junto o material de autenticação).
> Aqui, por **limitação do laboratório** (1 sessão curta, sem domínio/DNS nem
> gestão de certs própria), simplificamos: a autenticação (JWT) roda **no mesmo
> container do backend**. É suficiente para a demo, mas a separação é o que se
> faria "para valer".

---

## 3. Caminho A — script CLI (rápido)

O jeito mais direto de ver tudo no ar. Na raiz do repositório:

```bash
bash infra/servers/semana-06-servidores-subir.sh
```

O script: acha a AMI Amazon Linux 2023 mais nova, aloca um **Elastic IP**, cria
um **security group** (22/80/443 abertos; 8000/3000 **só dentro** do grupo) e
sobe os três EC2 — gerando o Edge (Caddy) com o SPA e a config de TLS/proxy. No
fim ele imprime algo assim:

```text
  App (abra este):    https://SEU-IP.sslip.io/
  Swagger (c/ senha): https://SEU-IP.sslip.io/api/docs   (admin / admin#123)
  Grafana:            https://SEU-IP.sslip.io/grafana/   (admin / admin#123)
```

Espere **~3–5 min** (a API faz `docker build`; o Caddy emite o certificado) e
abra o link do **App**. Login: `admin` / `admin#123`. Tudo é **HTTPS** — `http://`
redireciona para `https://`.

> Os servidores usam o **`LabInstanceProfile`** (a *role* do laboratório, já
> pronta) — por isso o Grafana lê o CloudWatch sem você configurar credencial.

---

## 4. Caminho B — IaC com CDK (a 7ª stack)

O mesmo resultado, agora **versionado**: a `ComputeStack` descreve os três EC2.
Ela reutiliza os **mesmos** scripts de `infra/servers/` como `user-data`, então
não há divergência entre o caminho A e o B.

```bash
cd infra/cdk
cat cdk.out/CloudTaskCompute.template.json   # (depois do synth) só p/ espiar
./semana-06-cdk-deploy.sh deploy                       # sobe TODAS as stacks, em ordem
```

Diferença importante do caminho B: como a `DatabaseStack` (RDS) sobe antes, a
API se conecta ao **RDS gerenciado** (lendo a senha do **Secrets Manager**), em
vez de um Postgres em container. É a versão "produção".

> Por que isso funciona no Academy sem `cdk bootstrap`: a stack **não cria IAM**
> (usa o `LabInstanceProfile` existente) e **não tem assets** (o HTML do
> frontend e o dashboard do Grafana vão embutidos em base64 no template). Mesmo
> truque da [prática 18](18-cdk-iac.md).

Repare no salto de complexidade: agora são **3 servidores + RDS + VPC + security
group**, todos amarrados (o frontend depende da API, a API depende do RDS). Na
mão isso seria frágil e demorado; com **CDK** vira **um** `deploy`/`destroy`, na
ordem certa, versionado e revisável. Quanto **maior** a infra, **maior** o ganho
de descrevê-la como código — é justamente o que esta semana quer mostrar (mais
detalhes em [como o CDK funciona por dentro](20-cdk-python-por-dentro.md)).

---

## 5. O que olhar no Grafana

Abra `https://SEU-IP.sslip.io/grafana/` (admin / admin#123) → ele já entra no
dashboard **“CloudTask — Infra (Academy)”** (definido como *home*). Use o seletor
**EC2 Instance** no topo para filtrar. Painéis:

* **CPU dos EC2 (%)** e **Rede de saída** — saúde das três máquinas.
* **DynamoDB — capacidade consumida** — aparece quando a API grava eventos.
* **RDS — conexões ativas** — aparece se você subiu o RDS (caminho B).

As métricas levam alguns minutos para popular (o CloudWatch agrega de 1 em 1
min).

---

## 6. Limpeza (faça SEMPRE) 🔥

```bash
# Caminho A (script):
bash infra/servers/semana-06-servidores-destruir.sh

# Caminho B (CDK):
cd infra/cdk && ./semana-06-cdk-deploy.sh destroy
```

Confira no Console (EC2 → Instances; RDS → Databases) que **nada** ficou
`running`/`available`. O RDS é o que mais cobra — não deixe ligado.

---

## 7. Resumo

| Peça | Servidor | Acesso (público) | Login |
| --- | --- | --- | --- |
| Edge (Caddy + SPA) | `t3.small` | `https://<ip>.sslip.io/` (443, **cert válido**) | `admin` / `admin#123` |
| API (FastAPI) | `t3.small` Docker | só via Edge: `/api/...` (token Bearer) | token via `/api/auth/login` |
| Grafana | `t3.small` | só via Edge: `/grafana/` | `admin` / `admin#123` |

Você subiu uma arquitetura de **produção de verdade** — Edge HTTPS com
certificado válido, backend com **autenticação por token** e observabilidade —
pelos **dois** caminhos (script e IaC), terminando a jornada
**console → CLI → script → IaC** da disciplina. A segurança em detalhe:
[prática 21](21-seguranca-https-auth.md).
