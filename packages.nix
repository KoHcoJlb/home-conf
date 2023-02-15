{ pkgs, ... }:

{
  home.packages = with pkgs; [
      bashInteractive
      coreutils
      ncurses
      util-linux
      git
      nix

      nano
      rsync
      htop
      tcpdump
      curl
    ];
}
