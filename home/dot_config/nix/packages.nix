{ pkgs ? import <nixpkgs> {} }:

with pkgs;
buildEnv {
  name = "packages";
  paths = [
    chezmoi
    git
    tmux
    zsh
    nix
    glibcLocalesUtf8

    curl
    jq
    htop
    nettools
    file
  ];
}
