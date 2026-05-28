# Guia completo de configuração — do zero ao AWS Academy

> **Para quem é este guia?** Para o aluno que **nunca usou terminal**, nunca
> instalou Docker e nunca mexeu na AWS. Vamos do absoluto zero. Leia na ordem,
> faça um passo de cada vez, e **não pule etapas**.
>
> Faça **uma única vez** as Partes 1 e 2 (instalação). As Partes 3 em diante
> você consulta conforme a aula pedir.

## Índice

1. [Parte 0 — O que é "terminal" e por que usamos](#parte-0--o-que-é-terminal)
2. [Parte 1 — Instalar as ferramentas base](#parte-1--instalar-as-ferramentas-base)
3. [Parte 2 — Configurar o AWS Academy Learner Lab](#parte-2--configurar-o-aws-academy-learner-lab)
4. [Parte 3 — Conectar a AWS CLI ao Learner Lab](#parte-3--conectar-a-aws-cli-ao-learner-lab)
5. [Parte 4 — Quais serviços AWS cada aula usa](#parte-4--serviços-aws-por-aula)
6. [Parte 5 — Avisos importantes (leia antes de gastar crédito!)](#parte-5--avisos-importantes)
7. [Parte 6 — Checklist rápido por sessão](#parte-6--checklist-rápido-por-sessão)
8. [Parte 7 — Solução de problemas](#parte-7--solução-de-problemas)

---

## Parte 0 — O que é "terminal"

O **terminal** (também chamado de "prompt de comando", "shell" ou "console") é
uma janela onde você **digita comandos em texto** em vez de clicar em botões.
Quase tudo de nuvem é feito por comandos — então é normal estranhar no começo.

### Qual terminal abrir

| Seu sistema | Abra este terminal | Como abrir |
| ----------- | ------------------ | ---------- |
| **Windows** | **PowerShell** | Tecla `Windows` → digite `PowerShell` → Enter |
| **macOS**   | **Terminal**   | `Cmd + Espaço` → digite `Terminal` → Enter |
| **Linux**   | **Terminal**   | `Ctrl + Alt + T` |

> 💡 No Windows, **recomendamos fortemente** instalar o **WSL2** (Linux dentro
> do Windows) — ver Parte 1. Mas dá para começar só com o PowerShell.

### Comandos de sobrevivência no terminal

| Quero... | Windows (PowerShell) | macOS / Linux |
| -------- | -------------------- | ------------- |
| Ver em que pasta estou | `pwd` | `pwd` |
| Listar arquivos da pasta | `ls` | `ls` |
| Entrar numa pasta | `cd nome-da-pasta` | `cd nome-da-pasta` |
| Voltar uma pasta | `cd ..` | `cd ..` |
| Limpar a tela | `cls` | `clear` |
| Cancelar um comando travado | `Ctrl + C` | `Ctrl + C` |

> 💡 **Copiar/colar no terminal:** no PowerShell, `Ctrl + C` / `Ctrl + V`
> funcionam. No Terminal do macOS, `Cmd + C` / `Cmd + V`. Em alguns terminais
> Linux use `Ctrl + Shift + C` / `Ctrl + Shift + V`.

---

## Parte 1 — Instalar as ferramentas base

> ## 🧭 Dois modos de trabalho — escolha um antes de instalar
>
> **Modo A — Devcontainer (RECOMENDADO neste curso).** Você desenvolve dentro
> de um container, abrindo o projeto no VS Code. As ferramentas de nuvem (AWS
> CLI, kubectl, eksctl, Node/CDK, docker) **já vêm prontas dentro do container**.
> No **HOST** você instala apenas:
> - **Docker Desktop** (1.2)
> - **VS Code + extensão Dev Containers** (1.10)
> - **Git** (1.1)
> - **WSL2** (1.3, só Windows)
> - **kind** (1.7) — *única* ferramenta de nuvem que roda no host (Aula 6).
>
> Pode **pular** no host: AWS CLI, kubectl, eksctl, Node/CDK (1.5, 1.6, 1.8,
> 1.9) — elas vivem no container. As **credenciais** você configura **uma vez
> no host** (Parte 3) e o container lê o mesmo arquivo automaticamente.
>
> **Modo B — Tudo no host.** Você instala e roda tudo direto no seu sistema,
> sem container. Aí siga **todos** os passos 1.1 a 1.10.
>
> Em caso de dúvida, use o **Modo A**. O resto da Parte 1 cobre os dois — só
> instale o que o seu modo pede.

Instale as ferramentas do seu modo. Após cada instalação, **feche e reabra
o terminal** e rode o comando de verificação para confirmar.

> ⚠️ Sempre que um comando de verificação mostrar um número de versão, deu
> certo. Se aparecer "command not found" / "não é reconhecido", a instalação
> falhou ou o terminal não foi reaberto.

> 💡 **Processador ARM?** Os comandos manuais de Linux abaixo baixam binários
> `amd64` (Intel/AMD — a maioria dos PCs). Se você usa ARM (Raspberry Pi,
> alguns ambientes Apple Silicon ou VMs ARM), troque **`amd64` por `arm64`**
> nas URLs. No Windows e no macOS isso é automático (winget/brew escolhem certo).

> 💡 **Se um `winget install` falhar** com "Nenhum pacote encontrou os
> critérios", o ID pode ter mudado. Descubra o novo com `winget search <nome>`.

### 1.1 — Git (controle de versão)

**Windows:** baixe em <https://git-scm.com/download/win> e instale com as opções
padrão (next, next, next).
**macOS:** já vem; se não, instale o [Homebrew](https://brew.sh) e rode `brew install git`.
**Linux (Ubuntu/Debian):** `sudo apt update && sudo apt install -y git`

Verificar (em qualquer terminal):
```bash
git --version
```

### 1.2 — Docker Desktop (containers)

Baixe em <https://www.docker.com/products/docker-desktop/> e instale.

- **Windows:** durante a instalação, **marque a opção "Use WSL 2"**. Depois de
  instalar, **abra o Docker Desktop** e espere o ícone da baleia ficar verde
  ("Engine running").
- **macOS:** arraste para Applications e abra.
- **Linux:** siga <https://docs.docker.com/engine/install/> (Docker Engine).

> ⚠️ O Docker Desktop precisa estar **aberto e rodando** sempre que você for
> usar `docker` ou subir o projeto. Se der erro "cannot connect to the Docker
> daemon", é porque o Docker Desktop está fechado.

Verificar:
```bash
docker --version
docker compose version
```

### 1.3 — WSL2 (só Windows — altamente recomendado)

O WSL2 dá um Linux real dentro do Windows. Docker e Kubernetes funcionam muito
melhor nele.

Abra o **PowerShell como Administrador** (clique direito → "Executar como
administrador") e rode:
```powershell
wsl --install
```
Reinicie o PC quando pedir. Na primeira vez o Ubuntu abre e pede para criar um
usuário e senha — guarde essa senha.

> A partir daqui, no Windows, você pode usar **tanto o PowerShell quanto o
> terminal do Ubuntu (WSL)**. Para a maioria das aulas o PowerShell basta.

### 1.4 — Python 3.11+

**Windows:** baixe em <https://www.python.org/downloads/> e, na primeira tela do
instalador, **marque "Add Python to PATH"** antes de clicar em Install.
**macOS:** `brew install python@3.11`
**Linux:** `sudo apt install -y python3 python3-pip python3-venv`

Verificar:
```bash
python --version    # Windows
python3 --version   # macOS / Linux
```

> 💡 Neste projeto você quase **não precisa** de Python instalado no PC, porque
> rodamos tudo dentro do container/devcontainer. Mas é bom ter.

### 1.5 — AWS CLI v2 (falar com a AWS pelo terminal)

A "AWS CLI" é o programa que executa comandos da AWS (`aws ...`).

**Windows (PowerShell):**
```powershell
msiexec.exe /i https://awscli.amazonaws.com/AWSCLIV2.msi
```
Ou baixe o instalador em <https://awscli.amazonaws.com/AWSCLIV2.msi> e dê 2 cliques.

**macOS:**
```bash
curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o "AWSCLIV2.pkg"
sudo installer -pkg AWSCLIV2.pkg -target /
```

**Linux:**
```bash
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip && sudo ./aws/install
```

Verificar (reabra o terminal):
```bash
aws --version
```
Deve aparecer algo como `aws-cli/2.x.x`.

### 1.6 — kubectl (controlar Kubernetes) — a partir da Aula 6

O `kubectl` é o comando que conversa com clusters Kubernetes.

**Windows (PowerShell):**
```powershell
winget install -e --id Kubernetes.kubectl
```
**macOS:** `brew install kubectl` *(é um atalho para a fórmula `kubernetes-cli`; ambos funcionam)*
**Linux:**
```bash
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
```

Verificar:
```bash
kubectl version --client
```

### 1.7 — Kind (Kubernetes local) — Aula 6

O Kind cria um cluster Kubernetes dentro do Docker, na sua máquina.

**Windows (PowerShell):**
```powershell
winget install -e --id Kubernetes.kind
```
**macOS:** `brew install kind`
**Linux:**
```bash
curl -Lo ./kind https://kind.sigs.k8s.io/dl/latest/kind-linux-amd64
sudo install -o root -g root -m 0755 kind /usr/local/bin/kind
```

Verificar:
```bash
kind --version
```

### 1.8 — eksctl (criar clusters na AWS) — Aula 8

**Windows (PowerShell):**
```powershell
winget install -e --id eksctl.eksctl
```
> 💡 O `eksctl` saiu da Weaveworks e hoje é mantido pela comunidade `eksctl-io`.
> Por isso o ID do winget é **`eksctl.eksctl`** (o antigo `Weaveworks.eksctl`
> não existe mais). Se o `winget` disser "Nenhum pacote encontrou os critérios",
> confira o ID com `winget search eksctl`.

**macOS:** `brew install eksctl`
**Linux:**
```bash
curl -sLO "https://github.com/eksctl-io/eksctl/releases/latest/download/eksctl_Linux_amd64.tar.gz"
tar -xzf eksctl_Linux_amd64.tar.gz && sudo mv eksctl /usr/local/bin
```

Verificar:
```bash
eksctl version
```

### 1.9 — Node.js + AWS CDK — Aula 11

O CDK precisa do Node.js.

**Windows (PowerShell):**
```powershell
winget install -e --id OpenJS.NodeJS.LTS
```
**macOS:** `brew install node`
**Linux:** `sudo apt install -y nodejs npm`

Depois instale o CDK (vale para todos os sistemas):
```bash
npm install -g aws-cdk
```

Verificar:
```bash
node --version
cdk --version
```

### 1.10 — VS Code + extensão Dev Containers (editor)

Baixe o VS Code em <https://code.visualstudio.com/>.
Abra o VS Code → ícone de extensões (quadradinhos na lateral) → procure e
instale **"Dev Containers"** (publisher Microsoft).

> Com isso você consegue abrir o projeto **dentro do container** (o jeito
> recomendado neste curso). Ver `docs/HOW_TO_USE.md`.

---

## Parte 2 — Configurar o AWS Academy Learner Lab

O **AWS Academy Learner Lab** é uma conta AWS temporária e com crédito limitado
que a instituição fornece. Tem regras especiais — leia com atenção.

### 2.1 — Entrar no laboratório

1. Acesse <https://awsacademy.instructure.com/> e faça login com a conta que a
   instituição passou.
2. Entre no curso → módulo **"Learner Lab"** → botão **"Start Lab"**.
3. Espere a **bolinha ao lado de "AWS"** ficar **verde** (pode levar ~1 min).
   - 🔴 vermelha = laboratório desligado
   - 🟡 amarela = ligando
   - 🟢 verde = pronto

> ⏰ **O laboratório tem tempo limitado (geralmente 4 horas)** e desliga
> sozinho. Quando reabrir, clique em "Start Lab" de novo. **Os dados em alguns
> serviços podem ser perdidos quando o lab encerra** — não conte com ele para
> guardar nada importante.

### 2.2 — Abrir o Console da AWS

Com a bolinha verde, clique em **"AWS"** (ao lado da bolinha). Abre o **Console
da AWS** numa nova aba — é a interface web com todos os serviços.

> 💡 **Sempre confira a região** no canto superior direito do Console. Deve
> estar em **N. Virginia (us-east-1)**. O Learner Lab só funciona bem nessa
> região. Se estiver em outra, troque.

### 2.3 — Pegar as credenciais para o terminal

Para usar a AWS pelo terminal (`aws`, `eksctl`, `cdk`), você precisa das
credenciais temporárias:

1. No Learner Lab, clique em **"AWS Details"** (perto do botão Start Lab).
2. Aparece um bloco **"AWS CLI"**. Clique em **"Show"**.
3. Vai aparecer um texto parecido com:
   ```ini
   [default]
   aws_access_key_id=ASIA....
   aws_secret_access_key=....
   aws_session_token=....
   ```
4. **Copie esse bloco inteiro.** Você vai colá-lo na Parte 3.

> ⚠️ **Essas credenciais expiram a cada sessão do lab.** Toda vez que você
> reiniciar o Learner Lab, precisa copiar de novo e repetir a Parte 3.

---

## Parte 3 — Conectar a AWS CLI ao Learner Lab

Você vai colar as credenciais copiadas num arquivo de configuração da AWS.

> 🧭 **Modo A (devcontainer):** edite este arquivo **no HOST** mesmo. O
> devcontainer monta o seu `~/.aws` para dentro do container, então o
> `aws`/`kubectl`/`eksctl`/`cdk` que rodam no container leem o **mesmo**
> arquivo automaticamente. Você configura **uma vez** e vale nos dois lugares.
> A cada nova sessão do Learner Lab, basta colar o bloco novo aqui no host — o
> container enxerga na hora (não precisa reabrir o container).
>
> ⚠️ No Modo A, **crie a pasta `~/.aws` no host ANTES** de abrir o devcontainer
> pela primeira vez (passo 3.2). Se ela não existir na hora de abrir, o Docker
> cria uma pasta vazia pertencente ao root e o container não consegue gravar.

### 3.1 — Onde fica o arquivo de credenciais

| Sistema | Caminho do arquivo |
| ------- | ------------------ |
| Windows | `C:\Users\SEU_USUARIO\.aws\credentials` |
| macOS / Linux | `~/.aws/credentials` |

### 3.2 — Criar/editar o arquivo (jeito fácil pelo terminal)

**Windows (PowerShell)** — abre o arquivo no Bloco de Notas (cria se não existir):
```powershell
mkdir "$env:USERPROFILE\.aws" -Force | Out-Null
notepad "$env:USERPROFILE\.aws\credentials"
```
Se o Bloco de Notas perguntar se quer criar o arquivo, clique em **Sim**.
**Cole** o bloco que você copiou no "AWS Details", salve (`Ctrl + S`) e feche.

**macOS / Linux:**
```bash
mkdir -p ~/.aws
nano ~/.aws/credentials
```
Cole o bloco, salve com `Ctrl + O` → Enter, saia com `Ctrl + X`.

### 3.3 — Definir a região padrão

**Windows (PowerShell):**
```powershell
notepad "$env:USERPROFILE\.aws\config"
```
Cole o conteúdo abaixo, salve e feche:
```ini
[default]
region = us-east-1
output = json
```

**macOS / Linux:**
```bash
nano ~/.aws/config
```
Cole o mesmo conteúdo, salve (`Ctrl + O`, Enter, `Ctrl + X`).

### 3.4 — Testar se funcionou

```bash
aws sts get-caller-identity
```
Se aparecer um JSON com `Account`, `Arn` e `UserId`, **está conectado!** 🎉
Se der erro de token expirado, repita a Parte 2.3 (credenciais novas).

### 3.5 — Anotar o ARN da `LabRole` (você vai precisar nas Aulas 8 e 11)

No Learner Lab, o AWS Academy cria uma role pronta chamada **`LabRole`**. Pegue
o ARN dela:
```bash
aws iam list-roles --query "Roles[?RoleName=='LabRole'].Arn" --output text
```
Guarde esse valor (algo como `arn:aws:iam::123456789012:role/LabRole`). Vamos
chamá-lo de **`<LabRole-ARN>`** no resto do guia.

---

## Parte 4 — Serviços AWS por aula

Resumo do que cada aula usa. **Você não precisa habilitar nada antecipadamente**
no Learner Lab — os serviços já vêm liberados. A tabela serve para você saber o
que esperar.

| Aula | Serviço(s) AWS | Já tem fallback local? |
| ---: | -------------- | ---------------------- |
| 1–4  | *(nenhum — roda tudo local/Docker)* | — |
| 5    | **S3** (armazenar uploads) | ✅ sim (`STORAGE_MODE=local`) |
| 6    | *(nenhum — Kubernetes local com Kind)* | ✅ é local |
| 7    | **ECR** (registry de imagem Docker) | ❌ precisa da AWS |
| 8    | **EKS** + **EC2** (nós) + **ELB** (load balancer) + **IAM** | ❌ precisa da AWS |
| 9    | **EKS** (auto-scaling) + **CloudWatch** + **Cost Explorer** | ❌ precisa da AWS |
| 10   | **DynamoDB** (eventos/logs) | ✅ sim (`EVENT_STORE_MODE=local`) |
| 11   | **CDK** → **CloudFormation** + **S3** + **ECR** + **VPC** | ❌ precisa da AWS |
| 12   | *(documentação e checklists)* | — |

> 💡 As Aulas 5 e 10 têm **fallback local**: se você não quiser gastar crédito,
> dá para completá-las sem AWS, usando disco/JSON local. As Aulas 7, 8, 9 e 11
> exigem a AWS de verdade.

---

## Parte 5 — Avisos importantes

> 🔴 **Leia tudo aqui ANTES de fazer as aulas de AWS. Estes são os erros que
> mais derrubam alunos e queimam crédito.**

### 5.1 — Crédito é limitado: destrua o que criar

O Learner Lab tem um **teto de crédito** (geralmente entre US$ 50 e US$ 100). Os
recursos que mais gastam: **EKS, instâncias EC2 e Load Balancers** — cobram
**por hora ligados**, mesmo sem uso.

✅ **Regra de ouro:** ao terminar cada aula de AWS, **apague os recursos**:
```bash
# Apagar deploy do Kubernetes/EKS
kubectl delete -f infra/k8s/aws/

# Apagar cluster EKS inteiro (Aula 8)
eksctl delete cluster --name cloudtask

# Apagar infraestrutura criada pelo CDK (Aula 11)
cdk destroy
```

E sempre clique em **"End Lab"** ao terminar a sessão.

### 5.2 — EKS no Learner Lab é o ponto mais delicado (Aulas 8 e 9)

O Learner Lab **não deixa você criar novas IAM roles**. O `eksctl`, por padrão,
**tenta criar roles** → e **falha**. Solução: mandar o `eksctl` **reutilizar a
`LabRole`** que já existe.

> ⚠️ **Teste isto com antecedência** (não em cima da aula). Se nem assim
> funcionar, avise o professor — alguns labs bloqueiam o EKS por completo, e
> nesse caso a turma usa uma alternativa.

Exemplo de criação reaproveitando a `LabRole` (substitua `<LabRole-ARN>` pelo
valor da Parte 3.5):
```bash
eksctl create cluster \
  --name cloudtask \
  --region us-east-1 \
  --nodes 2 \
  --node-type t3.small \
  --managed
```
> Se o comando acima falhar por causa de IAM, a turma receberá um arquivo de
> configuração `cluster.yaml` ajustado para a `LabRole`. Use:
> `eksctl create cluster -f cluster.yaml`.

### 5.3 — Use instâncias pequenas

Tipos grandes/GPU são bloqueados e caros. Para os nós do EKS use **`t3.small`**
ou **`t3.medium`**. Nunca peça dezenas de nós — **2 nós bastam** para o curso.

### 5.4 — CDK precisa de "bootstrap" (Aula 11)

Antes do primeiro `cdk deploy`, rode uma vez:
```bash
cdk bootstrap aws://SEU_ACCOUNT_ID/us-east-1
```
O `SEU_ACCOUNT_ID` aparece no resultado de `aws sts get-caller-identity`
(campo `Account`). Se o bootstrap reclamar de permissão IAM, peça orientação —
no Learner Lab pode ser necessário limitar as stacks a S3 + ECR.

### 5.5 — Cost Explorer demora a "ligar"

Na Aula 9 usaremos o **Cost Explorer**. Ao habilitá-lo pela primeira vez, a AWS
leva **até 24 horas** para começar a mostrar dados. **Ative no início da
semana**, não na hora da aula.

### 5.6 — As credenciais expiram

Toda vez que o lab reiniciar, as chaves mudam. Se um comando `aws`/`eksctl`/`cdk`
começar a dar erro de "token expirado" ou "credentials", **refaça a Parte 2.3 e
3.2** (copiar credenciais novas).

---

## Parte 6 — Checklist rápido por sessão

Faça **toda vez** que for trabalhar nas aulas de AWS:

```text
[ ] 1. Abrir Docker Desktop (esperar ficar verde)
[ ] 2. Learner Lab → Start Lab → esperar bolinha verde
[ ] 3. AWS Details → copiar bloco "AWS CLI"
[ ] 4. Colar em ~/.aws/credentials (Parte 3.2)
[ ] 5. Testar:  aws sts get-caller-identity
[ ] 6. Trabalhar na aula
[ ] 7. AO TERMINAR: apagar recursos (kubectl delete / eksctl delete / cdk destroy)
[ ] 8. End Lab
```

---

## Parte 7 — Solução de problemas

| Erro / sintoma | Causa provável | Como resolver |
| -------------- | -------------- | ------------- |
| `command not found` / "não é reconhecido" | Ferramenta não instalada ou terminal não reaberto | Reabra o terminal; se persistir, reinstale (Parte 1) |
| `Cannot connect to the Docker daemon` | Docker Desktop fechado | Abra o Docker Desktop e espere ficar verde |
| `Unable to locate credentials` | Não configurou o `~/.aws/credentials` | Faça a Parte 3.2 |
| `ExpiredToken` / `The security token included in the request is expired` | Sessão do lab expirou | Copie credenciais novas (Parte 2.3 + 3.2) |
| `AccessDenied` ao criar role/usuário | Learner Lab não permite criar IAM | Reutilize a `LabRole` (Parte 5.2) |
| `eksctl` falha criando cluster | Restrição de IAM do lab | Ver Parte 5.2; use `cluster.yaml` com a `LabRole` |
| Conta com pouco crédito / lab não liga | Crédito esgotado | Avise o professor — pode ser preciso resetar o lab |
| Região errada (recursos "somem") | Console em região diferente de us-east-1 | Troque para **N. Virginia (us-east-1)** no canto superior direito |

---

## Referências

- Guia geral de uso do repositório: [`HOW_TO_USE.md`](HOW_TO_USE.md)
- Roadmap das aulas: [`ROADMAP.md`](ROADMAP.md)
- Lista de tarefas: [`TAREFAS.md`](TAREFAS.md)
- AWS CLI: <https://docs.aws.amazon.com/cli/>
- eksctl: <https://eksctl.io/>
- AWS CDK: <https://docs.aws.amazon.com/cdk/v2/guide/home.html>
