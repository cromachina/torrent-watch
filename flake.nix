{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    flake-utils.url = "github:numtide/flake-utils";
    poetry2nix.url = "github:nix-community/poetry2nix";
  };
  outputs = {
    self,
    nixpkgs,
    flake-utils,
    poetry2nix,
  }:
  flake-utils.lib.eachDefaultSystem (
    system:
    let
      pkgs = nixpkgs.legacyPackages.${system};
      inherit (poetry2nix.lib.mkPoetry2Nix { inherit pkgs; }) mkPoetryApplication mkPoetryEnv;
      config = {
        projectDir = self;
        preferWheels = true;
      };
    in
    {
      packages.default = mkPoetryApplication config;
      devShells.default = pkgs.mkShellNoCC {
        packages = with pkgs; [
          poetry
          (mkPoetryEnv config)
        ];
      };
    }
  );
}
