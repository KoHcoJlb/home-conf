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
    nixVersions.latest

    gcc.cc.lib

    rsync
    curlHTTP3
    jaq
    htop
    nettools
    file
    patchelf
    tcpdump
    dig
    dust

    inputs.nix-index.packages.${pkgs.system}.nix-index-with-db
  ] ++ optionals stdenv.isLinux [
    (lib.hiPrio glibcLocalesUtf8)
    glibc.out

    inotify-tools
  ] ++ optionals stdenv.isDarwin [
    coreutils-full
  ];
}
