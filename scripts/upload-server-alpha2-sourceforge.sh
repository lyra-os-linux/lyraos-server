#!/usr/bin/env bash
# Upload the verified Lyra OS Server Alpha 2 artifacts to SourceForge FRS.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
ARTIFACT_DIR="$REPO_ROOT/kiwi/.kiwi/test-$(id -u)-server/iso"
REMOTE="rodrigobritosoa@frs.sourceforge.net:/home/frs/project/lyra/releases/1.0/server/alpha2/"
KNOWN_HOSTS="$REPO_ROOT/kiwi/.kiwi/sourceforge-known-hosts"
PREFIX="lyra-os-server.x86_64-2026.08-alpha2"

FILES=(
  README.md
  "$PREFIX.cdx.json"
  "$PREFIX.iso"
  "$PREFIX.iso.manifest.json"
  "$PREFIX.iso.sha256"
  "$PREFIX.packages"
  "$PREFIX.report"
  "$PREFIX.spdx.json"
  "$PREFIX.verified"
)

mkdir -p "$(dirname "$KNOWN_HOSTS")"
printf '%s\n' \
  'frs.sourceforge.net ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOQD35Ujalhh+JJkPvMckDlhu4dS7WH6NsOJ15iGCJLC' \
  >"$KNOWN_HOSTS"
chmod 0600 "$KNOWN_HOSTS"

cd "$ARTIFACT_DIR"
for file in "${FILES[@]}"; do
  if [ ! -f "$file" ]; then
    echo "ERRO: artefato ausente: $ARTIFACT_DIR/$file" >&2
    exit 1
  fi
done

sha256sum -c "$PREFIX.iso.sha256"

echo "Destino: $REMOTE"
echo "O rsync solicitará a senha ou passphrase SSH da conta SourceForge."

rsync -avP \
  -e "ssh -o UserKnownHostsFile=$KNOWN_HOSTS -o StrictHostKeyChecking=yes" \
  "${FILES[@]}" \
  "$REMOTE"

echo "Upload concluído. Confira em:"
echo "https://sourceforge.net/projects/lyra/files/releases/1.0/server/alpha2/"
