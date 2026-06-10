# Prática 11 — Publicar a imagem no Amazon ECR (Aula 7)

> **Objetivo:** levar a imagem Docker da CloudTask **da sua máquina para a
> nuvem**, num registry privado da AWS — o **Amazon ECR** —, de onde o EKS
> (Prática 12) vai puxá-la.
>
> **Quando:** Semana 4 / Aula 7.
> **Tempo:** 20–30 min.
> **Custo:** centavos (ECR cobra por GB-mês de imagem). O caro é o EKS (Aula 8).
>
> **Pré-req:**
> - Devcontainer da semana-04 rodando.
> - **AWS CLI v2** configurada com as credenciais do **Learner Lab**
>   (ver [`00-setup-inicial-e-aws-academy.md`](00-setup-inicial-e-aws-academy.md) §AWS Academy).
> - **Docker** disponível (no devcontainer, via docker-outside-of-docker).
> - Conceito de registry: [`../conceitos/infra-aws-minima-por-semana.md`](../conceitos/infra-aws-minima-por-semana.md).

---

## 0. O que é um registry, e por que ECR

A imagem que você builda fica **só na sua máquina**. O cluster na nuvem (EKS)
não a enxerga. Um **registry** é o "GitHub das imagens Docker": você faz
`push` e o cluster faz `pull`.

| Registry | Característica |
| --- | --- |
| Docker Hub | público/grátis (com limite de rate), fora da AWS |
| **Amazon ECR** | **privado**, integrado ao **IAM**, perto do EKS (pull rápido, sem rate limit) |

Fluxo desta prática: **build → tag → login → push**.

---

## 1. Confirmar que está logado na AWS

```bash
aws sts get-caller-identity
# {
#   "Account": "123456789012",   ← seu ID de conta (12 dígitos)
#   "Arn": "arn:aws:sts::...:assumed-role/voclabs/..."
# }
```

> ❌ `Unable to locate credentials` → rode `aws configure` e cole as
> credenciais temporárias do Learner Lab (*AWS Details → AWS CLI*).

---

## 2. Caminho fácil: o script pronto

O repositório traz `scripts/build-and-push-ecr.sh`, que faz **tudo** (cria o
repo se faltar, login, build `--target prod`, tag, push):

```bash
# da raiz do repo:
./scripts/build-and-push-ecr.sh
```

Variáveis opcionais (têm defaults):

```bash
REGION=us-east-1 REPO=cloudtask-api TAG=latest ./scripts/build-and-push-ecr.sh

# taggear com o SHA do commit (rastreável — boa prática de produção):
TAG="$(git rev-parse --short HEAD)" ./scripts/build-and-push-ecr.sh
```

> Se der `Permission denied` ao rodar o script:
> `chmod +x scripts/build-and-push-ecr.sh` e tente de novo.

Pule para o **passo 4 (conferir)** se usou o script.

---

## 3. Caminho manual (entender cada comando)

```bash
# variáveis
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
REGION=us-east-1
REPO=cloudtask-api
REGISTRY=$ACCOUNT.dkr.ecr.$REGION.amazonaws.com

# 3.1 criar o repositório (uma vez; ignora erro se já existir)
aws ecr create-repository --repository-name $REPO --region $REGION \
  --image-scanning-configuration scanOnPush=true || true

# 3.2 login do Docker no ECR (token dura ~12h)
aws ecr get-login-password --region $REGION \
  | docker login --username AWS --password-stdin $REGISTRY

# 3.3 build da imagem PROD (estágio enxuto do Dockerfile multi-stage)
docker build --target prod -t cloudtask-api:prod .

# 3.4 tag apontando para o ECR
docker tag cloudtask-api:prod $REGISTRY/$REPO:latest

# 3.5 push
docker push $REGISTRY/$REPO:latest
```

> **Por que `--target prod`?** A imagem que vai para a nuvem é a enxuta, sem
> pytest/ferramentas de dev. `dev` (com `--reload`) fica só para o Kind local.

---

## 4. Conferir que a imagem subiu

```bash
aws ecr list-images --repository-name cloudtask-api --output table
# deve listar a tag 'latest' (e/ou o SHA, se você usou)
```

No **Console AWS**: *ECR → Repositories → cloudtask-api → Images*.

Anote a URI da imagem — você vai colá-la no Deployment do EKS:

```text
<ACCOUNT>.dkr.ecr.us-east-1.amazonaws.com/cloudtask-api:latest
```

---

## 5. Troubleshooting

| Erro | Causa | Fix |
| --- | --- | --- |
| `Unable to locate credentials` | Learner Lab não configurado | `aws configure` com credenciais temporárias |
| `denied: ...` no push | login expirou (~12h) ou falta IAM | refaça `aws ecr get-login-password \| docker login ...` |
| `repository ... already exists` | repo já criado | normal — ignore (o script trata com `|| true`) |
| `no basic auth credentials` | não fez login no ECR | rode o passo 3.2 |
| `Cannot connect to the Docker daemon` | Docker Desktop desligado no host | ligue o Docker Desktop |

---

## Próximos passos

| Quero... | Vá em |
| --- | --- |
| Rodar essa imagem no EKS | [`12-eks-deploy.md`](12-eks-deploy.md) |
| Ver a aula 3+4 do começo ao fim | [`13-roteiro-aula-3-e-4.md`](13-roteiro-aula-3-e-4.md) |
| Comparar ECR x Docker Hub, ECS x EKS | [`../conceitos/infra-aws-minima-por-semana.md`](../conceitos/infra-aws-minima-por-semana.md) |
