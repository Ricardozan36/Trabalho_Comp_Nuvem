# `infra/k8s/` — Manifests Kubernetes (Aula 6)

Manifests do **cluster Kubernetes local com Kind** para a Aula 6 da Semana 3.

> **Roteiro completo passo a passo:** [`docs/praticas/10-kubernetes-kind-local.md`](../../docs/praticas/10-kubernetes-kind-local.md).
> Este README é só o índice dos arquivos + ordem de aplicação.

---

## Arquivos

| Arquivo | O que faz |
| --- | --- |
| `kind-config.yaml` | Cria cluster Kind com porta 30080 exposta no host. |
| `namespace.yaml` | Namespace `cloudtask`. |
| `configmap.yaml` | Configs **não sensíveis** (APP_ENV, hostname Postgres, STORAGE_MODE). |
| `secret.example.yaml` | **Template** do Secret. Copie para `secret.yaml` (gitignored) e preencha. |
| `postgres-deployment.yaml` | Postgres como Pod único, `emptyDir` (dados somem ao reiniciar — didático). |
| `postgres-service.yaml` | DNS interno `postgres:5432`. |
| `api-deployment.yaml` | API FastAPI 2 réplicas, init container espera Postgres, probes HTTP. |
| `api-service.yaml` | `NodePort 30080` → mapeado para `localhost:30080` via Kind. |
| `kustomization.yaml` | `kubectl apply -k .` aplica tudo na ordem. |

---

## Quick start (do HOST — Kind roda fora do devcontainer!)

```bash
# 1. Cluster Kind
kind create cluster --config infra/k8s/kind-config.yaml

# 2. Build da imagem prod (código embutido) e carga no Kind
#    POR QUÊ prod e não dev: o target dev NÃO copia app/ (espera volume do
#    devcontainer). No cluster não há volume → ModuleNotFoundError.
docker build --target prod -t cloudtask-api:prod .
kind load docker-image cloudtask-api:prod --name cloudtask

# 3. Secret real a partir do template
cp infra/k8s/secret.example.yaml infra/k8s/secret.yaml
# edite com valores base64 (ver instruções no secret.example.yaml)

# 4. Aplicar tudo
kubectl apply -k infra/k8s/

# 5. Verificar
kubectl get pods -n cloudtask -w

# 6. Acessar
curl http://localhost:30080/health
open http://localhost:30080/docs

# 7. Destruir cluster (libera memória)
kind delete cluster --name cloudtask
```

---

## Por que Kind roda no HOST e não no devcontainer

`kind` usa o **Docker do host** para criar os "nós" do cluster (que são
containers). Se você rodar `kind create cluster` **dentro** do devcontainer:

- O cluster sobe usando o Docker socket compartilhado (via feature
  `docker-outside-of-docker`), mas a API do cluster fica em
  `127.0.0.1:RANDOM_PORT` do **host** — inacessível de dentro do container.

Solução: comandos `kind create / delete / load` rodam no **terminal do
host**. O `kubectl` no devcontainer fala com o cluster lendo
`~/.kube/config` (que está montado do host).
