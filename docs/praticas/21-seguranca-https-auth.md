# Prática 21 — Segurança na prática: login, token, HTTPS e Swagger com senha (Aula 12)

> **Objetivo:** **usar** as camadas de segurança que subimos na entrega final —
> fazer login e pegar um **token**, chamar uma rota protegida **com** e **sem**
> token, ver o **`/api` como Server** no Swagger, conferir o **certificado
> válido** e o **Swagger com senha**.
>
> **Quando:** Semana 6 / Aula 12. Faça depois da
> [prática 19](19-servidores-ec2-grafana.md) (que sobe os servidores).
>
> **Teoria por trás:** [`../conceitos/seguranca-aula12-auth-proxy-cert.md`](../conceitos/seguranca-aula12-auth-proxy-cert.md).
>
> **Pré-req:** os 3 servidores no ar (`bash infra/servers/semana-06-servidores-subir.sh`).
> Anote o host impresso, ex.: `https://SEU-IP.sslip.io`. Aqui chamamos de `$APP`.

```bash
# guarde o host numa variável para copiar/colar os comandos
APP=https://34-239-41-96.sslip.io      # troque pelo SEU host
```

---

## 1. Tudo é HTTPS (e o cadeado é válido)

```bash
# HTTP é redirecionado para HTTPS (308)
curl -s -o /dev/null -w "%{http_code}\n" http://SEU-IP.sslip.io/      # -> 308

# HTTPS sem -k: o curl SÓ aceita se o certificado for VÁLIDO (CA confiável)
curl -sI "$APP/" | head -1                                            # -> HTTP/2 200

# quem assinou o certificado?
echo | openssl s_client -connect SEU-IP.sslip.io:443 -servername SEU-IP.sslip.io 2>/dev/null \
  | openssl x509 -noout -issuer
# -> issuer= ... Let's Encrypt  (ou ZeroSSL)
```

No navegador, abra `$APP/` e clique no **cadeado** → o certificado é de uma CA
real (Let's Encrypt/ZeroSSL), válido para o hostname `sslip.io`. **Sem aviso de
"não seguro".**

> Se o cadeado ainda estiver "emitindo", espere ~1–3 min após o boot — o Caddy
> está fazendo o desafio ACME (ver a [teoria, §4](../conceitos/seguranca-aula12-auth-proxy-cert.md)).

---

## 2. Login → token (JWT)

```bash
# credenciais da demo: admin / admin#123
TOKEN=$(curl -s -X POST "$APP/api/auth/login" \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin#123"}' | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

echo "${TOKEN:0:30}..."    # eyJhbGciOiJIUzI1NiIs...  (cabeçalho.dados.assinatura)
```

Repare nos **3 pedaços** separados por ponto. Cole o token em
[jwt.io](https://jwt.io) para ver o conteúdo (`sub`, `exp`) — **mas** a
assinatura só o servidor valida (ele tem a `SECRET_KEY`).

```bash
# senha errada NÃO devolve token:
curl -s -o /dev/null -w "%{http_code}\n" -X POST "$APP/api/auth/login" \
  -H 'Content-Type: application/json' -d '{"username":"admin","password":"errada"}'   # -> 401
```

---

## 3. Rota protegida: com e sem o crachá

```bash
# SEM token -> 401 (a guarda barra ANTES de tocar o banco)
curl -s -o /dev/null -w "sem token: %{http_code}\n" "$APP/api/tasks"          # -> 401

# COM o token no cabeçalho Authorization: Bearer
curl -s -o /dev/null -w "com token: %{http_code}\n" \
  -H "Authorization: Bearer $TOKEN" "$APP/api/tasks"                          # -> 200

# criar uma tarefa (também exige o token)
curl -s -X POST "$APP/api/tasks" -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"title":"Tarefa via token","priority":"high","status":"pending"}'
```

> Troque **um caractere** do token e repita o GET: vira **401** — a assinatura
> não bate mais. É assim que o servidor confia no crachá sem guardar sessão.

---

## 4. Swagger: `/api` como **Server** + senha

Abra `$APP/api/docs` no navegador. O navegador vai **pedir usuário e senha**
(`admin` / `admin#123`) — é o **Basic auth do Caddy** protegendo a documentação.

Depois de entrar, repare:

1. No topo, em **Servers**, aparece **`/api`** — é o `root_path` em ação (a API
   sabe que está publicada sob `/api`, então o Swagger busca `/api/openapi.json`).
2. Clique em **Authorize** (cadeado, canto superior) e cole o **token** do passo 2.
   Agora você consegue executar as rotas protegidas direto pelo Swagger.

```bash
# provando a senha do Swagger pela linha de comando:
curl -s -o /dev/null -w "sem senha: %{http_code}\n" "$APP/api/docs"                       # -> 401
curl -s -o /dev/null -w "com senha: %{http_code}\n" -u admin:'admin#123' "$APP/api/docs"  # -> 200

# o Server declarado no contrato OpenAPI:
curl -s -u admin:'admin#123' "$APP/api/openapi.json" | python -c "import sys,json;print(json.load(sys.stdin).get('servers'))"
# -> [{'url': '/api'}]
```

---

## 5. A superfície é mínima (API/Grafana não ficam expostos)

Tente bater **direto** na porta da API/Grafana pelo IP público — deve **falhar**
(timeout): essas portas só aceitam conexões **de dentro** do security group; o
mundo só fala com o Edge (443).

```bash
# tenta a porta 8000 direto no IP (espera travar/timeout):
curl -s -m 5 -o /dev/null -w "%{http_code}\n" http://SEU-IP:8000/health || echo "bloqueado (esperado)"
```

Tudo que você consegue acessar passa **pelo Edge, em HTTPS**. É a ideia de
**superfície mínima** da [teoria, §5](../conceitos/seguranca-aula12-auth-proxy-cert.md).

---

## 6. Resumo

| Você testou | Resultado esperado |
| --- | --- |
| `http://` | redireciona para `https://` (308) |
| certificado | **válido** (CA real, cadeado verde) |
| login com senha certa / errada | token / `401` |
| `/api/tasks` sem / com token | `401` / `200` |
| Swagger | pede **senha** + mostra **Server `/api`** |
| porta 8000 direto | **bloqueada** (só o Edge é público) |

Você exercitou as **cinco camadas** de defesa em profundidade da entrega final.
Ao terminar, **destrua** os servidores: `bash infra/servers/semana-06-servidores-destruir.sh`.
