{ pkgs ? import <nixpkgs> {} }:

with pkgs;
with lib;

buildEnv {
  name = "packages";
  extraOutputsToInstall = ["man"];
  paths = [
    chezmoi
    git
    tmux
    zsh
    nixVersions.latest

    gcc.cc.lib

    rsync
    curl
    jq
    yq-go
    htop
    nettools
    file
    patchelf
    tcpdump
    dig
  ] ++ optionals stdenv.isLinux [
    (lib.hiPrio glibcLocalesUtf8)
    glibc.out

    inotify-tools
  ];
}
