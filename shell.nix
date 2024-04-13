{ pkgs ? import <nixpkgs> { } }:
pkgs.mkShell {
  nativeBuildInputs = with pkgs.buildPackages; [
    python312
    libxml2
    libxslt
  ];
  shellHook = ''
    python -m venv venv
    source venv/bin/activate
  '';
}