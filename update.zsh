#!/usr/bin/env zsh

source "$HOME/.shellenv" || exit
export SSH_AUTH_SOCK=${SSH_AUTH_SOCK:-${ZSH_SSH_AGENT_SOCK:-$HOME/.ssh/auth_sock}}

function do_update {
  setopt local_options err_return
  local update_lock_fd

  cd ~/.local/share/chezmoi

  zmodload zsh/system || return
  touch .git/chezmoi-update.lock || return
  zsystem flock -t 0 -f update_lock_fd .git/chezmoi-update.lock 2>/dev/null || return 0

  {
    git fetch

    PREV=$(git rev-parse HEAD)
    git reset --hard origin/master
    git -P diff --stat $PREV HEAD

    git submodule update --recursive

    chezmoi apply
  } always {
    zsystem flock -u "$update_lock_fd"
  }
}

if ! (do_update); then
  if [[ -n "$TMUX_PANE" ]]; then
    tmux rename-window -t "$TMUX_PANE" "!ERROR! chezmoi update"
    read -s
  fi
  exit 1
fi
