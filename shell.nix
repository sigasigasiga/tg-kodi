{ pkgs ? import <nixpkgs> {} }:

let
  python = pkgs.python312;
in
pkgs.mkShell {
  packages = [
    python
    python.pkgs.pip
    pkgs.pyright
  ];

  shellHook = ''
    if [ ! -d .venv ]; then
      ${python.interpreter} -m venv .venv
    fi
    source .venv/bin/activate
  '';
}
