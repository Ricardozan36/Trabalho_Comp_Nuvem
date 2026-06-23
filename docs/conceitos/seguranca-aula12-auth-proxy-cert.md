# Segurança da entrega final — login, token, proxy e certificado (Aula 12)

Guia didático das **camadas de segurança** que a Semana 6 adicionou ao CloudTask:
quem é você (**autenticação**), como o navegador confia no servidor (**certificado
válido**) e como tudo passa por **um único ponto seguro** (o proxy reverso).

> **Resumo de uma frase:** o usuário **faz login e recebe um crachá (token JWT)**;
> toda chamada às rotas de dados leva esse crachá; e **só o Edge fala com a
> internet**, em HTTPS com **certificado válido de verdade**.
>
> Pré-leitura: [`https-tls.md`](https-tls.md) (o que é TLS) e
> [`security-model.md`](security-model.md) (modelo geral). Aqui focamos no que
> **mudou na Aula 12**.

---

## 1. A arquitetura em uma figura

```text
   navegador ──HTTPS (cert válido)──► EDGE (Caddy)  ──HTTP interno──►  API  (:8000)
   (443)                              <ip>.sslip.io  ├─ /api/*      ──►  Grafana(:3000)
                                      serve o SPA    └─ /grafana/*
```

Três ideias de segurança convivem aqui:

1. **Autenticação** (você prova quem é) → **token JWT**.
2. **Confiança no transporte** (o navegador confia no servidor) → **certificado válido**.
3. **Superfície mínima** (menos portas abertas) → **um proxy só** na frente.

---

## 2. Autenticação: login → token (JWT) → Bearer

Antes, qualquer um que alcançasse a API usava as rotas. Agora:

1. **Tela de login** (no frontend) manda usuário/senha para `POST /api/auth/login`.
2. A API confere as credenciais e devolve um **token JWT** (`access_token`).
3. O frontend **guarda** o token e o envia em **todas** as chamadas às rotas de
   dados, no cabeçalho:

   ```http
   Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
   ```

4. As rotas `/tasks`, `/uploads`, `/events` exigem esse cabeçalho. **Sem token →
   `401`** (antes de tocar o banco). O `/auth/login` e o `/health` ficam
   **públicos** (senão você não conseguiria logar nem o balanceador checar saúde).

### O que é um JWT (rápido)

Um **JWT** tem 3 partes separadas por ponto: `cabeçalho.dados.assinatura`.

* **dados** (payload): quem é (`sub: admin`) e até quando vale (`exp`).
* **assinatura**: um HMAC-SHA256 dos dados usando a `SECRET_KEY` do servidor.

A graça: o servidor **não guarda sessão**. Ele só **recalcula a assinatura** e
compara — se bate (e não expirou), o token é legítimo. Por isso o token é
**auto-contido** e a verificação é barata. Trocar 1 byte do token quebra a
assinatura → `401`.

> 🔑 Na demo, usuário/senha = `admin` / `admin#123` em tudo, **de propósito**.
> Em produção: senhas fortes e diferentes, fora do código, e idealmente um
> **servidor de autenticação dedicado** (ex.: Authentik/Cognito) — ver a nota na
> [prática 19](../praticas/19-servidores-ec2-grafana.md).

---

## 3. O proxy reverso e o `/api` como **Server**

O Edge (Caddy) recebe tudo em HTTPS e **encaminha** internamente:

| Você acessa | O Edge faz | Chega na |
| --- | --- | --- |
| `https://host/` | serve o arquivo do SPA | (nginx-like, no próprio Edge) |
| `https://host/api/...` | **tira** o `/api` e repassa | API `:8000` |
| `https://host/grafana/...` | repassa | Grafana `:3000` |

Como o SPA e a API ficam **na mesma origem** (`https://host`), o navegador **não
reclama de CORS nem de conteúdo misto** — some toda aquela dor de cabeça.

### Por que a API precisa saber que está em `/api` (`root_path`)

O Edge **remove** o prefixo `/api` antes de repassar (a API recebe `/tasks`, não
`/api/tasks`). Mas o **Swagger** precisa montar a URL do `openapi.json` para
desenhar a documentação. Sem ajuda, o FastAPI geraria `/openapi.json` (na raiz)
— que, no navegador, vira `https://host/openapi.json` (sem `/api`) → cai no SPA
→ o Swagger tenta ler HTML como especificação e **quebra**.

