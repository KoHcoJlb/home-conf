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
    glibcLocalesUtf8

    rsync
    curl
    jq
    htop
    nettools
    file
  ];
}
