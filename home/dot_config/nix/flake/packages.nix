{ pkgs, inputs }:

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
    bash
    nixVersions.latest

    gcc.cc.lib

    rsync
    curl
    jaq
    htop
    nettools
    file
    patchelf
    tcpdump
    dig
    dust
    fd
    sd

    inputs.nix-index.packages.${pkgs.system}.nix-index-with-db
  ] ++ optionals stdenv.isLinux [
    (lib.hiPrio glibcLocalesUtf8)
    glibc.out

    inotify-tools
  ] ++ optionals stdenv.isDarwin [
    coreutils-full
  ];
}
