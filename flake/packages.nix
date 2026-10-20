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
    (callPackage ./atuin { })

    gcc.cc.lib

    rsync
    curl
    jaq
    htop
    btop
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

    (inputs.nix-index.packages.${pkgs.stdenv.hostPlatform.system}.nix-index-with-db.overrideAttrs
      (old: {
        buildCommand = old.buildCommand + ''
          # This home configuration always enables the modern Nix CLI.
          ${lib.getExe patch} -d "$out" -p1 < ${./patches/nix-index-modern-cli.patch}
        '';
      })
    )
  ]
  ++ optionals stdenv.hostPlatform.isLinux [
    (lib.hiPrio glibcLocalesUtf8)
    glibc.out

    inotify-tools
  ]
  ++ optionals stdenv.hostPlatform.isDarwin [
    coreutils-full
  ]
  ++ optional (local.installNix or true) nixVersions.latest
  ++ (local.extraPackages or (ps: [ ])) pkgs;
}
