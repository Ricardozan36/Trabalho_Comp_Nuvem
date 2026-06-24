#!/usr/bin/env bash
# =============================================================================
# post-create.sh — roda UMA vez, após o devcontainer ser criado.
# -----------------------------------------------------------------------------
# Instala as ferramentas que não têm feature oficial confiável (eksctl e o
# AWS CDK) e ajusta as permissões das credenciais montadas do host.
#
# Roda como o usuário `appuser`, que tem sudo NOPASSWD apenas no target `dev`
# (ver Dockerfile). POR QUÊ sudo aqui: instalar binários em /usr/local/bin e
# pacotes npm globais exige escrita em diretórios do sistema.
# =============================================================================
# NÃO usamos `set -e`: se a instalação de uma ferramenta falhar (ex.: sem rede
# no primeiro build), queremos AVISAR mas NÃO abortar a criação do container.
# Um container que sobe "quase pronto" é melhor que um que não sobe.
set -uo pipefail

echo "==> [post-create] Ajustando dono das credenciais montadas (host -> container)..."
# Se a pasta foi criada pelo Docker como root (host não tinha ~/.aws ou ~/.kube),
# devolvemos a posse ao appuser para o AWS CLI / kubectl conseguirem ler/escrever.
# O '|| true' evita quebrar o build se a pasta não existir.
sudo mkdir -p /home/appuser/.aws /home/appuser/.kube
sudo chown -R appuser:appuser /home/appuser/.aws /home/appuser/.kube || true
chmod 700 /home/appuser/.aws /home/appuser/.kube || true

# Cache do usuário GRAVÁVEL: o `jsii` (runtime do AWS CDK em Python) EXTRAI
# módulos nativos para ~/.cache/aws/jsii e PRECISA escrever ali — senão o
# `cdk synth` morre com "EACCES: permission denied, mkdir .../jsii/package-cache".
# (E o cache do pip também mora aqui.) Em rebuilds essa pasta às vezes nasce
# como root; devolvemos a posse ao appuser.
sudo mkdir -p /home/appuser/.cache/aws/jsii /home/appuser/.cache/pip
sudo chown -R appuser:appuser /home/appuser/.cache || true

# Posse do projeto para o appuser. POR QUÊ: dependendo de como o workspace é
# montado (bind mount do Windows, clone feito por root, etc.) os arquivos podem
# aparecer como root -> o aluno não consegue editar/rodar/commitar. Devolvemos a
# posse ao appuser. O '|| true' evita quebrar o build se o mount não permitir
# (ex.: bind mount onde a posse é virtual).
sudo chown -R appuser:appuser /app 2>/dev/null || true

# Pasta do histórico do zsh, persistida num volume (ver devcontainer.json).
# POR QUÊ: o histórico de comandos sobrevive a rebuilds do container.
sudo mkdir -p /commandhistory
sudo chown -R appuser:appuser /commandhistory || true

echo "==> [post-create] Permitindo appuser acessar o socket do Docker..."
# O docker-outside-of-docker monta /var/run/docker.sock do host. A feature
# normalmente alinha o grupo dele com a entrypoint, mas com overrideCommand:false
# nossa CMD do uvicorn pula essa entrypoint. Detectamos o GID do socket e
# garantimos que appuser pertença ao grupo correspondente.
# POR QUÊ NÃO chmod 666: o socket é bind-mount; mudar perm pode afetar o host.
if [ -S /var/run/docker.sock ]; then
  SOCK_GID="$(stat -c '%g' /var/run/docker.sock)"
  if [ "${SOCK_GID}" = "0" ]; then
    # Socket pertence ao root (caso comum no Docker Desktop). Coloca appuser no grupo root.
    sudo usermod -aG root appuser || true
  else
    # Cria/ajusta grupo "docker" com o mesmo GID do socket e inclui appuser.
    if getent group docker >/dev/null 2>&1; then
      CUR_GID="$(getent group docker | cut -d: -f3)"
      [ "${CUR_GID}" = "${SOCK_GID}" ] || sudo groupmod -g "${SOCK_GID}" docker || true
    else
      sudo groupadd -g "${SOCK_GID}" docker || true
    fi
    sudo usermod -aG docker appuser || true
  fi
  echo "    -> abra um TERMINAL NOVO para o grupo entrar em vigor (ou: 'newgrp docker')."
else
  echo "    -> socket Docker não encontrado (docker-outside-of-docker indisponível)."
fi

echo "==> [post-create] Instalando eksctl..."
# Detecta a arquitetura para baixar o binário certo (amd64 x arm64).
ARCH_RAW="$(uname -m)"
case "${ARCH_RAW}" in
  x86_64)            ARCH="amd64" ;;
  aarch64 | arm64)   ARCH="arm64" ;;
  *)                 ARCH="amd64" ;;
