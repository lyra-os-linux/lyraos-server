#!/usr/bin/env bash
# Build Lyra OS Server Alpha 2 and prepare the unsigned publication bundle.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$REPO_ROOT/kiwi/.kiwi/test-$(id -u)-server/build"
ARTIFACT_DIR="$REPO_ROOT/kiwi/.kiwi/test-$(id -u)-server/iso"
EXPECTED_VERSION="2026.08-alpha2"
ARTIFACTS_ONLY=0

usage() {
  cat <<EOF
Uso: ./scripts/build-server-alpha2.sh [--artifacts-only]

Sem opções, constrói e valida uma nova ISO Server. --artifacts-only reutiliza
a ISO Alpha 2 já validada e prepara o bundle de publicação sem executar
novamente o KIWI.
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --artifacts-only) ARTIFACTS_ONLY=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "ERRO: opção desconhecida: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

cd "$REPO_ROOT"

echo "Validando metadados do Lyra OS Server Alpha 2..."
./scripts/server-release.py check
./scripts/image-build.py validate \
  --profile server \
  --release-file release-server.toml \
  --manifest image-build-server.toml

VERSION="$(./scripts/server-release.py field version_id)"
ISO_NAME="$(./scripts/server-release.py field iso_filename)"
PREFIX="${ISO_NAME%.iso}"
if [ "$VERSION" != "$EXPECTED_VERSION" ]; then
  echo "ERRO: release-server.toml não aponta para $EXPECTED_VERSION." >&2
  exit 1
fi

if [ "$ARTIFACTS_ONLY" -eq 0 ]; then
  echo "Autenticando sudo para o build KIWI..."
  sudo -v
  echo "Iniciando o build da ISO Server (a VM existente não será alterada)..."
  ./kiwi/test/build-and-run-vm.sh --build-only --profile server
fi

ISO="$ARTIFACT_DIR/$ISO_NAME"
BUILD_MANIFEST="$ISO.manifest.json"
PACKAGES_SOURCE="$BUILD_DIR/$PREFIX.packages"
VERIFIED_SOURCE="$BUILD_DIR/$PREFIX.verified"

for file in "$ISO" "$BUILD_MANIFEST" "$PACKAGES_SOURCE" "$VERIFIED_SOURCE"; do
  if [ ! -s "$file" ]; then
    echo "ERRO: entrada de artefato ausente ou vazia: $file" >&2
    exit 1
  fi
done

COMMIT="$(python3 - "$BUILD_MANIFEST" "$EXPECTED_VERSION" <<'PY'
import json
import pathlib
import re
import sys

path = pathlib.Path(sys.argv[1])
expected_version = sys.argv[2]
document = json.loads(path.read_text(encoding="utf-8"))
commit = document.get("source", {}).get("commit", "")
if document.get("version") != expected_version:
    raise SystemExit("ERRO: versão inesperada no manifesto do build")
if document.get("source", {}).get("dirty") is not False:
    raise SystemExit("ERRO: o build não veio de uma árvore limpa")
if document.get("iso", {}).get("filename") != path.name.removesuffix(".manifest.json"):
    raise SystemExit("ERRO: nome da ISO diverge do manifesto do build")
if not re.fullmatch(r"[0-9a-f]{40}", commit):
    raise SystemExit("ERRO: commit inválido no manifesto do build")
print(commit)
PY
)"
git cat-file -e "$COMMIT^{commit}"

echo "Preparando inventário KIWI e artefatos derivados..."
install -m 0644 "$PACKAGES_SOURCE" "$ARTIFACT_DIR/$PREFIX.packages"
install -m 0644 "$VERIFIED_SOURCE" "$ARTIFACT_DIR/$PREFIX.verified"
./scripts/release-artifacts.py generate \
  --iso "$ISO" \
  --packages "$ARTIFACT_DIR/$PREFIX.packages" \
  --verified "$ARTIFACT_DIR/$PREFIX.verified" \
  --output-dir "$ARTIFACT_DIR" \
  --commit "$COMMIT" \
  --release-file release-server.toml \
  --product "Lyra OS Server"
install -m 0644 \
  "$REPO_ROOT/docs/releases/lyra-os-server-$EXPECTED_VERSION.md" \
  "$ARTIFACT_DIR/README.md"

echo "Validando checksum final..."
(cd "$ARTIFACT_DIR" && sha256sum -c "$PREFIX.iso.sha256")

echo "Bundle Server Alpha 2 pronto em: $ARTIFACT_DIR"
printf '  %s\n' \
  README.md \
  "$PREFIX.cdx.json" \
  "$PREFIX.iso" \
  "$PREFIX.iso.manifest.json" \
  "$PREFIX.iso.sha256" \
  "$PREFIX.packages" \
  "$PREFIX.report" \
  "$PREFIX.spdx.json" \
  "$PREFIX.verified"
echo "Alpha 2 não usa assinatura GPG da ISO; ela passa a ser obrigatória na Beta 1."
