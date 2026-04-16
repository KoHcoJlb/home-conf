{ pkgs, inputs }:

with pkgs;
with lib;

let
  inherit (inputs.self) local;

in
buildEnv {
  name = "packages";
  extraOutputsToInstall = [ "man" ];
  postBuild = ''
    ln -s ${inputs.nixpkgs} $out/share/nixpkgs
  '';
  paths = [
    chezmoi
    pkgs.gitCustom or git
    tmux
    zsh
    bash

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

    (_7zz.override {
      enableUnfree = true;
    })

    inputs.nix-index.packages.${pkgs.stdenv.hostPlatform.system}.nix-index-with-db
  ]
  ++ optionals stdenv.isLinux [
    (lib.hiPrio glibcLocalesUtf8)
    glibc.out

    inotify-tools
  ]
  ++ optionals stdenv.isDarwin [
    coreutils-full
  ]
  ++ optional (local.installNix or true) nixVersions.latest
  ++ (local.extraPackages or (ps: [ ])) pkgs;
}
