{ config, pkgs, ... }:

{
  imports = [
    ./auto-update.nix
    ./packages.nix
    ./zsh.nix
  ];

  # This value determines the Home Manager release that your
  # configuration is compatible with. This helps avoid breakage
  # when a new Home Manager release introduces backwards
  # incompatible changes
  #
  # You can update Home Manager without changing this value. See
  # the Home Manager release notes for a list of state version
  # changes in each release.
  home = {
    stateVersion = "22.11";
  };

  # Let Home Manager install and manage itself.
  programs = {
    home-manager.enable = true;

    git = {
      enable = true;
      userName = "Igor Stuzhuk (KoHcoJlb)";
      userEmail = "fujitsigor@gmail.com";
    };
  };
}
