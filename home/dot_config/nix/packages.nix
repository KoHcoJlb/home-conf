{ pkgs ? import <nixpkgs> {} }:

with pkgs;
buildEnv {
  name = "packages";
  extraOutputsToInstall = ["man"];
  paths = [
    chezmoi
    git
    tmux
    zsh
    nixVersions.latest

    (lib.hiPrio glibcLocalesUtf8)
    glibc.out

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
    inotify-tools
  ];
}
