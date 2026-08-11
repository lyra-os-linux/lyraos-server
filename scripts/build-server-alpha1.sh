#!/usr/bin/env bash
# Build and validate the Lyra OS Server Alpha 1 ISO from a real terminal.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$REPO_ROOT"

echo "Validando metadados do Lyra OS Server Alpha 1..."
./scripts/server-release.py check

if [ "$(./scripts/server-release.py field version_id)" != "2026.08-alpha1" ]; then
  echo "ERRO: release-server.toml não aponta para 2026.08-alpha1." >&2
  exit 1
fi

echo "Autenticando sudo para o build KIWI..."
sudo -v

echo "Iniciando o build da ISO server (a VM existente não será alterada)..."
exec ./kiwi/test/build-and-run-vm.sh --build-only --profile server
