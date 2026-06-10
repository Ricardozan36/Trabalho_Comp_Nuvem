# `infra/k8s/aws/` — Manifests Kubernetes na AWS / EKS (Aulas 7 e 8)

Manifests para rodar a CloudTask no **Amazon EKS** (Kubernetes gerenciado),
com a imagem vinda do **Amazon ECR** e exposição via **Service LoadBalancer**.

> **Roteiros passo a passo:**
> - ECR (Aula 7): [`docs/praticas/11-ecr-push.md`](../../../docs/praticas/11-ecr-push.md)
> - EKS (Aula 8): [`docs/praticas/12-eks-deploy.md`](../../../docs/praticas/12-eks-deploy.md)
> - Aula combinada Semanas 3+4: [`docs/praticas/13-roteiro-aula-3-e-4.md`](../../../docs/praticas/13-roteiro-aula-3-e-4.md)
>
> Este README é só o índice + ordem de aplicação.

> ⚠️ **Semana mais cara.** EKS + nós EC2 + ELB cobram **por hora ligados**.
> Roteiro seguro: criar → demonstrar → **destruir na mesma sessão** → *End Lab*.

---

## Arquivos

| Arquivo | O que faz |
| --- | --- |
| `configmap.yaml` | Config AWS: `STORAGE_MODE=s3`, `BEHIND_PROXY=true` (LB na frente). |
| `secret.example.yaml` | **Template** do Secret. Copie para `secret.yaml` (gitignored). |
| `deployment-eks.yaml` | API 2 réplicas, **imagem do ECR** (troque `<ACCOUNT>`), probes. |
| `service-loadbalancer.yaml` | `type: LoadBalancer` → AWS cria um ELB público. |
| `ingress-optional.yaml` | **(produção)** ALB + ACM (HTTPS). NÃO use no Learner Lab. |
| `namespace.yaml` | Namespace `cloudtask` (cópia self-contained). |
| `postgres-deployment.yaml` | Postgres como Pod (`emptyDir` — troque por RDS em prod). |
| `postgres-service.yaml` | DNS interno `postgres:5432`. |
| `kustomization.yaml` | `kubectl apply -k .` — aplica tudo desta pasta, na ordem. |

> Esta pasta é **autocontida**: não referencia `../` (o Kustomize bloqueia, por
> segurança, incluir arquivos acima da pasta). Por isso o namespace e o
> Postgres têm cópias aqui. Em produção, troque o Postgres-Pod por **RDS**.

---

## Quick start (do devcontainer; precisa de AWS CLI configurada)

```bash
# 0. Pré: estar logado no Learner Lab (aws configure / credenciais temporárias)
aws sts get-caller-identity        # confirma a conta

# 1. Build + push da imagem PROD para o ECR (Aula 7)
./scripts/build-and-push-ecr.sh
# anote a linha "image: <ACCOUNT>.dkr.ecr....amazonaws.com/cloudtask-api:latest"

# 2. Editar deployment-eks.yaml: troque <ACCOUNT> pelo ID da sua conta

# 3. Conectar o kubectl ao cluster EKS (cluster do professor ou criado por você)
aws eks update-kubeconfig --name <cluster> --region us-east-1
kubectl get nodes

# 4. Secret real a partir do template
cp infra/k8s/aws/secret.example.yaml infra/k8s/aws/secret.yaml
# edite com base64 (ver instruções no arquivo) e descomente a linha no kustomization

# 5. Aplicar
kubectl apply -k infra/k8s/aws/
kubectl get pods -n cloudtask -w

# 6. Pegar o DNS do Load Balancer e testar (1-3 min para provisionar)
kubectl get svc -n cloudtask
curl http://<DNS-DO-LB>/health

# 7. DESTRUIR (custo!) — na mesma sessão
kubectl delete -k infra/k8s/aws/
# e, se você criou o cluster: eksctl delete cluster --name <cluster>
```

---

## Postgres x RDS

Para a aula seguimos com **Postgres como Pod** (reaproveitado do Kind) — mesma
limitação didática: **sem volume persistente, os dados somem** se o Pod morre.

Em **produção real** você trocaria por **Amazon RDS**:

1. Remova `../postgres-deployment.yaml` e `../postgres-service.yaml` do
   `kustomization.yaml`.
2. No `configmap.yaml`, aponte `POSTGRES_HOST` para o **endpoint do RDS**.
3. Ponha usuário/senha do RDS no Secret (`DATABASE_URL`).

Ver `docs/praticas/09-deploy-manual-aws.md` §7 (RDS) para o passo a passo.

---

## Limitação do AWS Academy / Learner Lab

- **Não cria IAM roles** → `eksctl create cluster` padrão falha. Use a
  `LabRole` existente ou um **cluster pré-criado pelo professor**.
- **Sem domínio/ACM** → HTTPS real (ALB + ACM) não roda aqui. Use só o
  **Service LoadBalancer (HTTP)**; o HTTPS de verdade é demonstrado na Aula 12,
  na conta pessoal do professor. Ver `docs/conceitos/https-tls.md`.
