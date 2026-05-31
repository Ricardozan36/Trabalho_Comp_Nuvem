# =============================================================================
# .zshrc do devcontainer — CloudTask AI SaaS
# -----------------------------------------------------------------------------
# Copiado para ~/.zshrc pelo post-create.sh. Configura o oh-my-zsh com um tema
# de DUAS LINHAS e informativo, além de plugins úteis para o projeto.
#
# POR QUÊ o tema "fino-time": mostra, em duas linhas, usuário@host, diretório
# atual, branch do git e a hora — exatamente o "onde estou?" que ajuda o aluno.
# Usa só caracteres comuns (├ ╰ ─ ‹ ›), funcionando na maioria das fontes de
# terminal SEM precisar de Nerd Font. Se algum glifo (a setinha ➜) não aparecer
# bonito na sua fonte, o prompt continua 100% funcional.
# =============================================================================

export ZSH="$HOME/.oh-my-zsh"

# Tema de duas linhas com bastante informação (ver comentário acima).
ZSH_THEME="fino-time"

# Plugins do oh-my-zsh: adicionam autocompletar e atalhos por ferramenta.
#   git           -> status/branch no prompt, aliases (gst, gco, gp...)
#   aws           -> completar aws-cli; asp/agp p/ trocar/ver profile
#   docker        -> completar docker
#   docker-compose-> completar docker compose
#   kubectl       -> alias `k` + completar kubectl
#   helm          -> completar helm
#   python / pip  -> completar python e pip
#   postgres      -> aliases para psql/pg_dump etc.
#   vscode        -> helper `code` dentro do container
#   colored-man-pages -> man pages coloridas
#   zsh-autosuggestions     -> sugere comandos do histórico enquanto digita
#   zsh-syntax-highlighting -> colore o comando (verde=ok, vermelho=erro)  [POR ÚLTIMO]
plugins=(
  git
  aws
  docker
  docker-compose
  kubectl
  helm
  python
  pip
  postgres
  vscode
  colored-man-pages
  zsh-autosuggestions
  zsh-syntax-highlighting
)

source "$ZSH/oh-my-zsh.sh"

# ----- VS Code: shell integration -------------------------------------------
# Habilita o "sticky scroll" (linha do comando fixa no topo enquanto rolamos
# a saída longa), decorações de prompt/exit code e command markers.
# Tentamos 2 caminhos para achar o script `shellIntegration.zsh`:
#   1. via `code --locate-shell-integration-path zsh` (oficial)
#   2. procurando direto no ~/.vscode-server (fallback, caso `code` não esteja no PATH)
if [[ "$TERM_PROGRAM" == "vscode" ]]; then
    _vsc_int=""
    if command -v code &>/dev/null; then
        _vsc_int="$(code --locate-shell-integration-path zsh 2>/dev/null)"
    fi
    if [[ -z "$_vsc_int" || ! -f "$_vsc_int" ]]; then
        _vsc_int="$(find ~/.vscode-server -name 'shellIntegration.zsh' 2>/dev/null | head -1)"
    fi
    if [[ -n "$_vsc_int" && -f "$_vsc_int" ]]; then
        . "$_vsc_int"
    fi
    unset _vsc_int
fi

# ----- Histórico de comandos -------------------------------------------------
# As setas ↑/↓ navegam no histórico e ←/→ movem dentro do comando (zsh já faz
# isso por padrão). Guardamos o histórico em /commandhistory (volume), então
# ele SOBREVIVE a rebuilds do container.
HISTFILE=/commandhistory/.zsh_history
HISTSIZE=10000
SAVEHIST=10000
setopt SHARE_HISTORY        # compartilha histórico entre abas/sessões
setopt HIST_IGNORE_ALL_DUPS # não guarda comandos duplicados
setopt HIST_IGNORE_SPACE    # comando começando com espaço não vai pro histórico

# Binários Python instalados com `pip install --user` (uvicorn, pytest, ruff...).
export PATH="$HOME/.local/bin:$PATH"

# ----- Atalhos do projeto ----------------------------------------------------
alias dc='docker compose'
alias dcup='docker compose up'
alias dcdown='docker compose down'
alias dclogs='docker compose logs -f api'
alias k='kubectl'
alias serve='uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload'
alias health='curl -s http://localhost:8000/health; echo'
alias ready='curl -s http://localhost:8000/health/ready; echo'
alias tasks='curl -s http://localhost:8000/tasks; echo'
alias t='pytest -q'
alias tv='pytest -v'
alias cov='pytest --cov=app'
alias psqldb='psql "$DATABASE_URL"'

# Mostra o contexto atual do Kubernetes (qual cluster) — útil nas Aulas 6-9.
alias kctx='kubectl config current-context 2>/dev/null || echo "(sem cluster k8s configurado)"'
# Mostra a identidade/conta AWS ativa — útil nas Aulas 5,7-11.
alias whoaws='aws sts get-caller-identity 2>/dev/null || echo "(sem credencial AWS ativa)"'

# ----- Prompt "transient" ----------------------------------------------------
# Quando o aluno aperta Enter, a linha do comando que acabou de rodar é redesenhada
# com um prompt MÍNIMO ("> comando"), deixando o histórico do terminal limpo. A
# próxima linha (aguardando comando) volta a ter o prompt cheio do tema fino-time.
# POR QUÊ: prompt longo de 2 linhas a cada comando vira poluição visual no log.
_cloudtask_transient_accept() {
    local _ORIG_PROMPT="$PROMPT"
    local _ORIG_RPROMPT="$RPROMPT"
    # `%F{8}` = cinza (subdued), `%D{...}` = data/hora pelo zsh.
    # Formato: [YYYY-MM-DD HH:MM:SS] > comando
    PROMPT='%F{8}[%D{%Y-%m-%d %H:%M:%S}]%f > '
    RPROMPT=''
    zle reset-prompt
    PROMPT="$_ORIG_PROMPT"
    RPROMPT="$_ORIG_RPROMPT"
    zle accept-line
}
zle -N _cloudtask_transient_accept
bindkey '^M' _cloudtask_transient_accept   # Enter (carriage return)

# Mensagem de boas-vindas (ajuda o aluno a se localizar).
echo "CloudTask AI SaaS — devcontainer. App em http://localhost:8000/docs | testes: tv | logs: dclogs"
