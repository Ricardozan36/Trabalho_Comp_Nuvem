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
| [`conceitos/seguranca-aula12-auth-proxy-cert.md`](conceitos/seguranca-aula12-auth-proxy-cert.md) | 6 | **Entrega final:** login/JWT Bearer, proxy reverso + `/api` como Server (root_path), servidor de cert (Caddy+ACME+sslip.io), Swagger com senha |
| [`conceitos/s3-efs-datalake.md`](conceitos/s3-efs-datalake.md) | 5 | S3 × EFS × EBS, classes, URL pré-assinada, Data Lake |
| [`conceitos/infra-aws-minima-por-semana.md`](conceitos/infra-aws-minima-por-semana.md) | 4+ | Stack AWS mínima por semana, custos, Postgres container × RDS, ECS × EKS |
| [`conceitos/cost-explorer.md`](conceitos/cost-explorer.md) | 5 | Cost Explorer, Budgets (alerta por e-mail), regra "subiu/testou/destruiu" |
| [`conceitos/aws-pricing-notes.md`](conceitos/aws-pricing-notes.md) | 5 | Preços por serviço (EC2/EKS/ELB/S3/ECR/DynamoDB) e dicas de economia |

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
| [`praticas/11-ecr-push.md`](praticas/11-ecr-push.md) | Aula 7: build `--target prod` + push da imagem para o Amazon ECR (com `scripts/semana-04-ecr/build-push-ecr.sh`) |
| [`praticas/12-eks-deploy.md`](praticas/12-eks-deploy.md) | Aula 8: deploy no Amazon EKS (imagem do ECR + Service LoadBalancer) e **destruir** para não queimar crédito |
| [`praticas/13-roteiro-aula-semanas-3-e-4.md`](praticas/13-roteiro-aula-semanas-3-e-4.md) | 🧭 **Roteiro da aula combinada Semanas 3+4** (Kind local → ECR → EKS), com os testes de cada etapa |
| [`praticas/14-hpa-carga-custos.md`](praticas/14-hpa-carga-custos.md) | Aula 9: metrics-server + HPA, teste de carga (`scripts/semana-05-hpa/teste-carga.py`), observar escala e custos |
| [`praticas/15-eventos-dynamodb.md`](praticas/15-eventos-dynamodb.md) | Aula 10: eventos/logs em DynamoDB (fallback JSON local), emissão automática no CRUD |
| [`praticas/16-console-vs-script.md`](praticas/16-console-vs-script.md) | 🐢 Console vs Script: criar DynamoDB/EKS/Budget **na mão** pelo console (cliques + tempo) vs 1 comando — sentir por que automatizar |
| [`praticas/17-site-estatico-s3-vs-ec2.md`](praticas/17-site-estatico-s3-vs-ec2.md) | 🌐 **Demo rápida no AWS CloudShell**: mesma página na internet por **S3 Static Website** (sem servidor, centavos) vs **EC2 + Apache** (servidor real, cobra por hora) |
| [`praticas/18-cdk-iac.md`](praticas/18-cdk-iac.md) | Aula 11: **Infra como Código (AWS CDK)** — `cdk synth/deploy/destroy` das stacks em `infra/cdk/` |
| [`praticas/19-servidores-ec2-grafana.md`](praticas/19-servidores-ec2-grafana.md) | Aula 12: **3 servidores EC2** (API + Frontend + Grafana) por script CLI e pela 7ª stack CDK; **link externo real** + auth |
| [`praticas/20-cdk-python-por-dentro.md`](praticas/20-cdk-python-por-dentro.md) | Aula 11/12: **como o AWS CDK em Python funciona por dentro** — App/Stack/Construct, synth→CloudFormation, tour pelos arquivos |
| [`praticas/21-seguranca-https-auth.md`](praticas/21-seguranca-https-auth.md) | Aula 12: **segurança na prática** — login→token JWT, rota protegida com/sem Bearer, `/api` como Server no Swagger, cert válido, Swagger com senha |
| [`praticas/99-troubleshooting.md`](praticas/99-troubleshooting.md) | Erros comuns + como resolver |

> 💡 **Os práticos não dependem todos uns dos outros.** Mas se está perdido,
> faça nesta ordem: 00 → 01 → 02 → 03 → 04. Os 05–08 vão entrando aula a aula.

---

## 🎓 `entrega-final/` — fechamento da disciplina (Aula 12)

Materiais de consolidação e entrega.

| Arquivo | Para que serve |
| --- | --- |
| [`entrega-final/final-architecture.md`](entrega-final/final-architecture.md) | Arquitetura final consolidada (as 6 semanas em um diagrama). |
| [`entrega-final/final-report-template.md`](entrega-final/final-report-template.md) | **Template do relatório** de entrega — copie e preencha. |
| [`entrega-final/lgpd-checklist.md`](entrega-final/lgpd-checklist.md) | Checklist LGPD + segurança. |
| [`entrega-final/deployment-checklist.md`](entrega-final/deployment-checklist.md) | Checklist de deploy + **limpeza de custos**. |

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
    ├── 13-roteiro-aula-semanas-3-e-4.md        ← roteiro combinado 3+4
    ├── 14-hpa-carga-custos.md          ← Semana 5 (Aula 9: HPA + custos)
    ├── 15-eventos-dynamodb.md          ← Semana 5 (Aula 10: DynamoDB/eventos)
    ├── 16-console-vs-script.md         ← Semana 5 (console na mão vs script)
    ├── 17-site-estatico-s3-vs-ec2.md   ← site estático: S3 vs EC2
    ├── 18-cdk-iac.md                   ← Semana 6 (Aula 11: AWS CDK / IaC)
    ├── 19-servidores-ec2-grafana.md    ← Semana 6 (Aula 12: 3 EC2 API/Front/Grafana)
    ├── 20-cdk-python-por-dentro.md     ← Semana 6 (Aula 11/12: CDK Python por dentro)
    ├── 21-seguranca-https-auth.md      ← Semana 6 (Aula 12: login/token/HTTPS/Swagger c/ senha)
    └── 99-troubleshooting.md

entrega-final/                          ← Aula 12 (fechamento)
├── final-architecture.md
├── final-report-template.md
├── lgpd-checklist.md
└── deployment-checklist.md
```

> 🧭 **Semanas 3 e 4 são dadas juntas** (a Semana 3 não teve aula). Comece
> pela [`praticas/13-roteiro-aula-semanas-3-e-4.md`](praticas/13-roteiro-aula-semanas-3-e-4.md),
> que encadeia Kind local → ECR → EKS com os testes de cada etapa.
