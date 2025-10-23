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
    { nixpkgs, flake-utils, ... }@inputs:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = import nixpkgs {
          inherit system;
          config.allowUnfree = true;
          overlays = if builtins.pathExists ./pkgs-overlays.nix then import ./pkgs-overlays.nix else [ ];
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
