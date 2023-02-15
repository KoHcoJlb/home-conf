{ pkgs ? import <nixpkgs> {}
, extraConf ? null
}:

let
  home-manager = import (fetchGit {
    url = "https://github.com/nix-community/home-manager.git";
  }) { inherit pkgs; };
in
{
  install = pkgs.stdenv.mkDerivation {
    name = "install";
    nativeBuildInputs = [ home-manager.home-manager pkgs.nix pkgs.git ];
    shellHook = ''
    set -e

    conf_dir=$HOME/.config/nixpkgs
    conf_file=$conf_dir/home.nix

    mkdir -p $conf_dir

    cat > $conf_file <<EOF
    { ... }:

    {
      imports = [
        (fetchGit {
          url = "https://github.com/KoHcoJlb/home-conf.git";
        } + /home.nix)
        ${if extraConf != null then "./${builtins.baseNameOf extraConf}" else ""}
      ];

      home = {
        username = "$USER";
        homeDirectory = "$HOME";
      };
    }
    EOF

    ${if extraConf != null then "cp ${toString extraConf} $conf_dir/" else ""}

    nix-channel --add https://github.com/nix-community/home-manager/archive/master.tar.gz home-manager
    nix-channel --update

    home-manager build
    nix-env -e "*"
    home-manager switch
    exit 0
    '';
  };
}
