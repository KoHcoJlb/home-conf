#!/usr/bin/env zsh

source "$HOME/.shellenv" || exit
export SSH_AUTH_SOCK=${SSH_AUTH_SOCK:-${ZSH_SSH_AGENT_SOCK:-$HOME/.ssh/auth_sock}}

function do_update {
  setopt local_options err_return
  local update_lock_fd previous target signature

  cd ~/.local/share/chezmoi

  zmodload zsh/system || return
  touch .git/chezmoi-update.lock || return
  zsystem flock -t 0 -f update_lock_fd .git/chezmoi-update.lock 2>/dev/null || return 0

  {
    git fetch || return

    target=$(git rev-parse origin/master) || return
    signature=$(git -c gpg.ssh.allowedSignersFile="$PWD/allowed_signers" \
      -c gpg.openpgp.program=false -c gpg.x509.program=false \
      log -1 --format='%G?' "$target") || return
    case "$signature" in
      G) ;;
      N)
        print -u2 -r -- "Unsigned commit $target; refusing to update."
        return 1
        ;;
      *)
        print -u2 -r -- "Invalid or untrusted signature on commit $target."
        return 1
        ;;
    esac

    previous=$(git rev-parse HEAD) || return
    git reset --hard "$target" || return
    git -P diff --stat "$previous" HEAD || return

    git submodule update --recursive || return

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
