#!/usr/bin/env bash
# Validate and publish the signed Server Beta 1 bundle to SourceForge.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
ARTIFACT_DIR="$REPO_ROOT/kiwi/.kiwi/test-$(id -u)-server/iso"
REMOTE="rodrigobritosoa@frs.sourceforge.net:/home/frs/project/lyra/releases/1.0/server/beta1/"
DOWNLOAD_URL="https://downloads.sourceforge.net/project/lyra/releases/1.0/server/beta1"
CHECK_ONLY=0
[ "${1:-}" != --check-only ] || CHECK_ONLY=1
[ "$#" -le 1 ] || { echo "Uso: $0 [--check-only]" >&2; exit 2; }

cd "$REPO_ROOT"
VERSION="$(./scripts/server-release.py field version_id)"
ISO_NAME="$(./scripts/server-release.py field iso_filename)"
[ "$VERSION" = 2026.08-beta1 ] || { echo "ERRO: versão não é Beta 1" >&2; exit 1; }
PREFIX="${ISO_NAME%.iso}"
FILES=(README.md "$PREFIX.cdx.json" "$PREFIX.evidence.json" "$PREFIX.iso"
  "$PREFIX.iso.manifest.json" "$PREFIX.iso.sha256" "$PREFIX.iso.sha256.asc"
  "$PREFIX.packages" "$PREFIX.report" "$PREFIX.spdx.json" "$PREFIX.verified")
for file in "${FILES[@]}"; do
  [ -s "$ARTIFACT_DIR/$file" ] || { echo "ERRO: artefato ausente: $file" >&2; exit 1; }
done

cd "$ARTIFACT_DIR"
sha256sum -c "$PREFIX.iso.sha256"
gpg --verify "$PREFIX.iso.sha256.asc" "$PREFIX.iso.sha256"
python3 - "$PREFIX.evidence.json" <<'PY'
import json, pathlib, sys
d = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
required = {"obs-repositories", "live-session", "installer", "first-boot", "uefi-secure-boot", "hardware-matrix"}
if d.get("source", {}).get("dirty") is not False or set(d.get("test_results", {})) != required:
    raise SystemExit("ERRO: manifesto final incompleto ou originado de árvore suja")
if any(v.get("status") != "passed" for v in d["test_results"].values()):
    raise SystemExit("ERRO: há evidência obrigatória não aprovada")
PY

if [ "$CHECK_ONLY" -eq 1 ]; then
  echo "Bundle válido; nenhum arquivo foi enviado."
  exit 0
fi

KNOWN_HOSTS="$REPO_ROOT/kiwi/.kiwi/sourceforge-known-hosts"
mkdir -p "$(dirname "$KNOWN_HOSTS")"
printf '%s\n' 'frs.sourceforge.net ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOQD35Ujalhh+JJkPvMckDlhu4dS7WH6NsOJ15iGCJLC' >"$KNOWN_HOSTS"
chmod 0600 "$KNOWN_HOSTS"
rsync -avP --partial -e "ssh -o UserKnownHostsFile=$KNOWN_HOSTS -o StrictHostKeyChecking=yes" "${FILES[@]}" "$REMOTE"

DOWNLOAD_DIR="$(mktemp -d /tmp/lyra-server-beta1-download.XXXXXX)"
trap 'rm -rf -- "$DOWNLOAD_DIR"' EXIT
curl --fail --location --retry 5 --output "$DOWNLOAD_DIR/$PREFIX.iso.sha256" "$DOWNLOAD_URL/$PREFIX.iso.sha256"
curl --fail --location --retry 5 --output "$DOWNLOAD_DIR/$PREFIX.iso.sha256.asc" "$DOWNLOAD_URL/$PREFIX.iso.sha256.asc"
curl --fail --location --retry 5 --output "$DOWNLOAD_DIR/$PREFIX.iso" "$DOWNLOAD_URL/$PREFIX.iso"
(cd "$DOWNLOAD_DIR" && sha256sum -c "$PREFIX.iso.sha256")
gpg --verify "$DOWNLOAD_DIR/$PREFIX.iso.sha256.asc" "$DOWNLOAD_DIR/$PREFIX.iso.sha256"
echo "Publicação Beta 1 verificada após download."
