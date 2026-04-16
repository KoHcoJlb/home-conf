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
          config.allowUnfree = true;
          overlays = self.local.nixpkgs-overlays or [];
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
