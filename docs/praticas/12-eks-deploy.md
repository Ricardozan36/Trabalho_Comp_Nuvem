# Prática 12 — Deploy no Amazon EKS (Aula 8)

> **Objetivo:** rodar a CloudTask num **cluster Kubernetes gerenciado (EKS)**,
> com a imagem vinda do **ECR** (Prática 11) e exposição pública via **Service
> LoadBalancer**. É o "Kind da Prática 10, mas na nuvem".
>
> **Quando:** Semana 4 / Aula 8.
> **Tempo:** 40–60 min.
> **Custo:** 💸 **ALTO** — EKS + nós EC2 + ELB cobram **por hora ligados**.
> Esta é a semana mais cara. **Destrua tudo na mesma sessão.**
>
> **Pré-req:**
> - Prática 11 feita (imagem no ECR).
> - `kubectl` (vem no devcontainer) + **AWS CLI v2** configurada.
> - Um **cluster EKS**: criado pelo professor (recomendado no Learner Lab) ou
>   por você com `eksctl` usando a `LabRole`.
> - Manifests em [`infra/k8s/aws/`](../../infra/k8s/aws/) — leia os comentários.

---

## 0. Por que EKS (e o que muda do Kind)

| Kind (Prática 10, local) | EKS (aqui, nuvem) |
| --- | --- |
| Nós = containers Docker no seu PC | Nós = **instâncias EC2** da AWS |
| Imagem `cloudtask-api:dev` carregada com `kind load` | Imagem **puxada do ECR** |
| Service `NodePort 30080` → `localhost` | Service **`LoadBalancer`** → ELB público |
| Control plane local | Control plane **gerenciado pela AWS** |
| Custo $0 | Custo **por hora** (EKS + EC2 + ELB) |

O resto (Deployment 2 réplicas, ConfigMap, Secret, probes) é **igual** — de
propósito: o que você aprendeu no Kind vale na nuvem.

---

## 1. Conectar o `kubectl` ao cluster EKS

```bash
# pega as credenciais do cluster e grava em ~/.kube/config
aws eks update-kubeconfig --name <cluster> --region us-east-1

# confirma que enxerga os nós EC2
kubectl get nodes
# NAME                            STATUS   ROLES    AGE   VERSION
# ip-10-0-1-23.ec2.internal       Ready    <none>   5m    v1.30.x
```

> ⚠️ **Learner Lab:** se `eksctl create cluster` falhou com erro de IAM, é
> esperado — o lab não cria roles. Use a `LabRole` ou o **cluster pré-criado
> pelo professor**. Ver [`00-setup-inicial-e-aws-academy.md`](00-setup-inicial-e-aws-academy.md).

---

## 2. Apontar o Deployment para a SUA imagem do ECR

Edite `infra/k8s/aws/deployment-eks.yaml` e troque `<ACCOUNT>` pelo ID da sua
conta (12 dígitos, do `aws sts get-caller-identity`):

```yaml
# antes:
image: <ACCOUNT>.dkr.ecr.us-east-1.amazonaws.com/cloudtask-api:latest
# depois (exemplo):
image: 123456789012.dkr.ecr.us-east-1.amazonaws.com/cloudtask-api:latest
```

---

## 3. Criar o Secret real (a partir do template)

```bash
cp infra/k8s/aws/secret.example.yaml infra/k8s/aws/secret.yaml

# gerar valores base64 (no devcontainer):
echo -n 'cloudtask' | base64
openssl rand -hex 16 | tr -d '\n' | base64    # POSTGRES_PASSWORD
openssl rand -hex 32 | tr -d '\n' | base64    # SECRET_KEY
# DATABASE_URL:
echo -n "postgresql://cloudtask:SUA_SENHA@postgres:5432/cloudtask" | base64
```

Cole nos campos `data:` de `secret.yaml` e **descomente** a linha `- secret.yaml`
no `infra/k8s/aws/kustomization.yaml`.

> ⚠️ `secret.yaml` já está no `.gitignore`. Nunca commite.

---

## 4. Aplicar os manifests

```bash
kubectl apply -k infra/k8s/aws/

# acompanhar os Pods subindo
kubectl get pods -n cloudtask -w
```

Esperado (~1–2 min; a API espera o Postgres no initContainer):

```text
NAME                             READY   STATUS     RESTARTS   AGE
postgres-xxxx-yyyy               1/1     Running    0          40s
cloudtask-api-xxxx-aaaa          1/1     Running    0          30s
cloudtask-api-xxxx-bbbb          1/1     Running    0          30s
```

`Ctrl+C` para sair do watch.

---

