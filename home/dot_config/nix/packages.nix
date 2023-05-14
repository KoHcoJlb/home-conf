{ pkgs ? import <nixpkgs> {} }:

with pkgs;
buildEnv {
  name = "packages";
  paths = [
    chezmoi
    git
    tmux
    zsh
    nixVersions.unstable

    (lib.hiPrio glibcLocalesUtf8)
    glibc.out

    gcc.cc.lib

    rsync
    curl
    jq
    htop
    nettools
    file
    patchelf
  ];
}
