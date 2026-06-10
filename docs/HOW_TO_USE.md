# Como usar este repositório (guia do aluno)

Este projeto é um **mini SaaS de gerenciamento de tarefas** em Python + FastAPI, construído **aula a aula**. Cada aula tem uma branch própria com **o que já foi visto até aquele momento** — nada de spoiler do código futuro.

> Se você está abrindo o repo pela primeira vez na semana 1, leia até o final desta página antes de pedir ajuda.

> 🆕 **Nunca usou terminal, Docker ou AWS?** Comece pelo guia passo a passo
> **do absoluto zero**: [`praticas/00-setup-inicial-e-aws-academy.md`](praticas/00-setup-inicial-e-aws-academy.md). Ele
> cobre instalação de todas as ferramentas e a configuração do AWS Academy.

---

## 1. Pré-requisitos

Instale na sua máquina (mesma versão ou mais nova):

| Ferramenta            | Versão mínima | Verifica com                |
| --------------------- | ------------- | --------------------------- |
| Git                   | 2.40          | `git --version`             |
| Python                | 3.11          | `python --version`          |
| pip                   | 23.x          | `pip --version`             |
| Docker Desktop        | 4.30          | `docker --version`          |
| Docker Compose (v2)   | 2.20          | `docker compose version`    |

A partir da **aula 6** (Kubernetes local):
- **Kind** ou **Minikube** + **kubectl**.

A partir da **aula 7** (AWS):
- **AWS CLI v2** (`aws --version`).
- Conta no **AWS Academy / Learner Lab** (o professor fornece).

A partir da **aula 11** (CDK):
- **Node.js 20+** e `npm i -g aws-cdk`.

> **Windows:** recomenda-se WSL2 para Docker e Kubernetes.
> **macOS / Linux:** funciona nativo.

---

## 2. Clonar o repositório

```bash
git clone https://github.com/N-CPUninter/Computa-o-em-Nuvem---Projeto-exemplo-CloudTask-AI-SaaS.git
cd Computa-o-em-Nuvem---Projeto-exemplo-CloudTask-AI-SaaS
```

A pasta clonada tem o **nome do repositório**. Você pode renomeá-la livremente — não afeta o Git.

---

## 3. Trocar para a aula correta

A branch `main` contém **apenas este guia e a documentação**. O código de cada aula vive em sua própria branch.

```bash
# listar todas as branches publicadas
git fetch --all
git branch -r

# entrar na aula 1
git checkout aula-01-final

# avançar para a próxima aula
git checkout aula-02-final
```

Cada `aula-XX-final` é **autocontida**: você não precisa fazer merge de nada.

### E se eu mexi no código e quero voltar ao original?

```bash
# descarta alterações locais (cuidado: perde o que você fez)
git restore .
git clean -fd

# ou guarda suas alterações em uma "gaveta"
git stash
git checkout aula-XX-final
```

### Acompanhando atualizações do professor

```bash
git fetch --all
git checkout aula-XX-final
git pull
```

---

## 4. Configurando variáveis de ambiente

A partir da **aula 4**, a aplicação lê configurações de um arquivo `.env`.

```bash
cp .env.example .env
# edite .env com seus valores locais
```

**Nunca** versione o `.env` — ele já está no `.gitignore`.

---

## 5. Rodando a aplicação

### Aula 1 — direto com Python

```bash
python -m venv .venv
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# macOS / Linux:
source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload
```

Acesse:
- API: <http://localhost:8000>
- Swagger: <http://localhost:8000/docs>
- Health: <http://localhost:8000/health>

### Aula 2 em diante — com Docker

```bash
docker compose up --build
```

Para parar:

```bash
docker compose down
```

### Aula 6 — Kubernetes local (Kind)

```bash
kind create cluster --name cloudtask
kubectl apply -f infra/k8s/
kubectl get pods -n cloudtask
```

### Aula 7 — Publicar imagem no ECR

```bash
./scripts/build-and-push-ecr.sh        # build --target prod + push para o ECR
```

Passo a passo: [`praticas/11-ecr-push.md`](praticas/11-ecr-push.md).

### Aula 8 — Deploy no EKS (nuvem)

```bash
aws eks update-kubeconfig --name <cluster> --region us-east-1
kubectl apply -k infra/k8s/aws/
kubectl get svc -n cloudtask           # pega o DNS do Load Balancer
```

Passo a passo: [`praticas/12-eks-deploy.md`](praticas/12-eks-deploy.md) e
[`infra/k8s/aws/README.md`](../infra/k8s/aws/README.md).

> 🧭 **Semanas 3 e 4 juntas:** como a Semana 3 não teve aula, siga o roteiro
> combinado [`praticas/13-roteiro-aula-3-e-4.md`](praticas/13-roteiro-aula-3-e-4.md)
> (Kind local → ECR → EKS).
>
> 💸 EKS + EC2 + ELB cobram **por hora**. Sempre `kubectl delete -k infra/k8s/aws/`
> e **End Lab** ao terminar.

---

## 6. Onde encontrar o quê

| Quero saber...                                | Vá em                                  |
| --------------------------------------------- | -------------------------------------- |
| O que cada aula entrega                       | [`ROADMAP.md`](ROADMAP.md)             |
| Conceitos de VPC, IAM, segurança (aula 4)     | `conceitos/aws-networking.md`, `conceitos/security-model.md` (a partir da aula 4) |
| S3, EFS e Data Lake (aula 5)                  | `conceitos/s3-efs-datalake.md` (a partir da aula 5) |
| Como subir imagem para ECR (aula 7)           | `praticas/11-ecr-push.md` + `scripts/build-and-push-ecr.sh` |
| Como fazer deploy no EKS (aula 8)             | `praticas/12-eks-deploy.md` + `infra/k8s/aws/README.md` |
| Roteiro da aula combinada 3+4                 | `praticas/13-roteiro-aula-3-e-4.md`    |
| Custos AWS (aula 9)                           | `cost-explorer.md`, `aws-pricing-notes.md` |
| Checklist LGPD e entrega final (aula 12)      | `lgpd-checklist.md`, `deployment-checklist.md` |

---

## 7. Problemas comuns

**`port already in use` ao rodar `docker compose up`**
Outro serviço já usa a porta `8000` ou `5432`. Pare-o ou ajuste no `docker-compose.yml`.

**`ModuleNotFoundError: No module named 'app'`**
Você está rodando o `uvicorn` fora da raiz do projeto. Volte para a pasta onde está o `app/`.

**Swagger não abre em `/docs`**
Confira se a app subiu (`docker compose logs api` ou terminal do `uvicorn`). Veja se o `APP_PORT` está correto.

**`could not connect to server: Connection refused` (PostgreSQL, aula 3+)**
O banco ainda não está pronto. Espere alguns segundos e tente de novo, ou veja `docker compose logs db`.

**AWS pedindo credenciais**
Rode `aws configure` e use as credenciais do seu Learner Lab. Para o Learner Lab, normalmente são credenciais temporárias copiadas do console.

---

## 8. Pedindo ajuda

1. Releia a mensagem de erro completa.
2. Confirme que está na branch correta (`git branch --show-current`).
3. Confirme que copiou o `.env.example` para `.env`.
4. Procure no Moodle / fórum da disciplina antes de abrir issue aqui.
5. Se for um bug real do projeto: abra uma **issue** descrevendo a aula, branch, comando e erro.
