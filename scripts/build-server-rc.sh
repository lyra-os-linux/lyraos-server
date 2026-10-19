#!/usr/bin/env bash
# Build and qualify the signed Lyra OS Server 16.1 release-candidate bundle.
# The candidate (RC number) comes from release-server.toml; this script serves
# every RC of the 16.1 cycle (RC 2, RC 3, ...) without per-iteration copies.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
WORK_DIR="${LYRA_TEST_WORK_DIR:-/var/tmp/lyraos-server-test-$(id -u)}"
BUILD_DIR="$WORK_DIR/build"
ARTIFACT_DIR="$WORK_DIR/iso"
ARTIFACTS_ONLY=0
RELEASE_SIGNING_FINGERPRINT="01B63EEDBE6B079126A0116EFA7353A131ECEFEB"

verify_release_signature() {
  local signature="$1" signed_file="$2" valid_fingerprint
  valid_fingerprint="$(gpg --batch --status-fd 1 --verify "$signature" "$signed_file" 2>/dev/null \
    | awk '$1 == "[GNUPG:]" && $2 == "VALIDSIG" { print $3 }')"
  [ "$valid_fingerprint" = "$RELEASE_SIGNING_FINGERPRINT" ] || {
    echo "ERRO: assinatura não pertence à chave oficial $RELEASE_SIGNING_FINGERPRINT." >&2
    exit 1
  }
}

usage() {
  echo "Uso: $0 [--artifacts-only]" >&2
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --artifacts-only) ARTIFACTS_ONLY=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "ERRO: opção desconhecida: $1" >&2; usage; exit 2 ;;
  esac
  shift
done
cd "$REPO_ROOT"
./scripts/server-release.py check
python3 ./scripts/image-build.py validate \
  --release-file release-server.toml --manifest image-build-server.toml

PRODUCT_VERSION="$(./scripts/server-release.py field product_version)"
STAGE="$(./scripts/server-release.py field stage)"
ITERATION="$(./scripts/server-release.py field release_iteration)"
VERSION="$(./scripts/server-release.py field version_id)"
ISO_NAME="$(./scripts/server-release.py field iso_filename)"
[ "$PRODUCT_VERSION" = 16.1 ] && [ "$STAGE" = rc ] || {
  echo "ERRO: release-server.toml não aponta para uma RC do Server 16.1 (atual: $VERSION)." >&2
  exit 1
}
RELEASE_NOTES="$REPO_ROOT/docs/releases/lyra-os-server-$VERSION.md"
[ -s "$RELEASE_NOTES" ] || {
  echo "ERRO: notas de release ausentes: $RELEASE_NOTES" >&2
  exit 1
}

if [ "$ARTIFACTS_ONLY" -eq 0 ]; then
  case "${LYRA_PRIVILEGE_TOOL:-sudo}" in
    sudo) sudo -v ;;
    pkexec) command -v pkexec >/dev/null || {
      echo "ERRO: pkexec não está disponível." >&2
      exit 1
    } ;;
    *) echo "ERRO: LYRA_PRIVILEGE_TOOL deve ser sudo ou pkexec." >&2; exit 1 ;;
  esac
  ./kiwi/test/build-and-run-vm.sh --build-only
fi

ISO="$ARTIFACT_DIR/$ISO_NAME"
PREFIX="${ISO_NAME%.iso}"
BUILD_MANIFEST="$ISO.manifest.json"
for file in "$ISO" "$BUILD_MANIFEST" "$BUILD_DIR/$PREFIX.packages" "$BUILD_DIR/$PREFIX.verified"; do
  [ -s "$file" ] || { echo "ERRO: artefato ausente: $file" >&2; exit 1; }
done

COMMIT="$(python3 - "$BUILD_MANIFEST" "$VERSION" <<'PY'
import json, pathlib, re, sys
d = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
c = d.get("source", {}).get("commit", "")
if d.get("version") != sys.argv[2] or d.get("source", {}).get("dirty") is not False:
    raise SystemExit(f"ERRO: manifesto não representa a {sys.argv[2]} de árvore limpa")
if not re.fullmatch(r"[0-9a-f]{40}", c):
    raise SystemExit("ERRO: commit inválido")
print(c)
PY
)"
git cat-file -e "$COMMIT^{commit}"
[ "$(git rev-parse HEAD)" = "$COMMIT" ] || {
  echo "ERRO: a ISO não foi construída do HEAD atual." >&2
  exit 1
}
[ -z "$(git status --porcelain --untracked-files=normal)" ] || {
  echo "ERRO: o bundle final exige uma árvore de código limpa." >&2
  exit 1
}
install -m 0644 "$BUILD_DIR/$PREFIX.packages" "$ARTIFACT_DIR/$PREFIX.packages"
install -m 0644 "$BUILD_DIR/$PREFIX.verified" "$ARTIFACT_DIR/$PREFIX.verified"
./scripts/release-artifacts.py generate --iso "$ISO" \
  --packages "$ARTIFACT_DIR/$PREFIX.packages" \
  --verified "$ARTIFACT_DIR/$PREFIX.verified" --output-dir "$ARTIFACT_DIR" \
  --commit "$COMMIT" --release-file release-server.toml --product "Lyra OS Server"
install -m 0644 "$RELEASE_NOTES" "$ARTIFACT_DIR/README.md"

gpg --batch --local-user "$RELEASE_SIGNING_FINGERPRINT" --detach-sign --armor \
  --output "$ARTIFACT_DIR/$PREFIX.iso.sha256.asc" \
  "$ARTIFACT_DIR/$PREFIX.iso.sha256"
verify_release_signature "$ARTIFACT_DIR/$PREFIX.iso.sha256.asc" \
  "$ARTIFACT_DIR/$PREFIX.iso.sha256"
(cd "$ARTIFACT_DIR" && sha256sum -c "$PREFIX.iso.sha256")

echo "Bundle Server $PRODUCT_VERSION RC $ITERATION assinado em: $ARTIFACT_DIR"