## 5. Descobrir o DNS do Load Balancer e testar

```bash
kubectl get svc -n cloudtask
# NAME              TYPE           EXTERNAL-IP                          PORT(S)
# cloudtask-api-lb  LoadBalancer   a1b2...elb.amazonaws.com             80:3xxxx/TCP
```

> O `EXTERNAL-IP` leva **1–3 min** para sair de `<pending>` (a AWS está
> provisionando o ELB). Aguarde.

```bash
LB=$(kubectl get svc cloudtask-api-lb -n cloudtask -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

curl http://$LB/health
# {"status":"ok"}

curl http://$LB/health/ready
# {"status":"ok","database":"ok"}

# CRUD na nuvem
curl -X POST http://$LB/tasks -H "Content-Type: application/json" \
  -d '{"title":"Tarefa no EKS","priority":"high"}'
curl http://$LB/tasks

echo "Swagger: http://$LB/docs"
```

---

## 6. Observabilidade rápida (logs, rollout, réplicas)

```bash
# logs agregados das 2 réplicas
kubectl logs -n cloudtask -l app=api -f

# status do rollout
kubectl rollout status -n cloudtask deploy/cloudtask-api

# ver os 2 Pods em (idealmente) AZs diferentes
kubectl get pods -n cloudtask -o wide
```

**Console AWS** para correlacionar: *EKS* (cluster/nodes), *EC2* (instâncias dos
nós), *EC2 → Load Balancers* (o ELB criado pelo Service).

---

## 7. 🔥 DESTRUIR — não pule este passo

> EKS + EC2 + ELB cobram **por hora**. Esquecer ligado **queima o crédito**.

```bash
# 1. apaga app + Service (o ELB some junto)
kubectl delete -k infra/k8s/aws/

# 2. confirme que o ELB sumiu
kubectl get svc -n cloudtask          # não deve haver LoadBalancer
aws elbv2 describe-load-balancers --query 'LoadBalancers[].LoadBalancerName' --output table

# 3. se VOCÊ criou o cluster, apague-o
eksctl delete cluster --name <cluster> --region us-east-1

# 4. End Lab no painel do AWS Academy
```

---

## 8. HTTPS? Fica para a Aula 12

No Learner Lab expomos **HTTP** (sem domínio/ACM). O **HTTPS real** (ALB + ACM +
domínio no Route53) é demonstrado na **Aula 12**, na conta pessoal do professor.
O arquivo [`infra/k8s/aws/ingress-optional.yaml`](../../infra/k8s/aws/ingress-optional.yaml)
mostra como seria — **não aplique no lab**. Conceito: [`../conceitos/https-tls.md`](../conceitos/https-tls.md).

---

## 9. Troubleshooting

| Erro | Causa | Fix |
| --- | --- | --- |
| `EXTERNAL-IP` preso em `<pending>` | ELB ainda provisionando (1–3 min) ou falta permissão | aguarde; se nunca sair, é limite do lab |
| Pod `ErrImagePull` / `ImagePullBackOff` | `<ACCOUNT>` não trocado ou nó sem permissão de ECR | corrija a `image:`; confira IAM do node |
| Pod `Init:0/1` parado | Postgres não ficou pronto | `kubectl logs -n cloudtask <pod> -c wait-for-postgres` |
| `/tasks` retorna 500 | `DATABASE_URL` errada no Secret | confira o base64 do `secret.yaml` |
| `eksctl create cluster` falha (IAM) | Learner Lab não cria roles | use `LabRole` ou cluster do professor |
| `error: You must be logged in to the server` | kubeconfig vencido | refaça `aws eks update-kubeconfig ...` |

---

## 10. O que mudou em relação ao Kind (Prática 10)

| Kind (Aula 6) | EKS (Aula 8) |
| --- | --- |
| `kind load docker-image` | `docker push` para o **ECR** + pull automático |
| `NodePort 30080` em `localhost` | `LoadBalancer` com **DNS público** |
| Cluster no seu PC, $0 | Cluster gerenciado, **custo por hora** |
| `kind delete cluster` | `kubectl delete -k` + `eksctl delete cluster` + **End Lab** |

---

## Próximos passos

| Quero... | Vá em |
| --- | --- |
| Escalar com HPA + ver custos | Semana 5 — [`../ROADMAP.md`](../ROADMAP.md) (Aula 9) |
| Revisar a aula combinada 3+4 | [`13-roteiro-aula-3-e-4.md`](13-roteiro-aula-3-e-4.md) |
| Trocar Postgres-Pod por RDS | [`09-deploy-manual-aws.md`](09-deploy-manual-aws.md) §7 |
