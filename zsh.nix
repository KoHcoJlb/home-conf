{ pkgs, ... }:

{
  programs.zsh =
  let
    oh-my-zsh = pkgs.oh-my-zsh.overrideAttrs (final: previous: {
      src = builtins.fetchGit {
        url = "https://github.com/KoHcoJlb/ohmyzsh.git";
        submodules = true;
      };
    });
  in
  {
    enable = true;

    envExtra = ''
    ZSH="${oh-my-zsh}/share/oh-my-zsh"
    DISABLE_AUTO_UPDATE="true"
    '';
    initExtra = ''
    source $ZSH/zshrc
    '';

    # NIX's zsh sources global zprofile from /etc/zprofile
    # but on Archlinux it's located at /etc/zsh/zprofile
    profileExtra = ''
    if [[ -e /etc/zsh/zprofile ]]
    then
      . /etc/zsh/zprofile
    fi
    '';
  };

  home.packages = [ pkgs.tmux ];
}
