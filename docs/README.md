# Documentação — CloudTask AI SaaS

Índice da pasta `docs/`. Dividida em **dois tipos** de conteúdo + arquivos transversais na raiz.

---

## Por onde começar?

| Sua situação | Vá em |
| --- | --- |
| Nunca instalei nada — partindo do zero | [`praticas/00-setup-inicial-e-aws-academy.md`](praticas/00-setup-inicial-e-aws-academy.md) |
| Já tenho Git/Docker/VS Code, quero rodar o projeto | [`HOW_TO_USE.md`](HOW_TO_USE.md) → [`praticas/01-rodar-api-devcontainer.md`](praticas/01-rodar-api-devcontainer.md) |
| Quero entender o que cada aula entrega | [`ROADMAP.md`](ROADMAP.md) |
| Quero a lista de tarefas por aula | [`TAREFAS.md`](TAREFAS.md) |

---

## 📁 `conceitos/` — leitura para **entender**

Texto explicativo. Pouco ou nenhum comando para rodar. Leia antes (ou durante) a aula correspondente.

| Arquivo | Aula | Cobre |
| --- | --- | --- |
| [`conceitos/docker-explained.md`](conceitos/docker-explained.md) | 2 | Imagens, multi-stage, Docker Compose (dev/prod/test), devcontainer |
| [`conceitos/aws-networking.md`](conceitos/aws-networking.md) | 4 | VPC, subnets pública/privada, Security Groups, Internet Gateway, NAT, bastion |
| [`conceitos/security-model.md`](conceitos/security-model.md) | 4 | IAM, MFA, responsabilidade compartilhada, criptografia, LGPD |
| [`conceitos/https-tls.md`](conceitos/https-tls.md) | 4 | TLS, ALB, HSTS, mkcert local, proxy-headers |
| [`conceitos/s3-efs-datalake.md`](conceitos/s3-efs-datalake.md) | 5 | S3 × EFS × EBS, classes, URL pré-assinada, Data Lake |
| [`conceitos/infra-aws-minima-por-semana.md`](conceitos/infra-aws-minima-por-semana.md) | 4+ | Stack AWS mínima por semana, custos, Postgres container × RDS, ECS × EKS |

---

## 🛠️ `praticas/` — passo a passo para **fazer**

Tutoriais com comandos. Cada arquivo é um exercício prático que você pode (e deve) executar.

| Arquivo | O que você vai fazer |
| --- | --- |
| [`praticas/00-setup-inicial-e-aws-academy.md`](praticas/00-setup-inicial-e-aws-academy.md) | Instalar Git, Docker, AWS CLI, kubectl, eksctl, Node+CDK + configurar AWS Academy / Learner Lab |
| [`praticas/01-rodar-api-devcontainer.md`](praticas/01-rodar-api-devcontainer.md) | Abrir o projeto no devcontainer e verificar que tudo subiu |
| [`praticas/02-explorar-swagger.md`](praticas/02-explorar-swagger.md) | Usar Swagger UI ("Try it out"), inspecionar schemas, baixar OpenAPI |
| [`praticas/03-crud-tasks-via-curl.md`](praticas/03-crud-tasks-via-curl.md) | CRUD completo de `/tasks` via curl + ver no banco |
| [`praticas/04-explorar-banco-psql.md`](praticas/04-explorar-banco-psql.md) | Conectar no PostgreSQL com `psql`, rodar SELECT/INSERT |
| [`praticas/05-uploads-modo-local.md`](praticas/05-uploads-modo-local.md) | Testar `/uploads` com `STORAGE_MODE=local` + 404 + 413 |
| [`praticas/06-uploads-modo-s3.md`](praticas/06-uploads-modo-s3.md) | Criar bucket S3, trocar `.env`, validar URL pré-assinada |
| [`praticas/07-rodar-testes.md`](praticas/07-rodar-testes.md) | Rodar `pytest` no devcontainer e em container isolado |
| [`praticas/08-debug-vscode.md`](praticas/08-debug-vscode.md) | Depurar com breakpoints no VS Code (debugpy attach) |
| [`praticas/09-deploy-manual-aws.md`](praticas/09-deploy-manual-aws.md) | Deploy manual AWS: ECR, ECS Fargate, EKS, RDS, Secrets Manager, DynamoDB (por semana) |
| [`praticas/10-kubernetes-kind-local.md`](praticas/10-kubernetes-kind-local.md) | Aula 6: cluster Kind local + manifests `infra/k8s/` (Postgres pod + API 2 réplicas + NodePort + demo perda de dados) |
| [`praticas/11-ecr-push.md`](praticas/11-ecr-push.md) | Aula 7: build `--target prod` + push da imagem para o Amazon ECR (com `scripts/build-and-push-ecr.sh`) |
| [`praticas/12-eks-deploy.md`](praticas/12-eks-deploy.md) | Aula 8: deploy no Amazon EKS (imagem do ECR + Service LoadBalancer) e **destruir** para não queimar crédito |
| [`praticas/13-roteiro-aula-3-e-4.md`](praticas/13-roteiro-aula-3-e-4.md) | 🧭 **Roteiro da aula combinada Semanas 3+4** (Kind local → ECR → EKS), com os testes de cada etapa |
| [`praticas/99-troubleshooting.md`](praticas/99-troubleshooting.md) | Erros comuns + como resolver |

