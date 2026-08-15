#!/usr/bin/env bash
# Build and qualify the signed Lyra OS Server Beta 1 publication bundle.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
WORK_DIR="$REPO_ROOT/kiwi/.kiwi/test-$(id -u)-server"
BUILD_DIR="$WORK_DIR/build"
ARTIFACT_DIR="$WORK_DIR/iso"
EVIDENCE_DIR=""
ARTIFACTS_ONLY=0

usage() {
  echo "Uso: $0 [--artifacts-only] --evidence-dir DIRETÓRIO" >&2
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --artifacts-only) ARTIFACTS_ONLY=1 ;;
    --evidence-dir) shift; EVIDENCE_DIR="${1:-}" ;;
    -h|--help) usage; exit 0 ;;
    *) echo "ERRO: opção desconhecida: $1" >&2; usage; exit 2 ;;
  esac
  shift
done
[ -n "$EVIDENCE_DIR" ] || { usage; exit 2; }
EVIDENCE_DIR="$(readlink -f "$EVIDENCE_DIR")"

cd "$REPO_ROOT"
./scripts/server-release.py check
./scripts/image-build.py validate --profile server \
  --release-file release-server.toml --manifest image-build-server.toml

VERSION="$(./scripts/server-release.py field version_id)"
ISO_NAME="$(./scripts/server-release.py field iso_filename)"
[ "$VERSION" = 2026.08-beta1 ] || {
  echo "ERRO: release-server.toml não aponta para 2026.08-beta1." >&2
  exit 1
}

if [ "$ARTIFACTS_ONLY" -eq 0 ]; then
  sudo -v
  ./kiwi/test/build-and-run-vm.sh --build-only --profile server
fi

ISO="$ARTIFACT_DIR/$ISO_NAME"
PREFIX="${ISO_NAME%.iso}"
BUILD_MANIFEST="$ISO.manifest.json"
for file in "$ISO" "$BUILD_MANIFEST" "$BUILD_DIR/$PREFIX.packages" "$BUILD_DIR/$PREFIX.verified"; do
  [ -s "$file" ] || { echo "ERRO: artefato ausente: $file" >&2; exit 1; }
done

COMMIT="$(python3 - "$BUILD_MANIFEST" <<'PY'
import json, pathlib, re, sys
d = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
c = d.get("source", {}).get("commit", "")
if d.get("version") != "2026.08-beta1" or d.get("source", {}).get("dirty") is not False:
    raise SystemExit("ERRO: manifesto não representa uma Beta 1 de árvore limpa")
if not re.fullmatch(r"[0-9a-f]{40}", c):
    raise SystemExit("ERRO: commit inválido")
print(c)
PY
)"
git cat-file -e "$COMMIT^{commit}"
install -m 0644 "$BUILD_DIR/$PREFIX.packages" "$ARTIFACT_DIR/$PREFIX.packages"
install -m 0644 "$BUILD_DIR/$PREFIX.verified" "$ARTIFACT_DIR/$PREFIX.verified"
./scripts/release-artifacts.py generate --iso "$ISO" \
  --packages "$ARTIFACT_DIR/$PREFIX.packages" \
  --verified "$ARTIFACT_DIR/$PREFIX.verified" --output-dir "$ARTIFACT_DIR" \
  --commit "$COMMIT" --release-file release-server.toml --product "Lyra OS Server"
install -m 0644 "$REPO_ROOT/docs/releases/lyra-os-server-2026.08-beta1.md" \
  "$ARTIFACT_DIR/README.md"

gpg --detach-sign --armor --output "$ARTIFACT_DIR/$PREFIX.iso.sha256.asc" \
  "$ARTIFACT_DIR/$PREFIX.iso.sha256"
gpg --verify "$ARTIFACT_DIR/$PREFIX.iso.sha256.asc" "$ARTIFACT_DIR/$PREFIX.iso.sha256"
(cd "$ARTIFACT_DIR" && sha256sum -c "$PREFIX.iso.sha256")

TEST_ARGS=()
for name in obs-repositories live-session installer first-boot uefi-secure-boot hardware-matrix; do
  file="$EVIDENCE_DIR/$name-result.json"
  [ -s "$file" ] || { echo "ERRO: evidência ausente: $file" >&2; exit 1; }
  TEST_ARGS+=(--test-result "$name=$file")
done
./scripts/image-build.py artifact-manifest --profile server \
  --release-file release-server.toml --manifest image-build-server.toml \
  "$ARTIFACT_DIR" --output "$ARTIFACT_DIR/$PREFIX.evidence.json" "${TEST_ARGS[@]}"

echo "Bundle Server Beta 1 assinado e qualificado em: $ARTIFACT_DIR"