A solução é dizer ao FastAPI **onde ele está publicamente**:

```python
app = FastAPI(root_path="/api")   # injetado por env (ROOT_PATH=/api)
```

Com isso o FastAPI gera as URLs já com `/api` e o Swagger mostra, no topo, o
**Server** `/api` — e busca `/api/openapi.json` corretamente. É o mesmo conceito
de "estou atrás de um proxy num subcaminho".

---

## 4. O servidor de certificado (cert válido sem domínio próprio)

Para o navegador mostrar o **cadeado verde**, o servidor precisa de um
**certificado** assinado por uma **CA** confiável. A novidade da Aula 12: obtemos
um cert **válido de verdade** **sem ter um domínio**.

### As três peças

1. **Caddy** — o servidor web/proxy do Edge. Ele tem **ACME embutido**: pede e
   renova certificados **sozinho** (Let's Encrypt; se falhar, ZeroSSL).
2. **`sslip.io`** — um DNS público "mágico": `34-239-41-96.sslip.io` **resolve
   para** `34.239.41.96`. Assim temos um **hostname** (a CA precisa de um nome,
   não de um IP) sem comprar domínio.
3. **Elastic IP** — um IP **fixo** para o Edge, para o hostname `sslip.io` sempre
   apontar para a máquina certa.

### O fluxo ACME (desafio HTTP-01), em 4 passos

```text
1. Caddy: "CA, quero um cert para 34-239-41-96.sslip.io"
2. CA   : "Prove que controla esse host: publique um arquivo em
           http://34-239-41-96.sslip.io/.well-known/acme-challenge/<token>"
3. Caddy publica o token na porta 80 (por isso o SG abre a 80)
4. CA valida, assina e entrega o certificado → Caddy passa a servir 443 com ele
```

Depois o Caddy **renova sozinho** antes de expirar. E **redireciona 80→443**: quem
chega por HTTP é mandado para HTTPS.

> ⚠️ **Pegadinha que vimos na prática:** o e-mail do ACME precisa de um **TLD
> válido**. `admin@cloudtask.local` foi **recusado** ("Domain name does not end
> with a valid public suffix") e nenhum cert era emitido. Trocar para um e-mail
> com TLD real (`@example.com`) resolveu. Mensagem: erros de ACME quase sempre
> estão nos **logs do Caddy** (`journalctl -u caddy`).
>
> ⚠️ **Sobre "válido de verdade":** `sslip.io` + Let's Encrypt funciona, mas é um
> recurso compartilhado e sujeito a **rate-limit**; se bater, o Caddy tenta o
> ZeroSSL (fallback). Em produção séria, use um **domínio próprio**.

---

## 5. Superfície mínima + Swagger com senha

* **API e Grafana não ficam expostos** à internet (portas 8000/3000 só dentro do
  security group). O **único** ponto público é o Edge (80/443). Menos portas
  abertas = menos superfície de ataque.
* O **Swagger** (`/api/docs`, `/api/openapi.json`, `/api/redoc`) fica **atrás de
  senha** (HTTP Basic no Caddy). Por quê: o Swagger lista todas as rotas — é um
  mapa da API. Numa demo pública, exigir senha evita expor esse mapa a qualquer
  um. (A senha do Basic é separada do token JWT do app — são duas camadas.)

---

## 6. As camadas, juntas (defesa em profundidade)

| Camada | O que protege | Como |
| --- | --- | --- |
| **TLS / cert válido** | o **transporte** (ninguém lê/altera no caminho) | Caddy + ACME + sslip.io |
| **HTTPS-only** | evita trafegar em texto puro | redirect 80→443 |
| **JWT Bearer** | as **rotas de dados** (só logados) | `/auth/login` + `require_auth` |
| **Basic auth no Swagger** | a **documentação** (mapa da API) | Caddy `basic_auth` |
| **Superfície mínima** | reduz **portas expostas** | só o Edge é público |

Nenhuma camada sozinha resolve tudo — **somadas** é que dão uma postura de
produção. Mão na massa: [prática 21](../praticas/21-seguranca-https-auth.md).