esac
EKSCTL_URL="https://github.com/eksctl-io/eksctl/releases/latest/download/eksctl_$(uname -s)_${ARCH}.tar.gz"
# '|| echo' impede que uma falha de rede aborte a criação do container.
(curl -sSL "${EKSCTL_URL}" | sudo tar -xz -C /usr/local/bin && sudo chmod +x /usr/local/bin/eksctl) \
  || echo "AVISO: falha ao instalar eksctl (instale depois com: bash .devcontainer/post-create.sh)"

echo "==> [post-create] Instalando AWS CDK (npm global)..."
sudo npm install -g aws-cdk \
  || echo "AVISO: falha ao instalar aws-cdk (instale depois com: sudo npm install -g aws-cdk)"

echo "==> [post-create] Instalando libs Python do CDK (aws-cdk-lib)..."
# O `cdk synth` roda `python3 app.py`, que importa `aws_cdk`. O CLI (npm acima)
# NÃO traz essa lib Python — ela vem do requirements do CDK. Sem isto, o deploy
# falha com "No module named 'aws_cdk'".
python3 -m pip install --user -q -r /app/infra/cdk/requirements.txt \
  || echo "AVISO: falha ao instalar libs do CDK (instale: python3 -m pip install --user -r infra/cdk/requirements.txt)"

echo "==> [post-create] Versões instaladas:"
# '|| true' para não abortar caso alguma ferramenta ainda não esteja no PATH.
python --version || true
aws --version    || true
kubectl version --client --output=yaml 2>/dev/null | head -3 || true
eksctl version   || true
node --version   || true
cdk --version    || true
docker --version || true

echo "==> [post-create] Limpando safe.directory herdado do host..."
# O VS Code copia o ~/.gitconfig do HOST para dentro do container (para os
# commits saírem com seu nome/e-mail). Mas as entradas `safe.directory` do
# host costumam ser CAMINHOS DO WINDOWS (ex.: F:/...), que no Linux do container
# não são absolutos -> o git imprime "warning: safe.directory '...' not absolute"
# a cada chamada (o prompt chama git para mostrar a branch).
# POR QUÊ remover: tira o ruído e evita expor caminhos de outros projetos seus.
# IMPACTO: mantém nome/e-mail do gitconfig; só apaga os safe.directory inválidos.
git config --global --unset-all safe.directory 2>/dev/null || true
# Confia no diretório do projeto montado (e em qualquer um, dentro do container).
git config --global --add safe.directory /app
git config --global --add safe.directory '*'

# core.fileMode=false: ignora mudanças de BIT DE EXECUÇÃO dos arquivos.
# POR QUÊ: o bind mount do Windows para o container Linux apresenta as
# permissões/exec-bit de forma diferente do que o git gravou no índice. Sem
# isso, o git do container marca TODOS os arquivos como "modificados" (só por
# causa do modo), poluindo o `git status`. fileMode=false faz o git comparar
# apenas o CONTEÚDO, não o modo. RISCO: ínfimo — em containers raramente
# dependemos do exec-bit versionado (e os scripts que precisam já têm +x no índice).
git config --global core.fileMode false

echo "==> [post-create] Configurando o terminal (oh-my-zsh: plugins + tema)..."
# Plugins externos (não vêm no oh-my-zsh). Clonados na pasta custom do omz.
ZSH_CUSTOM="${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}"
if [ -d "$HOME/.oh-my-zsh" ]; then
  git clone --depth=1 https://github.com/zsh-users/zsh-autosuggestions \
    "$ZSH_CUSTOM/plugins/zsh-autosuggestions" 2>/dev/null \
    || echo "AVISO: falha ao clonar zsh-autosuggestions"
  git clone --depth=1 https://github.com/zsh-users/zsh-syntax-highlighting \
    "$ZSH_CUSTOM/plugins/zsh-syntax-highlighting" 2>/dev/null \
    || echo "AVISO: falha ao clonar zsh-syntax-highlighting"
  # Aplica o nosso .zshrc (tema fino-time + plugins + atalhos do projeto).
  # O repo está montado em /app; copiamos de lá.
  cp /app/.devcontainer/.zshrc "$HOME/.zshrc" \
    || echo "AVISO: não foi possível copiar o .zshrc do projeto"
else
  echo "AVISO: oh-my-zsh não encontrado (feature common-utils não instalou?)."
fi

echo "==> [post-create] Pronto. Lembre: 'kind' (Aula 6) roda no HOST, não aqui."
