{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    flake-utils.url = "github:numtide/flake-utils";
    nix-index = {
      url = "github:nix-community/nix-index-database";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    { nixpkgs, flake-utils, self, ... }@inputs:
    {
      inherit (nixpkgs) lib;

      local = if builtins.pathExists ./local.nix then import ./local.nix else {};
    }
    // flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = import nixpkgs {
          inherit system;
          config = {
            allowUnfree = true;
            allowUnsupportedSystem = true;
          };
          overlays = [
            (_final: prev: nixpkgs.lib.optionalAttrs prev.stdenv.hostPlatform.isDarwin {
              e2fsprogs = (prev.e2fsprogs.override { withFuse = true; }).overrideAttrs (old: {
                patches = (old.patches or []) ++ [ ./patches/e2fsprogs-darwin.patch ];

                # Avoid gettext starting CoreFoundation threads before fuse_daemonize.
                configureFlags = (old.configureFlags or []) ++ [ "--disable-nls" ];
              });
            })
          ] ++ (self.local.nixpkgs-overlays or []);
        };
      in
      {
        legacyPackages = pkgs;

        packages = {
          homeEnv = import ./packages.nix { inherit pkgs inputs; };
        };
      }
    );
}
