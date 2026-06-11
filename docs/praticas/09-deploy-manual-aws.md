# Prática 09 — Deploy manual na AWS (ECR → Fargate / EKS, RDS, Secrets)

> **Objetivo:** subir a aplicação CloudTask na AWS **manualmente** (sem
> Terraform/CDK), usando AWS CLI e Console. Cobre o caminho **mais simples**
> (ECS Fargate) e o **caminho oficial do curso** (EKS), além de:
> - linkar o código do GitHub ao build na AWS,
> - configurar `.env` em **Secrets Manager**,
> - subir o banco em **container** OU em **RDS**, comparando custo e
>   complexidade.
>
> **Conceito de base obrigatório:** [`../conceitos/infra-aws-minima-por-semana.md`](../conceitos/infra-aws-minima-por-semana.md).
>
> **Pré-req:** [`00-setup-inicial-e-aws-academy.md`](00-setup-inicial-e-aws-academy.md)
> concluído (AWS CLI funcionando, Learner Lab ativo, `kubectl`, `eksctl`).

---

## Mapa do que **cada semana** faz aqui

| Etapa | Quando | Seção |
| --- | :---: | --- |
| **A.** Criar bucket S3 (sanity check) | Semana 3 | [§1](#1-semana-3--bucket-s3-sanity-check) |
| **B.** Linkar repo GitHub → AWS (CodeBuild) | Semana 4 | [§2](#2-semana-4--linkar-github-na-aws-via-codebuild) |
| **C.** Push da imagem para ECR | Semana 4 | [§3](#3-semana-4--push-da-imagem-para-ecr) |
| **D.** Subir API em **ECS Fargate** (atalho simples) | Semana 4 (opcional) | [§4](#4-semana-4-opcional--ecs-fargate-deploy-simples) |
| **E.** Provisionar **EKS** com `eksctl` | Semana 5 | [§5](#5-semana-5--provisionar-eks-com-eksctl) |
| **F.** Subir API no EKS com Postgres em **container** | Semana 5 | [§6](#6-semana-5--subir-api-no-eks-com-postgres-em-container) |
| **G.** Trocar Postgres por **RDS** | Semana 6/8 | [§7](#7-semana-68--trocar-postgres-por-rds) |
| **H.** Configurar `.env` via **Secrets Manager** | Semana 6 | [§8](#8-semana-6--secrets-manager-para-env) |
| **I.** HPA + load test | Semana 6 | [§9](#9-semana-6--hpa--load-test) |
| **J.** Eventos em **DynamoDB** | Semana 6 | [§10](#10-semana-6--dynamodb-para-eventos) |
| **K.** **Cleanup obrigatório** ao fim de toda aula | Sempre | [§11](#11-sempre--cleanup-obrigatorio) |

> ⚠️ **Numeração de semana** segue [`ROADMAP.md`](../ROADMAP.md). A demo final
> em ALB + ACM + Route 53 + EKS roda na **conta pessoal do professor** (não
> no Learner Lab) — não está nesta prática (vira material do professor).

---

## 0. Antes de cada sessão

```bash
# 1. abrir Learner Lab no AWS Academy → Start Lab → AWS Details → AWS CLI
# 2. copiar o bloco e colar em ~/.aws/credentials no HOST (não no container)
# 3. validar dentro do devcontainer
aws sts get-caller-identity
# saída deve ter "Account" e "Arn"

# 4. region default
aws configure set region us-east-1
```

> ⚠️ Credenciais do Learner Lab expiram em ~4 h. Quando acabar, recole.

---

## 1. Semana 3 — Bucket S3 (sanity check)

> **Quando:** Aula 5. **Já coberto** na prática [`06-uploads-modo-s3.md`](06-uploads-modo-s3.md).
> Aqui só lembramos o resumo.

**Linux/macOS (bash):**
```bash
export BUCKET=cloudtask-uploads-$(whoami)-$(date +%s)
aws s3 mb s3://$BUCKET --region us-east-1
echo "Bucket: $BUCKET"
```

**Windows (PowerShell):**
```powershell
# nome do bucket deve ser minúsculo e sem espaços
$BUCKET = "cloudtask-uploads-$($env:USERNAME.ToLower())-$([DateTimeOffset]::UtcNow.ToUnixTimeSeconds())"
aws s3 mb "s3://$BUCKET" --region us-east-1
echo "Bucket: $BUCKET"
```

Aponta no `.env`:

```env
STORAGE_MODE=s3
AWS_REGION=us-east-1
S3_BUCKET_NAME=cloudtask-uploads-...
```

**Cleanup:** `aws s3 rb s3://$BUCKET --force`.

---

## 2. Semana 4 — Linkar GitHub na AWS (via CodeBuild)

> **Quando:** **Aula 7**. **Opcional** — também pode buildar localmente e dar
> `docker push`. Mas conectar o GitHub ensina **pipeline real**.

### Por que CodeBuild e não Actions/Jenkins?

CodeBuild é **serverless** (paga só por minuto rodando), nativo da AWS e
integra com ECR/EKS sem extra. Para esta disciplina, é o caminho mais
didático para **ver o pipeline acontecer dentro da AWS**.

> Limite Learner Lab: o CodeBuild **roda**, mas a role `voclabs` **não
> autoriza** `codebuild:ImportSourceCredentials` (conectar GitHub privado)
> nem webhooks. No Academy a fonte do build vem de um **zip no S3**
> ([§2.3-AWS_ACADEMY](#23-aws_academy--fonte-do-build-via-s3-sem-github)) e o build
> é disparado **on-demand** (manual).

### Passos

#### 2.1. Criar `buildspec.yml` na raiz do repo

```yaml
# buildspec.yml — usado pelo CodeBuild
version: 0.2
phases:
  pre_build:
    commands:
      - echo "Login no ECR..."
      - aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REPO_URI
      - IMAGE_TAG=v$(date +%Y%m%d-%H%M%S)
  build:
    commands:
      - echo "Build da imagem (target prod)..."
      - docker build --target prod -t cloudtask-api:$IMAGE_TAG .
      - docker tag cloudtask-api:$IMAGE_TAG $ECR_REPO_URI:$IMAGE_TAG
      - docker tag cloudtask-api:$IMAGE_TAG $ECR_REPO_URI:latest
  post_build:
    commands:
      # O CodeBuild roda post_build mesmo se o build falhar. Sem este guard,
      # um build quebrado tenta o push e gera "image does not exist locally".
      - |
        if [ "$CODEBUILD_BUILD_SUCCEEDING" = "0" ]; then
          echo "Build falhou — pulando push para o ECR."
          exit 1
        fi
      - echo "Push para ECR..."
      - docker push $ECR_REPO_URI:$IMAGE_TAG
      - docker push $ECR_REPO_URI:latest
```

> 💡 **Imagem base via mirror ECR Public:** o `Dockerfile` usa
> `public.ecr.aws/docker/library/python:3.11-slim` (mirror oficial do Docker
> Hub na AWS) em vez de `python:3.11-slim`. No CodeBuild os IPs são
> compartilhados e o pull anônimo do Docker Hub estoura o **rate limit**
> (`429 Too Many Requests`); o mirror da AWS não tem esse limite e dispensa
> login.

Commitar e empurrar.

#### 2.2. Criar token GitHub (PAT apenas conta AWS PRÓPRIA)

1. GitHub → Settings → Developer Settings → Personal Access Tokens → Tokens (classic).
2. Permissões mínimas: `repo` (público) ou `repo` + `read:org` (privado).
3. Copie o token (`ghp_...`).

#### 2.3-AWS_PROPRIA — Conectar o GitHub no CodeBuild via CLI

> ⚠️ **Este comando só funciona em conta AWS própria/privada** (com IAM
> amplo). **No AWS Academy / Learner Lab ele FALHA** — a role `voclabs` não
> tem a permissão `codebuild:ImportSourceCredentials`:
>
> ```text
> An error occurred (AccessDeniedException) when calling the
> ImportSourceCredentials operation: User: arn:aws:sts::...:assumed-role/
> voclabs/... is not authorized to perform: codebuild:ImportSourceCredentials
> ```
>
> Não há como liberar essa permissão no Academy (IAM travado). **Se você
> está no Learner Lab, pule este comando** e use a alternativa via S3 logo
> abaixo ([§2.3-AWS_ACADEMY](#23-aws_academy--fonte-do-build-via-s3-sem-github)).

Em **conta própria**:

```bash
aws codebuild import-source-credentials \
  --server-type GITHUB \
  --auth-type PERSONAL_ACCESS_TOKEN \
  --token "ghp_SEU_TOKEN_AQUI"
```

#### 2.3-AWS_ACADEMY — Fonte do build via S3 (sem GitHub)

No Learner Lab o CodeBuild não consegue clonar o GitHub (sem
`ImportSourceCredentials`). Solução permitida pela role `voclabs`:
**empacotar o código num zip, subir num bucket S3 e apontar o CodeBuild
para esse zip**.

**Linux/macOS (bash):**
```bash
# 0. (uma vez) descobrir o ACCOUNT_ID — usado aqui e na §3
export ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "Account: $ACCOUNT_ID"

# 1. criar (ou reutilizar) um bucket para o codigo-fonte
export SRC_BUCKET=cloudtask-src-$ACCOUNT_ID
aws s3 mb s3://$SRC_BUCKET --region us-east-1

# 2. zipar o repo (sem .git e sem lixo) e enviar ao S3
zip -r /tmp/source.zip . -x '.git/*' '*/__pycache__/*' '*.pyc'
aws s3 cp /tmp/source.zip s3://$SRC_BUCKET/source.zip

# 3. confirmar
aws s3 ls s3://$SRC_BUCKET/
```

**Windows (PowerShell):**
```powershell
# 0. (uma vez) descobrir o ACCOUNT_ID — usado aqui e na §3
$env:ACCOUNT_ID = aws sts get-caller-identity --query Account --output text
echo "Account: $env:ACCOUNT_ID"

# 1. criar (ou reutilizar) um bucket para o codigo-fonte
$env:SRC_BUCKET = "cloudtask-src-$env:ACCOUNT_ID"
aws s3 mb "s3://$env:SRC_BUCKET" --region us-east-1

# 2. zipar o repo e enviar ao S3 (Compress-Archive no lugar do zip).
#    Remova .git/__pycache__ antes para não inflar o pacote.
Compress-Archive -Path * -DestinationPath "$env:TEMP\source.zip" -Force
aws s3 cp "$env:TEMP\source.zip" "s3://$env:SRC_BUCKET/source.zip"

# 3. confirmar
aws s3 ls "s3://$env:SRC_BUCKET/"
```

No projeto do CodeBuild (passo 2.4), em vez de **Source: GitHub**, escolha
**Source: Amazon S3** e informe `s3://<SEU_SRC_BUCKET>/source.zip`. O resto
(buildspec, env vars, LabRole) é idêntico.

> 💡 A cada mudança no código, refaça o `zip` + `aws s3 cp` e dispare o
> build de novo. É o "git push" manual do Academy.

#### 2.4. Criar o projeto CodeBuild

> 🟢 **AWS Academy (Learner Lab):** crie pelo **Console** (caminho A) — a
> role `voclabs` não autoriza tudo via CLI (criar role IAM, webhook etc.).
>
> 🔵 **Conta AWS própria:** dá para criar **tudo via CLI** (caminho B):
> role IAM + projeto + webhook de `git push`.

**A) Via Console (Academy e conta própria):**

1. Console → CodeBuild → Create build project.
2. **Source:** GitHub → seu repo → branch `semana-04-eks-aws`.
   - **No Academy:** escolha **Amazon S3** → `s3://cloudtask-src-<ACCOUNT_ID>/source.zip`
     (ver [§2.3-AWS_ACADEMY](#23-aws_academy--fonte-do-build-via-s3-sem-github)).
3. **Environment:**
   - Managed image, Ubuntu, Standard 7.0.
   - Privileged: **ON** (necessário para `docker build`).
   - Service role: **LabRole** (única disponível no Academy).
4. **Buildspec:** Use a buildspec file → `buildspec.yml`.
5. **Env vars:**
   - `AWS_REGION` = `us-east-1`
   - `ECR_REPO_URI` = (preencher depois de criar repo na §3)
6. Create build project → Start build (manual).

**B) Via CLI (apenas conta AWS PRÓPRIA):**

Pré-req: token GitHub já importado na §2.3-AWS_PROPRIA — é com essa credencial que o
CodeBuild clona o repo.

**Linux/macOS (bash):**
```bash
# 0. ACCOUNT_ID (se ainda não exportou nesta sessão)
export ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# 1. criar a role IAM que o CodeBuild assume (na conta própria não existe
#    LabRole — você cria a sua; trust policy = "CodeBuild pode me assumir")
aws iam create-role \
  --role-name codebuild-cloudtask-role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": { "Service": "codebuild.amazonaws.com" },
      "Action": "sts:AssumeRole"
    }]
  }'

# 2. permissões do build: escrever logs no CloudWatch + dar push no ECR.
#    Policies gerenciadas para simplificar a aula; em produção, aperte
#    para o repositório/log group específicos.
aws iam attach-role-policy --role-name codebuild-cloudtask-role \
  --policy-arn arn:aws:iam::aws:policy/CloudWatchLogsFullAccess
aws iam attach-role-policy --role-name codebuild-cloudtask-role \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPowerUser

# 3. criar o projeto apontando direto para o GitHub
#    (troque SEU_USUARIO/SEU_REPO; privilegedMode=true libera docker build)
#    Se der "Invalid service role": a role do passo 1 ainda nao propagou no
#    IAM. Aguarde ~1 min e repita ESTE comando (nao recrie a role).
aws codebuild create-project \
  --name cloudtask-api \
  --source "type=GITHUB,location=https://github.com/SEU_USUARIO/SEU_REPO.git,buildspec=buildspec.yml" \
  --source-version semana-04-eks-aws \
  --artifacts type=NO_ARTIFACTS \
  --environment "type=LINUX_CONTAINER,image=aws/codebuild/standard:7.0,computeType=BUILD_GENERAL1_SMALL,privilegedMode=true,environmentVariables=[{name=AWS_REGION,value=us-east-1},{name=ECR_REPO_URI,value=$ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/cloudtask-api}]" \
  --service-role arn:aws:iam::${ACCOUNT_ID}:role/codebuild-cloudtask-role

# 4. (opcional) webhook: dispara build automático a cada git push na branch
aws codebuild create-webhook \
  --project-name cloudtask-api \
  --filter-groups '[[{"type":"EVENT","pattern":"PUSH"},{"type":"HEAD_REF","pattern":"^refs/heads/semana-04-eks-aws$"}]]'
```

**Windows (PowerShell):**
```powershell
# 0. ACCOUNT_ID (se ainda não exportou nesta sessão)
$env:ACCOUNT_ID = aws sts get-caller-identity --query Account --output text

# 1. criar a role IAM que o CodeBuild assume (na conta própria não existe
#    LabRole — você cria a sua). Here-string @'...'@ preserva o JSON.
$trust = @'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Service": "codebuild.amazonaws.com" },
    "Action": "sts:AssumeRole"
  }]
}
'@
aws iam create-role `
  --role-name codebuild-cloudtask-role `
  --assume-role-policy-document $trust

# 2. permissões do build: logs no CloudWatch + push no ECR
aws iam attach-role-policy --role-name codebuild-cloudtask-role `
  --policy-arn arn:aws:iam::aws:policy/CloudWatchLogsFullAccess
aws iam attach-role-policy --role-name codebuild-cloudtask-role `
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPowerUser

# 3. criar o projeto apontando direto para o GitHub
#    (troque SEU_USUARIO/SEU_REPO; privilegedMode=true libera docker build)
#    Se der "Invalid service role": a role do passo 1 ainda nao propagou no
#    IAM. Aguarde ~1 min e repita ESTE comando (nao recrie a role).
aws codebuild create-project `
  --name cloudtask-api `
  --source "type=GITHUB,location=https://github.com/SEU_USUARIO/SEU_REPO.git,buildspec=buildspec.yml" `
  --source-version semana-04-eks-aws `
  --artifacts type=NO_ARTIFACTS `
  --environment "type=LINUX_CONTAINER,image=aws/codebuild/standard:7.0,computeType=BUILD_GENERAL1_SMALL,privilegedMode=true,environmentVariables=[{name=AWS_REGION,value=us-east-1},{name=ECR_REPO_URI,value=${env:ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/cloudtask-api}]" `
  --service-role "arn:aws:iam::${env:ACCOUNT_ID}:role/codebuild-cloudtask-role"

# 4. (opcional) webhook: dispara build automático a cada git push na branch
$filters = @'
[[{"type":"EVENT","pattern":"PUSH"},{"type":"HEAD_REF","pattern":"^refs/heads/semana-04-eks-aws$"}]]
'@
aws codebuild create-webhook `
  --project-name cloudtask-api `
  --filter-groups $filters
```

> ⚠️ **`Invalid service role` no `create-project`?** Duas causas:
> 1. **zsh comeu a ARN** — `$ACCOUNT_ID:role/...` em zsh vira
>    `...<id>ole/...` (o `:r` é modificador). Por isso a ARN usa
>    `${ACCOUNT_ID}` com chaves. Se persiste **mesmo após esperar**, é isto.
> 2. **Propagação IAM** — role recém-criada ainda não propagou. **Aguarde
>    ~1 min e repita** (a role está correta). Não recrie a role.
>
> 💡 A env var `ECR_REPO_URI` já aponta para o repositório da §3 — **crie o
> repo ECR ([§3.1](#31-criar-o-repositório-ecr--descobrir-o-acct)) antes do
> primeiro build**, senão o `docker push` falha.
>
> 💡 O webhook (passo 4) é o que transforma o build manual em **CI de
> verdade**: cada `git push` na branch dispara o pipeline sozinho. No
> Academy ele não existe (sem credencial GitHub) — lá o "git push" é o
> re-zip + `aws s3 cp` da [§2.3-AWS_ACADEMY](#23-aws_academy--fonte-do-build-via-s3-sem-github).

**Resultado:** CodeBuild puxa o código (GitHub ou zip no S3), faz
`docker build`, e dá push pro ECR.

---

## 3. Semana 4 — Push da imagem para ECR

> **Quando:** Aula 7. Duas formas de colocar a imagem no ECR:
> - **A) Deploy direto** — build local + `docker push` (rápido, sem pipeline).
> - **B) Via CodeBuild** — a AWS builda e dá push (usa o projeto da §2).
>
> Os dois precisam do **repositório ECR criado** primeiro (3.1).

> ⚠️ **Não confunda os dois eixos:**
> - **Caminho A vs B** = *onde* o build roda (sua máquina vs nuvem/CodeBuild).
> - **Conta própria vs Academy** = *qual* conta AWS (IAM amplo vs `voclabs`).
>
> São independentes. O **Caminho A** é **igual** nas duas contas (build é
> local). O **Caminho B** é o único que diverge — a **fonte** do build muda:
> GitHub (própria) ou zip no S3 (Academy) — daí o split `3.3-AWS_PROPRIA` /
> `3.3-AWS_ACADEMY`.

### 3.1. Criar o repositório ECR + descobrir o `<acct>`

O `<acct>` é o **ID numérico da conta** (12 dígitos) e aparece em **toda
URI do ECR**. Pegue-o por CLI — vale para conta própria **e** Learner Lab:

**Linux/macOS (bash):**
```bash
# ID da conta (12 dígitos) — é o <acct> das URIs
export ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "Account: $ACCOUNT_ID"

# criar o repositorio (idempotente: ignora erro se ja existir)
aws ecr create-repository \
  --repository-name cloudtask-api \
  --region us-east-1 2>/dev/null || true

# montar a URI completa do repositorio
export ECR=$ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/cloudtask-api
echo "ECR URI: $ECR"
```

**Windows (PowerShell):**
```powershell
# ID da conta (12 digitos) — e o <acct> das URIs
$env:ACCOUNT_ID = aws sts get-caller-identity --query Account --output text
echo "Account: $env:ACCOUNT_ID"

# criar o repositorio. Se ja existir, o aws sai com erro, mas o exit code
# de um .exe nao interrompe o PowerShell; 2>$null só esconde a mensagem.
aws ecr create-repository `
  --repository-name cloudtask-api `
  --region us-east-1 2>$null

# montar a URI completa do repositorio
$env:ECR = "$env:ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/cloudtask-api"
echo "ECR URI: $env:ECR"
```

> 💡 Pelo Console o `<acct>` também aparece no **canto superior direito**
> (Account ID) e na própria URI em **ECR → Repositories**.

### 3.2. Caminho A — build local + push direto (sem CodeBuild)

> Mesmo procedimento em **conta própria e Academy** — o build roda na **sua
> máquina** e só o push vai pra nuvem, então não depende de role/CodeBuild.
> (A diferença conta-própria-vs-Academy aparece no **Caminho B**, §3.3.)

**Linux/macOS (bash/zsh):**
```bash
# 1. login no ECR (usa o $ECR da 3.1)
aws ecr get-login-password --region us-east-1 \
  | docker login --username AWS --password-stdin $ECR

# 2. build prod
docker build --target prod -t cloudtask-api:v0.4.0 .

# 3. tag + push — SEMPRE use ${ECR}:tag com chaves (ver nota abaixo)
docker tag cloudtask-api:v0.4.0 ${ECR}:v0.4.0
docker tag cloudtask-api:v0.4.0 ${ECR}:latest
docker push ${ECR}:v0.4.0
docker push ${ECR}:latest

# 4. listar
aws ecr list-images --repository-name cloudtask-api
```

> ⚠️ **Use `${ECR}:latest`, não `$ECR:latest`.** No **zsh** (shell padrão do
> macOS), `$ECR:l` é o **modificador `:l`** (lowercase): ele come o `:l` e
> sobra `atest`, virando `cloudtask-apiatest` → `name unknown: repository
> does not exist`. As chaves `${ECR}` delimitam o nome da variável e evitam
> isso. No bash puro não acontece, mas `${ECR}` funciona nos dois.

**Windows (PowerShell):**
```powershell
# 1. login no ECR (usa o $env:ECR da 3.1)
aws ecr get-login-password --region us-east-1 `
  | docker login --username AWS --password-stdin $env:ECR

# 2. build prod
docker build --target prod -t cloudtask-api:v0.4.0 .

# 3. tag + push (chaves em ${env:ECR} separam o nome da var do ":tag")
docker tag cloudtask-api:v0.4.0 "${env:ECR}:v0.4.0"
docker tag cloudtask-api:v0.4.0 "${env:ECR}:latest"
docker push "${env:ECR}:v0.4.0"
docker push "${env:ECR}:latest"

# 4. listar
aws ecr list-images --repository-name cloudtask-api
```

> 💡 `target prod` garante imagem **sem dev tools** (menor superfície de
> ataque + imagem menor).

### 3.3. Caminho B — build via CodeBuild (push automático)

Reaproveita o projeto da §2 e o `buildspec.yml` (§2.1: login, build `target
prod`, tag e push) — o CodeBuild executa tudo na nuvem. A **única** diferença
entre as contas é a **fonte** do build: GitHub (própria) ou zip no S3
(Academy). Por isso este caminho se divide em dois abaixo.

#### 3.3-AWS_PROPRIA — fonte GitHub

A fonte já é o GitHub (configurada na §2.4). Cada `git push` na branch já
dispara o build pelo **webhook** (§2.4); para disparar **manualmente**:

**Linux/macOS (bash):**
```bash
# 1. disparar o build (use o NOME do projeto criado na 2.4)
export BUILD_ID=$(aws codebuild start-build \
  --project-name cloudtask-api \
  --query 'build.id' --output text)
echo "Build: $BUILD_ID"

# 2. acompanhar o status (repita ate SUCCEEDED; ~2-4 min)
aws codebuild batch-get-builds --ids $BUILD_ID \
  --query 'builds[0].buildStatus' --output text
# IN_PROGRESS -> SUCCEEDED

# 3. confirmar a imagem no ECR
aws ecr list-images --repository-name cloudtask-api
```

**Windows (PowerShell):**
```powershell
# 1. disparar o build (use o NOME do projeto criado na 2.4)
$env:BUILD_ID = aws codebuild start-build `
  --project-name cloudtask-api `
  --query 'build.id' --output text
echo "Build: $env:BUILD_ID"

# 2. acompanhar o status (repita ate SUCCEEDED; ~2-4 min)
aws codebuild batch-get-builds --ids $env:BUILD_ID `
  --query 'builds[0].buildStatus' --output text
# IN_PROGRESS -> SUCCEEDED

# 3. confirmar a imagem no ECR
aws ecr list-images --repository-name cloudtask-api
```

#### 3.3-AWS_ACADEMY — fonte zip → S3

Sem credencial GitHub, a fonte é um **zip no S3**
([§2.3-AWS_ACADEMY](#23-aws_academy--fonte-do-build-via-s3-sem-github)).
Reempacote e suba o código **antes de cada build** — é o "git push" manual
do Academy.

**Linux/macOS (bash):**
```bash
# 1. reempacotar o codigo e subir ao S3
zip -r /tmp/source.zip . -x '.git/*' '*/__pycache__/*' '*.pyc'
aws s3 cp /tmp/source.zip s3://cloudtask-src-$ACCOUNT_ID/source.zip

# 2. disparar o build
export BUILD_ID=$(aws codebuild start-build \
  --project-name cloudtask-api \
  --query 'build.id' --output text)
echo "Build: $BUILD_ID"

# 3. acompanhar o status + confirmar a imagem
aws codebuild batch-get-builds --ids $BUILD_ID \
  --query 'builds[0].buildStatus' --output text
aws ecr list-images --repository-name cloudtask-api
```

**Windows (PowerShell):**
```powershell
# 1. reempacotar o codigo e subir ao S3
Compress-Archive -Path * -DestinationPath "$env:TEMP\source.zip" -Force
aws s3 cp "$env:TEMP\source.zip" "s3://cloudtask-src-$env:ACCOUNT_ID/source.zip"

# 2. disparar o build
$env:BUILD_ID = aws codebuild start-build `
  --project-name cloudtask-api `
  --query 'build.id' --output text
echo "Build: $env:BUILD_ID"

# 3. acompanhar o status + confirmar a imagem
aws codebuild batch-get-builds --ids $env:BUILD_ID `
  --query 'builds[0].buildStatus' --output text
aws ecr list-images --repository-name cloudtask-api
```

> 💡 Se `start-build` falhar por permissão no Academy, dispare pelo Console
> (CodeBuild → projeto → **Start build**). O acompanhamento por CLI continua
> valendo.

> 💡 A env var `ECR_REPO_URI` é configurada no Console do CodeBuild
> (projeto → Edit → Environment → Env vars), não no shell:
> `ECR_REPO_URI = <acct>.dkr.ecr.us-east-1.amazonaws.com/cloudtask-api`.

**Cleanup do ECR:** seção [§11](#11-sempre--cleanup-obrigatorio).

---

## 4. Semana 4 (opcional) — ECS Fargate (deploy simples)

> **Quando:** Aula 7, **antes** de partir para EKS. Serve como
> **comparação**: "olha como Fargate é simples; agora veja o poder do EKS".
> Quem preferir ECS para o restante do curso pode — mas o curso oficial é
> EKS.

### Por que Fargate primeiro?

- Sem cluster pra gerenciar.
- Sem nó EC2.
- Cobra só pelo tempo do container ligado.
- Suba em ~5 min.

### Passos

> 🔵 **Conta AWS própria:** crie **tudo via CLI** (§4.1-AWS_PROPRIA).
>
> 🟢 **AWS Academy (Learner Lab):** crie pelo **Console** (§4.1-AWS_ACADEMY) —
> a role `voclabs` não autoriza criar a task execution role via CLI. O
> Console também serve à conta própria, se preferir clicar.

#### 4.1-AWS_PROPRIA — via CLI (apenas conta própria)

Na conta própria não existe `LabRole`: você cria a **task execution role**
(deixa o Fargate puxar do ECR e mandar logs). O resto é cluster → task
definition → rede → service.

> ⚠️ **`Role is not valid` no `register-task-definition`?** Duas causas (a #1
> derruba o resto em cascata: `TaskDefinition not found`, `Service not found`):
> 1. **zsh comeu a ARN no heredoc** — `$ACCOUNT_ID:role/...` em zsh vira
>    `...<id>ole/...` (o `:r` é modificador, igual ao `:l` do `:latest`). Por
>    isso o JSON usa `${ACCOUNT_ID}` e `${ECR}` com chaves. Confira com
>    `grep executionRoleArn /tmp/fargate-taskdef.json` — se aparecer `ole/`, é
>    isto: regere o arquivo (passo 3) e siga.
> 2. **Propagação IAM** — role do passo 1 ainda não propagou. Espere ~15 s.
>
> Se já caiu, repita só a partir do passo 3 — cluster e role já existem.
```bash
# 0. pre-req: imagem ja no ECR (§3); ACCOUNT_ID e URI
export ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export ECR=$ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/cloudtask-api

# 1. task execution role (idempotente). Trust = ecs-tasks pode assumir.
aws iam create-role --role-name ecsTaskExecutionRole \
  --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"ecs-tasks.amazonaws.com"},"Action":"sts:AssumeRole"}]}' 2>/dev/null || true
aws iam attach-role-policy --role-name ecsTaskExecutionRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

# 2. cluster Fargate
aws ecs create-cluster --cluster-name cloudtask-fargate

# 3. task definition via arquivo (evita quoting de JSON no shell)
cat > /tmp/fargate-taskdef.json <<JSON
{
  "family": "cloudtask-api",
  "requiresCompatibilities": ["FARGATE"],
  "networkMode": "awsvpc",
  "cpu": "256",
  "memory": "512",
  "executionRoleArn": "arn:aws:iam::${ACCOUNT_ID}:role/ecsTaskExecutionRole",
  "containerDefinitions": [{
    "name": "api",
    "image": "${ECR}:latest",
    "essential": true,
    "portMappings": [{"containerPort": 8000, "protocol": "tcp"}],
    "environment": [
      {"name": "DATABASE_URL", "value": "postgresql://USER:SENHA@HOST:5432/cloudtask"},
      {"name": "SECRET_KEY", "value": "troque-isto"}
    ]
  }]
}
JSON
aws ecs register-task-definition --cli-input-json file:///tmp/fargate-taskdef.json

# 4. rede: VPC default, 1 subnet publica, SG liberando 8000
export VPC_ID=$(aws ec2 describe-vpcs --filters Name=isDefault,Values=true \
  --query 'Vpcs[0].VpcId' --output text)
export SUBNET_ID=$(aws ec2 describe-subnets --filters Name=vpc-id,Values=$VPC_ID \
  --query 'Subnets[0].SubnetId' --output text)
# cria o SG; se ja existir (re-run), reaproveita o ID existente.
# Atribui SEM export (export sempre retorna 0 e mascararia a falha do $(...)).
SG_ID=$(aws ec2 create-security-group --group-name cloudtask-fargate-sg \
  --description "ECS Fargate 8000" --vpc-id $VPC_ID --query 'GroupId' --output text 2>/dev/null)
if [ -z "$SG_ID" ]; then
  SG_ID=$(aws ec2 describe-security-groups \
    --filters Name=group-name,Values=cloudtask-fargate-sg Name=vpc-id,Values=$VPC_ID \
    --query 'SecurityGroups[0].GroupId' --output text)
fi
export SG_ID
echo "SG_ID=$SG_ID"
# regra 8000 (|| true: ignora se a regra ja existir)
aws ec2 authorize-security-group-ingress --group-id $SG_ID \
  --protocol tcp --port 8000 --cidr 0.0.0.0/0 2>/dev/null || true

# 5. servico (1 task, IP publico para testar sem LB)
aws ecs create-service --cluster cloudtask-fargate --service-name cloudtask-api \
  --task-definition cloudtask-api --desired-count 1 --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_ID],securityGroups=[$SG_ID],assignPublicIp=ENABLED}"

# 6. IP publico da task (espere ~1 min ate RUNNING)
export TASK_ARN=$(aws ecs list-tasks --cluster cloudtask-fargate \
  --service-name cloudtask-api --query 'taskArns[0]' --output text)
export ENI_ID=$(aws ecs describe-tasks --cluster cloudtask-fargate --tasks $TASK_ARN \
  --query "tasks[0].attachments[0].details[?name=='networkInterfaceId'].value" --output text)
aws ec2 describe-network-interfaces --network-interface-ids $ENI_ID \
  --query "NetworkInterfaces[0].Association.PublicIp" --output text
# curl http://<IP>:8000/health
```

**Windows (PowerShell):**
```powershell
# 0. pre-req: imagem ja no ECR (§3); ACCOUNT_ID e URI
$env:ACCOUNT_ID = aws sts get-caller-identity --query Account --output text
$env:ECR = "$env:ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/cloudtask-api"

# 1. task execution role (se ja existir, o erro do .exe nao interrompe)
aws iam create-role --role-name ecsTaskExecutionRole `
  --assume-role-policy-document '{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Principal\":{\"Service\":\"ecs-tasks.amazonaws.com\"},\"Action\":\"sts:AssumeRole\"}]}' 2>$null
aws iam attach-role-policy --role-name ecsTaskExecutionRole `
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

# 2. cluster Fargate
aws ecs create-cluster --cluster-name cloudtask-fargate

# 3. task definition via arquivo (here-string @"..."@ interpola as vars)
$taskdef = @"
{
  "family": "cloudtask-api",
  "requiresCompatibilities": ["FARGATE"],
  "networkMode": "awsvpc",
  "cpu": "256",
  "memory": "512",
  "executionRoleArn": "arn:aws:iam::$($env:ACCOUNT_ID):role/ecsTaskExecutionRole",
  "containerDefinitions": [{
    "name": "api",
    "image": "$($env:ECR):latest",
    "essential": true,
    "portMappings": [{"containerPort": 8000, "protocol": "tcp"}],
    "environment": [
      {"name": "DATABASE_URL", "value": "postgresql://USER:SENHA@HOST:5432/cloudtask"},
      {"name": "SECRET_KEY", "value": "troque-isto"}
    ]
  }]
}
"@
$taskdef | Out-File -Encoding ascii "$env:TEMP\fargate-taskdef.json"
aws ecs register-task-definition --cli-input-json "file://$env:TEMP\fargate-taskdef.json"

# 4. rede: VPC default, 1 subnet publica, SG liberando 8000
$env:VPC_ID = aws ec2 describe-vpcs --filters Name=isDefault,Values=true `
  --query 'Vpcs[0].VpcId' --output text
$env:SUBNET_ID = aws ec2 describe-subnets --filters Name=vpc-id,Values=$env:VPC_ID `
  --query 'Subnets[0].SubnetId' --output text
# cria o SG; se ja existir (re-run), reaproveita o ID existente
$env:SG_ID = aws ec2 create-security-group --group-name cloudtask-fargate-sg `
  --description "ECS Fargate 8000" --vpc-id $env:VPC_ID --query 'GroupId' --output text 2>$null
if (-not $env:SG_ID) {
  $env:SG_ID = aws ec2 describe-security-groups `
    --filters Name=group-name,Values=cloudtask-fargate-sg Name=vpc-id,Values=$env:VPC_ID `
    --query 'SecurityGroups[0].GroupId' --output text
}
echo "SG_ID=$env:SG_ID"
# regra 8000 (ignora se a regra ja existir)
aws ec2 authorize-security-group-ingress --group-id $env:SG_ID `
  --protocol tcp --port 8000 --cidr 0.0.0.0/0 2>$null

# 5. servico (1 task, IP publico para testar sem LB)
aws ecs create-service --cluster cloudtask-fargate --service-name cloudtask-api `
  --task-definition cloudtask-api --desired-count 1 --launch-type FARGATE `
  --network-configuration "awsvpcConfiguration={subnets=[$env:SUBNET_ID],securityGroups=[$env:SG_ID],assignPublicIp=ENABLED}"

# 6. IP publico da task (espere ~1 min ate RUNNING)
$env:TASK_ARN = aws ecs list-tasks --cluster cloudtask-fargate `
  --service-name cloudtask-api --query 'taskArns[0]' --output text
$env:ENI_ID = aws ecs describe-tasks --cluster cloudtask-fargate --tasks $env:TASK_ARN `
  --query "tasks[0].attachments[0].details[?name=='networkInterfaceId'].value" --output text
aws ec2 describe-network-interfaces --network-interface-ids $env:ENI_ID `
  --query "NetworkInterfaces[0].Association.PublicIp" --output text
# curl http://<IP>:8000/health
```

#### 4.1-AWS_ACADEMY — via Console (também serve à conta própria)

1. Console → ECS → Clusters → Create cluster.
   - Cluster name: `cloudtask-fargate`.
   - Infrastructure: **AWS Fargate (serverless)**.
2. Task definitions → Create new.
   - Family: `cloudtask-api`.
   - Launch type: Fargate.
   - OS: Linux x86_64.
   - CPU: 0.25 vCPU, Memory: 0.5 GB.
   - Task role: **LabRole**, Task execution role: **LabRole**.
   - Container:
     - Name: `api`.
     - Image URI: `<ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/cloudtask-api:latest`.
     - Port mapping: 8000 TCP.
     - Env vars: cole `DATABASE_URL`, `SECRET_KEY`, etc.
3. Services → Create.
   - Cluster: `cloudtask-fargate`.
   - Task definition: `cloudtask-api:1`.
   - Desired tasks: 1.
   - Networking: VPC default, subnets públicas, Security Group permitindo 8000.
   - Public IP: ENABLED (para testar sem LB).
4. Aguardar `RUNNING` → pegar Public IP da task → `curl http://<IP>:8000/health`.

> ⚠️ **`Public IP: ENABLED` / `--cidr 0.0.0.0/0` é didático**, NÃO usar em
> produção real. Em produção: Fargate atrás de ALB, sem IP público.

**Cleanup Fargate:**

```bash
# zera e remove service + cluster (Academy e propria)
aws ecs update-service --cluster cloudtask-fargate \
  --service cloudtask-api --desired-count 0
aws ecs delete-service --cluster cloudtask-fargate \
  --service cloudtask-api --force
aws ecs delete-cluster --cluster cloudtask-fargate

# conta propria: apague tambem o SG criado na CLI (a role pode ficar p/ reuso)
aws ec2 delete-security-group --group-name cloudtask-fargate-sg 2>/dev/null || true
```

---

## 5. Semana 5 — Provisionar EKS com `eksctl`

> **Quando:** Aula 8.

```bash
# 1. criar cluster (demora ~15 min)
eksctl create cluster \
  --name cloudtask-eks \
  --region us-east-1 \
  --version 1.30 \
  --nodegroup-name std-nodes \
  --node-type t3.small \
  --nodes 2 \
  --nodes-min 1 \
  --nodes-max 3 \
  --managed

# 2. confirmar
kubectl get nodes
# 2 nós em Ready
```

> ⚠️ **CUSTO:** cluster cobra $0,10/h + 2 nós t3.small ($0,04/h). Total
> ~$0,14/h. Em 4 h de aula = $0,56. **Sempre destruir no fim.**

> 💡 **Sem permissão para criar cluster?** Learner Lab tem limites; se
> `eksctl` falhar com `iam:CreateRole`, use o **template já criado pelo
> professor** ou contate-o.

**Acesso:**

```bash
# kubeconfig já fica configurado pelo eksctl
kubectl cluster-info
kubectl get nodes -o wide
```

---

## 6. Semana 5 — Subir API no EKS com Postgres em container

> Caminho **mais barato e didático**. Postgres roda como Pod, dados **somem
> ao reiniciar** (sem PVC). Para persistência mínima, adicione PVC. Para
> produção, vá direto pra §7 (RDS).

### 6.1. Estrutura dos manifests

```text
infra/k8s/aws/
├── namespace.yaml
├── postgres-deployment.yaml      # NOVO — Pod do banco
├── postgres-service.yaml         # ClusterIP (DNS interno)
├── secret-app.yaml               # SECRET_KEY, DB password
├── configmap-app.yaml            # DATABASE_URL etc.
├── api-deployment.yaml           # Pod da API + image do ECR
├── api-service.yaml              # type=LoadBalancer (ELB)
└── README.md
```

### 6.2. Aplicar

```bash
# 1. namespace
kubectl create namespace cloudtask

# 2. secret (DB password)
kubectl create secret generic cloudtask-secrets \
  --namespace cloudtask \
  --from-literal=POSTGRES_PASSWORD=$(openssl rand -hex 16) \
  --from-literal=SECRET_KEY=$(openssl rand -hex 32)

# 3. configmap (config não-sensível)
kubectl create configmap cloudtask-config \
  --namespace cloudtask \
  --from-literal=APP_ENV=production \
  --from-literal=AWS_REGION=us-east-1

# 4. aplicar manifests
kubectl apply -f infra/k8s/aws/

# 5. acompanhar
kubectl get pods -n cloudtask -w
```

### 6.3. Pegar URL do LoadBalancer

```bash
kubectl get svc -n cloudtask api-service
# EXTERNAL-IP → endereço do ELB (demora 1–3 min para aparecer)

# testar
curl http://$ELB_DNS:8000/health
```

---

## 7. Semana 6/8 — Trocar Postgres por RDS

> **Quando:**
> - **Semana 6** se a aula focar em produção / persistência;
> - **Semana 8** (final, conta pessoal) com Multi-AZ.

### Por que mudar?

| Razão | Pod | RDS |
| --- | --- | --- |
| Persiste após restart | só com PVC | ✅ |
| Backup automático | manual | ✅ até 35 dias |
| Multi-AZ HA | não | ✅ opcional |
| Custo (4 h) | ~$0 | ~$0,15 |

### Passos

#### 7.1. Criar RDS via CLI

**Linux/macOS (bash):**
```bash
# Security Group permitindo 5432 só do EKS
export VPC_ID=$(aws eks describe-cluster --name cloudtask-eks \
  --query "cluster.resourcesVpcConfig.vpcId" --output text)

aws ec2 create-security-group \
  --group-name rds-sg \
  --description "RDS access from EKS" \
  --vpc-id $VPC_ID
export RDS_SG=$(aws ec2 describe-security-groups \
  --filters "Name=group-name,Values=rds-sg" \
  --query "SecurityGroups[0].GroupId" --output text)

# Liberar 5432 do CIDR do EKS
aws ec2 authorize-security-group-ingress \
  --group-id $RDS_SG \
  --protocol tcp --port 5432 \
  --cidr 10.0.0.0/8     # ajuste conforme VPC do EKS

# Criar instância RDS
aws rds create-db-instance \
  --db-instance-identifier cloudtask-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --engine-version 16.3 \
  --master-username cloudtask \
  --master-user-password "$(openssl rand -hex 16)" \
  --allocated-storage 20 \
  --vpc-security-group-ids $RDS_SG \
  --db-name cloudtask \
  --no-publicly-accessible

# aguardar (~8 min)
aws rds wait db-instance-available --db-instance-identifier cloudtask-db
```

**Windows (PowerShell):**
```powershell
# Security Group permitindo 5432 só do EKS
$env:VPC_ID = aws eks describe-cluster --name cloudtask-eks `
  --query "cluster.resourcesVpcConfig.vpcId" --output text

aws ec2 create-security-group `
  --group-name rds-sg `
  --description "RDS access from EKS" `
  --vpc-id $env:VPC_ID
$env:RDS_SG = aws ec2 describe-security-groups `
  --filters "Name=group-name,Values=rds-sg" `
  --query "SecurityGroups[0].GroupId" --output text

# Liberar 5432 do CIDR do EKS (ajuste conforme VPC do EKS)
aws ec2 authorize-security-group-ingress `
  --group-id $env:RDS_SG `
  --protocol tcp --port 5432 `
  --cidr 10.0.0.0/8

# senha aleatória (32 chars hex, equivalente a openssl rand -hex 16)
$PWD_RDS = -join (1..32 | ForEach-Object { '{0:x}' -f (Get-Random -Maximum 16) })

# Criar instância RDS
aws rds create-db-instance `
  --db-instance-identifier cloudtask-db `
  --db-instance-class db.t3.micro `
  --engine postgres `
  --engine-version 16.3 `
  --master-username cloudtask `
  --master-user-password $PWD_RDS `
  --allocated-storage 20 `
  --vpc-security-group-ids $env:RDS_SG `
  --db-name cloudtask `
  --no-publicly-accessible

# aguardar (~8 min)
aws rds wait db-instance-available --db-instance-identifier cloudtask-db
```

#### 7.2. Capturar endpoint

**Linux/macOS (bash):**
```bash
export RDS_HOST=$(aws rds describe-db-instances \
  --db-instance-identifier cloudtask-db \
  --query "DBInstances[0].Endpoint.Address" --output text)
echo "RDS: $RDS_HOST"
```

**Windows (PowerShell):**
```powershell
$env:RDS_HOST = aws rds describe-db-instances `
  --db-instance-identifier cloudtask-db `
  --query "DBInstances[0].Endpoint.Address" --output text
echo "RDS: $env:RDS_HOST"
```

#### 7.3. Atualizar Secret e ConfigMap no EKS

**Linux/macOS (bash):**
```bash
kubectl create secret generic cloudtask-secrets \
  --namespace cloudtask \
  --from-literal=DATABASE_URL=postgresql://cloudtask:SUA_SENHA@$RDS_HOST:5432/cloudtask \
  --dry-run=client -o yaml | kubectl apply -f -

# remover o Pod do Postgres (não precisa mais)
kubectl delete -f infra/k8s/aws/postgres-deployment.yaml
kubectl delete -f infra/k8s/aws/postgres-service.yaml

# reiniciar a API para pegar a nova DATABASE_URL
kubectl rollout restart deployment/api -n cloudtask
```

**Windows (PowerShell):**
```powershell
kubectl create secret generic cloudtask-secrets `
  --namespace cloudtask `
  --from-literal=DATABASE_URL=postgresql://cloudtask:SUA_SENHA@${env:RDS_HOST}:5432/cloudtask `
  --dry-run=client -o yaml | kubectl apply -f -

# remover o Pod do Postgres (não precisa mais)
kubectl delete -f infra/k8s/aws/postgres-deployment.yaml
kubectl delete -f infra/k8s/aws/postgres-service.yaml

# reiniciar a API para pegar a nova DATABASE_URL
kubectl rollout restart deployment/api -n cloudtask
```

#### 7.4. Testar

```bash
curl http://$ELB_DNS:8000/health/ready
# {"database":"ok"} → conectou no RDS
```

---

## 8. Semana 6 — Secrets Manager para `.env`

> **Quando:** Aula 9. Substitui o `kubectl create secret` por algo gerenciado
> e auditável.

### 8.1. Criar segredo

O JSON do `--secret-string` tem aspas, então o quoting **muda por shell**:

**Linux/macOS (bash)** — aspas simples seguram o JSON inteiro:
```bash
aws secretsmanager create-secret \
  --name cloudtask/prod \
  --description "Credenciais e config CloudTask" \
  --secret-string '{
    "DATABASE_URL":"postgresql://cloudtask:SENHA@HOST:5432/cloudtask",
    "SECRET_KEY":"...",
    "AWS_REGION":"us-east-1",
    "S3_BUCKET_NAME":"cloudtask-uploads-..."
  }'
```

**Windows (PowerShell)** — use here-string `@'...'@` (literal, não expande `$`):
```powershell
$secret = @'
{
  "DATABASE_URL":"postgresql://cloudtask:SENHA@HOST:5432/cloudtask",
  "SECRET_KEY":"...",
  "AWS_REGION":"us-east-1",
  "S3_BUCKET_NAME":"cloudtask-uploads-..."
}
'@
aws secretsmanager create-secret `
  --name cloudtask/prod `
  --description "Credenciais e config CloudTask" `
  --secret-string $secret
```

### 8.2. Consumir no EKS — duas formas

**A) External Secrets Operator (recomendado):**

```bash
# instalar
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets external-secrets/external-secrets \
  --namespace external-secrets-system --create-namespace
```

E aplicar um `ExternalSecret` apontando para `cloudtask/prod` (manifest em
`infra/k8s/aws/external-secret.yaml`).

**B) Init container que injeta o segredo (mais simples):**

```yaml
# trecho do api-deployment.yaml
initContainers:
  - name: fetch-secrets
    image: amazon/aws-cli:latest
    command:
      - sh
      - -c
      - |
        aws secretsmanager get-secret-value \
          --secret-id cloudtask/prod \
          --query SecretString --output text > /env/.env
    volumeMounts:
      - name: env-vol
        mountPath: /env
```

> 🔵 **Conta AWS real:** o caminho recomendado é a forma **(A) External Secrets
> Operator** com **IRSA** (IAM Roles for Service Accounts): o pod assume uma IAM
> role dedicada com `secretsmanager:GetSecretValue`. Requer um **OIDC provider**
> registrado no cluster (`eksctl utils associate-iam-oidc-provider`) e uma role
> ligada à ServiceAccount.
>
> 🟢 **AWS Academy (Learner Lab):** a forma (A) **não funciona** — criar o OIDC
> provider e a role exige `iam:CreateOpenIDConnectProvider` / `iam:CreateRole`,
> **bloqueados** para a `voclabs`. Use uma destas:
> 1. **Forma (B), init container** acima — o pod usa a `LabRole` (que já tem
>    acesso ao Secrets Manager) via instance profile dos nós. Mais simples,
>    funciona no Lab.
> 2. **Secret nativo do K8s** (`kubectl create secret generic ... --from-env-file`)
>    em base64 — sem Secrets Manager. É o suficiente para a aula; apaga tudo no
>    fim. Menos auditável, mas zero dependência de IAM.

### 8.3. Cleanup

```bash
aws secretsmanager delete-secret \
  --secret-id cloudtask/prod \
  --force-delete-without-recovery
```

---

## 9. Semana 6 — HPA + load test

```bash
# 1. instalar metrics-server (necessário para HPA)
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# 2. aplicar HPA
kubectl apply -f infra/k8s/hpa.yaml

# 3. ver status
kubectl get hpa -n cloudtask

# 4. teste de carga simples
python scripts/load-test-simple.py http://$ELB_DNS:8000

# 5. ver pods escalando
kubectl get pods -n cloudtask -w
```

> A escala é demonstrada — não deixe rodando para sempre, dispara custo.

---

## 10. Semana 6 — DynamoDB para eventos

> 🔵 **Conta AWS real:** `dynamodb:CreateTable` funciona; siga os passos abaixo.
>
> 🟢 **AWS Academy (Learner Lab):** o DynamoDB **pode estar bloqueado** ou com
> limite de tabelas (`AccessDenied` em `dynamodb:CreateTable`). **Teste antes da
> aula.** Se não funcionar, use o **fallback local** que a aplicação já suporta —
> sem AWS nenhuma:
>
> ```
> EVENT_STORE_MODE=local            # em vez de dynamodb
> LOCAL_EVENTS_FILE=./local_events/events.json
> ```
>
> Os eventos vão para um arquivo JSON (igual ao fallback local dos uploads). A
> lição de "object/NoSQL store desacoplado da app" se mantém.

Criar a tabela — a quebra de linha muda por shell (`\` no bash, `` ` `` no
PowerShell):

**Linux/macOS (bash):**
```bash
# 1. criar tabela (PAY_PER_REQUEST = só paga por uso)
aws dynamodb create-table \
  --table-name cloudtask-events \
  --attribute-definitions AttributeName=id,AttributeType=S \
  --key-schema AttributeName=id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST
```

**Windows (PowerShell):**
```powershell
aws dynamodb create-table `
  --table-name cloudtask-events `
  --attribute-definitions AttributeName=id,AttributeType=S `
  --key-schema AttributeName=id,KeyType=HASH `
  --billing-mode PAY_PER_REQUEST
```

```bash
# 2. esperar ativa (igual nos dois shells)
aws dynamodb wait table-exists --table-name cloudtask-events

# 3. configurar no Secrets Manager (ou ConfigMap)
# EVENT_STORE_MODE=dynamodb
# DYNAMODB_TABLE_NAME=cloudtask-events

# 4. testar POST /events
curl -X POST http://$ELB_DNS:8000/events \
  -H "Content-Type: application/json" \
  -d '{"event_type":"task.created","task_id":1,"message":"teste"}'

# 5. ver na tabela
aws dynamodb scan --table-name cloudtask-events --max-items 5
```

> 💡 No passo 4, no PowerShell a variável é `$env:ELB_DNS` (não `$ELB_DNS`) se
> você a exportou via `$env:`. O `curl` real do Windows é `curl.exe`.

**Cleanup:**

```bash
aws dynamodb delete-table --table-name cloudtask-events
```

---

## 11. SEMPRE — cleanup obrigatório

> ⚠️ **NÃO PULE**. Cluster EKS sozinho gasta crédito 24/7 ($0,10/h).

```bash
# 1. derrubar Services LoadBalancer (libera ELBs)
kubectl delete svc --all -n cloudtask

# 2. derrubar pods
kubectl delete namespace cloudtask

# 3. destruir cluster EKS
eksctl delete cluster --name cloudtask-eks --region us-east-1
# (~10 min)

# 4. apagar RDS (se subiu)
aws rds delete-db-instance \
  --db-instance-identifier cloudtask-db \
  --skip-final-snapshot

# 5. apagar buckets S3 (uploads e, se usou CodeBuild no Academy, o de fonte)
aws s3 rb s3://$BUCKET --force
aws s3 rb s3://cloudtask-src-$ACCOUNT_ID --force 2>/dev/null || true

# 6. apagar repo ECR
aws ecr delete-repository --repository-name cloudtask-api --force

# 7. apagar secret
aws secretsmanager delete-secret \
  --secret-id cloudtask/prod \
  --force-delete-without-recovery

# 8. apagar tabela DynamoDB
aws dynamodb delete-table --table-name cloudtask-events

# 9. ECS Fargate (se subiu)
aws ecs delete-cluster --cluster cloudtask-fargate

# 10. confirmar
aws ec2 describe-instances --filters "Name=instance-state-name,Values=running"
aws elbv2 describe-load-balancers
aws rds describe-db-instances
# tudo deve estar vazio
```

**Validação final via Cost Explorer:** abra o Cost Explorer 24 h depois — se
houver gasto, alguma coisa escapou.

---

## 12. Tabela de complexidade × momento

| O que | Complexidade | Quando tentar |
| --- | :---: | :---: |
| Criar bucket S3 | ⭐ | Aula 5 |
| Login + push ECR | ⭐⭐ | Aula 7 |
| ECS Fargate (CLI própria / Console Academy) | ⭐⭐ | Aula 7 (opcional) |
| CodeBuild + GitHub | ⭐⭐⭐ | Aula 7 |
| EKS + manifests | ⭐⭐⭐⭐ | Aula 8 |
| Postgres como Pod | ⭐⭐ | Aula 8 |
| Postgres RDS + SG | ⭐⭐⭐⭐ | Aula 9 ou final |
| Secrets Manager + IRSA | ⭐⭐⭐⭐⭐ | Aula 9 |
| HPA + load test | ⭐⭐⭐ | Aula 9 |
| DynamoDB + POST /events | ⭐⭐ | Aula 10 |
| Cleanup completo | ⭐⭐ | Toda aula |
| ALB + ACM + Route 53 | ⭐⭐⭐⭐⭐ | só Aula 12 (conta pessoal) |

---

## Próximos passos

| Quero... | Vá em |
| --- | --- |
| Entender o que mora na AWS | [`../conceitos/infra-aws-minima-por-semana.md`](../conceitos/infra-aws-minima-por-semana.md) |
| Modelo de segurança | [`../conceitos/security-model.md`](../conceitos/security-model.md) |
| VPC / SG | [`../conceitos/aws-networking.md`](../conceitos/aws-networking.md) |
| HTTPS / ACM | [`../conceitos/https-tls.md`](../conceitos/https-tls.md) |
| Resolver erros AWS | [`99-troubleshooting.md`](99-troubleshooting.md) (seção AWS) |
