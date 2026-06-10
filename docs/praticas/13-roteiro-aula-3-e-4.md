# Prática 13 — Roteiro da aula combinada: Semanas 3 + 4

> **Por que combinada?** A **Semana 3 não teve aula**. Então fazemos os
> experimentos e testes das **duas semanas numa só sessão**, seguindo a
> progressão natural:
>
> ```
> [Sem 3]  container local  →  Kubernetes LOCAL (Kind)
>                                     │
> [Sem 4]                       registry na nuvem (ECR)  →  Kubernetes NA NUVEM (EKS)
> ```
>
> **Quando:** aula única cobrindo Semana 3 (Aulas 5–6) + Semana 4 (Aulas 7–8).
> **Tempo total:** ~2h30–3h (Parte A local; Parte B na nuvem).
> **Versão da API:** `0.4.0`.
>
> **Pré-req (instale ANTES):** Docker Desktop, Kind, kubectl, AWS CLI v2,
> credenciais do Learner Lab. Guia: [`00-setup-inicial-e-aws-academy.md`](00-setup-inicial-e-aws-academy.md).

Este arquivo é o **fio condutor**: ele NÃO repete os passos detalhados — manda
você para a prática específica de cada etapa e diz **o que observar e testar**
em cada checkpoint.

---

## Mapa da aula

| Parte | Etapa | Prática detalhada | Custo |
| --- | --- | --- | --- |
| **A — Semana 3 (local)** | A1. Uploads S3/local | [`05`](05-uploads-modo-local.md) + [`06`](06-uploads-modo-s3.md) | $0 / centavos |
| | A2. Testes automatizados | [`07`](07-rodar-testes.md) | $0 |
| | A3. Kubernetes local (Kind) | [`10`](10-kubernetes-kind-local.md) | $0 |
| **B — Semana 4 (nuvem)** | B1. Imagem no ECR | [`11`](11-ecr-push.md) | centavos |
| | B2. Deploy no EKS | [`12`](12-eks-deploy.md) | 💸 por hora |
| | B3. Destruir tudo | [`12`](12-eks-deploy.md) §7 | — |

> 💡 **Regra de ouro de custo:** a Parte A é toda gratuita/local. Só entre na
> Parte B (nuvem) quando a Parte A estiver funcionando — e **destrua** ao fim.

---

# PARTE A — Semana 3 (tudo local, $0)

## A1. Uploads: S3 com fallback local

**Faça:** [`05-uploads-modo-local.md`](05-uploads-modo-local.md) e, se tiver
bucket, [`06-uploads-modo-s3.md`](06-uploads-modo-s3.md).

**O que testar / observar:**

```bash
# modo local (STORAGE_MODE=local)
curl -F "file=@README.md" http://localhost:8000/uploads
curl http://localhost:8000/uploads/README.md      # baixa de volta
curl -i http://localhost:8000/uploads/naoexiste    # 404 esperado
```

✅ **Checkpoint A1:** upload grava em `local_uploads/` (modo local) **ou** gera
URL pré-assinada do S3 (modo s3). A mesma API serve os dois — só muda o `.env`.

---

## A2. Testes automatizados (a rede de segurança)

**Faça:** [`07-rodar-testes.md`](07-rodar-testes.md).

```bash
# no devcontainer
pytest -v

# ou em container isolado (igual à CI)
docker compose -f docker-compose.test.yml up --build --abort-on-container-exit
```

**O que observar:** os testes cobrem health, schemas, CRUD de tasks e uploads.

✅ **Checkpoint A2:** suíte **verde**. Se algo falhar aqui, **não suba para a
nuvem** — conserte primeiro. Testar local é grátis; depurar no EKS custa
crédito.

---

## A3. Kubernetes LOCAL com Kind

**Faça:** [`10-kubernetes-kind-local.md`](10-kubernetes-kind-local.md) (completo).

**Sequência mínima (do HOST):**

```bash
kind create cluster --config infra/k8s/kind-config.yaml
docker build --target dev -t cloudtask-api:dev .
kind load docker-image cloudtask-api:dev --name cloudtask
cp infra/k8s/secret.example.yaml infra/k8s/secret.yaml   # edite os base64
kubectl apply -k infra/k8s/
kubectl get pods -n cloudtask -w
```

**O que testar:**

```bash
curl http://localhost:30080/health          # {"status":"ok"}
curl http://localhost:30080/health/ready     # checa o Postgres
curl -X POST http://localhost:30080/tasks \
  -H "Content-Type: application/json" -d '{"title":"Tarefa K8s local"}'
```

