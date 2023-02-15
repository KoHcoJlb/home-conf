#!/usr/bin/env sh

set -e

tmpdir=$(mktemp --tmpdir -d chezmoi_XXXXXX)
trap "rm -rf -- $tmpdir" EXIT

args=$@

if [ $# = 0 ]
then
  args="init --apply KoHcoJlb/home-conf"
fi

export BINDIR=$tmpdir
sh -c "$(curl -fsLS get.chezmoi.io)" -- -- $args

exec ~/.nix-packages/bin/zsh