> 💡 **Os práticos não dependem todos uns dos outros.** Mas se está perdido,
> faça nesta ordem: 00 → 01 → 02 → 03 → 04. Os 05–08 vão entrando aula a aula.

---

## Arquivos transversais (raiz de `docs/`)

| Arquivo | Para que serve |
| --- | --- |
| [`HOW_TO_USE.md`](HOW_TO_USE.md) | Guia rápido: pré-requisitos, clonar, trocar de branch, rodar |
| [`ROADMAP.md`](ROADMAP.md) | Plano completo das 12 aulas, entregas, branches, tags |
| [`TAREFAS.md`](TAREFAS.md) | Checklist espelho das issues do GitHub |

---

## Resumo visual

```
docs/
├── README.md              ← (você está aqui)
├── HOW_TO_USE.md          ← guia rápido
├── ROADMAP.md             ← plano 12 aulas
├── TAREFAS.md             ← checklist
│
├── conceitos/             ← LER pra entender (sem ou pouco comando)
│   ├── docker-explained.md
│   ├── aws-networking.md
│   ├── security-model.md
│   ├── https-tls.md
│   ├── s3-efs-datalake.md
│   └── infra-aws-minima-por-semana.md
│
└── praticas/              ← FAZER passo a passo (todo comando)
    ├── 00-setup-inicial-e-aws-academy.md
    ├── 01-rodar-api-devcontainer.md
    ├── 02-explorar-swagger.md
    ├── 03-crud-tasks-via-curl.md
    ├── 04-explorar-banco-psql.md
    ├── 05-uploads-modo-local.md
    ├── 06-uploads-modo-s3.md
    ├── 07-rodar-testes.md
    ├── 08-debug-vscode.md
    ├── 09-deploy-manual-aws.md
    ├── 10-kubernetes-kind-local.md     ← Semana 3 (Kind local)
    ├── 11-ecr-push.md                  ← Semana 4 (ECR)
    ├── 12-eks-deploy.md                ← Semana 4 (EKS)
    ├── 13-roteiro-aula-3-e-4.md        ← roteiro combinado 3+4
    └── 99-troubleshooting.md
```

> 🧭 **Semanas 3 e 4 são dadas juntas** (a Semana 3 não teve aula). Comece
> pela [`praticas/13-roteiro-aula-3-e-4.md`](praticas/13-roteiro-aula-3-e-4.md),
> que encadeia Kind local → ECR → EKS com os testes de cada etapa.