**Experimentos-chave (faça os dois — são o coração da Semana 3):**
1. **Rolling update** (Prática 10 §8): mude o ConfigMap, `kubectl rollout
   restart`, veja zero downtime.
2. **Perda de dados** (Prática 10 §9): mate o Pod do Postgres e veja as tarefas
   sumirem (`emptyDir` sem volume). Lição que se repete no EKS.

✅ **Checkpoint A3:** 2 réplicas da API `Running`, Service balanceando,
demo de perda de dados entendida. **Guarde o cluster Kind** — vamos comparar
com o EKS. (Ou destrua com `kind delete cluster --name cloudtask` se faltar RAM.)

---

# PARTE B — Semana 4 (nuvem AWS, custo por hora)

> ⚠️ A partir daqui **conta o crédito**. Faça em sequência, sem pausas longas,
> e **destrua na mesma sessão** (B3).

## B0. Pré-voo

```bash
aws sts get-caller-identity     # confirma login no Learner Lab
kubectl get nodes               # se já tiver cluster EKS conectado
```

## B1. Publicar a imagem no ECR

**Faça:** [`11-ecr-push.md`](11-ecr-push.md).

```bash
./scripts/build-and-push-ecr.sh
aws ecr list-images --repository-name cloudtask-api --output table
```

✅ **Checkpoint B1:** tag `latest` listada no ECR. Anote a URI da imagem.

> **Comparação didática:** no Kind você fez `kind load` (imagem local). Aqui
> você fez `push` para um **registry na nuvem** — é a diferença que permite um
> cluster remoto (EKS) baixar a imagem.

## B2. Deploy no EKS

**Faça:** [`12-eks-deploy.md`](12-eks-deploy.md).

```bash
aws eks update-kubeconfig --name <cluster> --region us-east-1
# troque <ACCOUNT> em infra/k8s/aws/deployment-eks.yaml
cp infra/k8s/aws/secret.example.yaml infra/k8s/aws/secret.yaml   # edite base64
kubectl apply -k infra/k8s/aws/
kubectl get pods -n cloudtask -w
```

**O que testar (mesmos testes do Kind, agora num DNS público):**

```bash
LB=$(kubectl get svc cloudtask-api-lb -n cloudtask \
  -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
curl http://$LB/health
curl -X POST http://$LB/tasks -H "Content-Type: application/json" \
  -d '{"title":"Tarefa no EKS"}'
curl http://$LB/tasks
echo "Swagger: http://$LB/docs"
```

✅ **Checkpoint B2:** mesma API respondendo, agora pela internet via ELB.
O `EXTERNAL-IP` é um DNS público (não mais `localhost:30080`).

## B3. 🔥 DESTRUIR (obrigatório)

**Faça:** [`12-eks-deploy.md`](12-eks-deploy.md) §7.

```bash
kubectl delete -k infra/k8s/aws/         # apaga app + ELB
eksctl delete cluster --name <cluster>   # se VOCÊ criou o cluster
# + End Lab no painel do AWS Academy
kind delete cluster --name cloudtask     # limpa também o Kind local da Parte A
```

✅ **Checkpoint B3:** `kubectl get svc -n cloudtask` sem `LoadBalancer`; nenhum
ELB em *EC2 → Load Balancers*. Crédito preservado.

---

## Quadro-resumo: a mesma app em 3 ambientes

| | Compose (Sem 1–2) | Kind (Sem 3) | EKS (Sem 4) |
| --- | --- | --- | --- |
| Onde roda | devcontainer | containers no seu PC | EC2 na AWS |
| Imagem | build local | `kind load` | **push p/ ECR** → pull |
| Acesso | `localhost:8000` | `localhost:30080` (NodePort) | DNS do ELB (LoadBalancer) |
| Config/Secret | `.env` | ConfigMap + Secret | ConfigMap + Secret |
| Réplicas | 1 | 2 | 2 (em 2 AZs) |
| Custo | $0 | $0 | 💸 por hora |
| Persistência DB | volume Compose | `emptyDir` (perde!) | `emptyDir` (perde!) → RDS em prod |

> A lição transversal das duas semanas: **o código não muda** — muda só *onde*
> e *como* ele é empacotado, configurado e exposto. É isso que torna a app
> "cloud-native".

---

## Se algo der errado

| Sintoma | Vá em |
| --- | --- |
| Erro no Kind / NodePort | [`10`](10-kubernetes-kind-local.md) §11 |
| Erro no push do ECR | [`11`](11-ecr-push.md) §5 |
| Erro no EKS / ELB pending | [`12`](12-eks-deploy.md) §9 |
| Problemas gerais | [`99-troubleshooting.md`](99-troubleshooting.md) |
