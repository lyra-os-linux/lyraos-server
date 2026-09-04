#!/usr/bin/env bash
# Validate and publish the signed Server 1.1 Beta 1.1 bundle to SourceForge.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
ARTIFACT_DIR="${LYRA_TEST_WORK_DIR:-/var/tmp/lyraos-server-test-$(id -u)}/iso"
REMOTE="rodrigobritosoa@frs.sourceforge.net:/home/frs/project/lyra/releases/1.1/beta1.1/server/"
DOWNLOAD_URL="https://downloads.sourceforge.net/project/lyra/releases/1.1/beta1.1/server"
CHECK_ONLY=0
RELEASE_SIGNING_FINGERPRINT="01B63EEDBE6B079126A0116EFA7353A131ECEFEB"
GITHUB_REPOSITORY="lyra-os-linux/lyraos-server"
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
  echo "Uso: $0 [--check-only]" >&2
}
while [ "$#" -gt 0 ]; do
  case "$1" in
    --check-only) CHECK_ONLY=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "ERRO: opção desconhecida: $1" >&2; usage; exit 2 ;;
  esac
  shift
done
cd "$REPO_ROOT"
VERSION="$(./scripts/server-release.py field version_id)"
ISO_NAME="$(./scripts/server-release.py field iso_filename)"
[ "$VERSION" = 1.1-beta.1.1 ] || { echo "ERRO: versão não é Server 1.1 Beta 1.1" >&2; exit 1; }
PREFIX="${ISO_NAME%.iso}"
FILES=(README.md "$PREFIX.cdx.json" "$PREFIX.iso"
  "$PREFIX.iso.manifest.json" "$PREFIX.iso.sha256" "$PREFIX.iso.sha256.asc"
  "$PREFIX.packages" "$PREFIX.report" "$PREFIX.spdx.json" "$PREFIX.verified")
for file in "${FILES[@]}"; do
  [ -s "$ARTIFACT_DIR/$file" ] || { echo "ERRO: artefato ausente: $file" >&2; exit 1; }
done

cd "$ARTIFACT_DIR"
sha256sum -c "$PREFIX.iso.sha256"
verify_release_signature "$PREFIX.iso.sha256.asc" "$PREFIX.iso.sha256"

# GitHub is authoritative. Failure to query it also blocks publication because
# an unknown blocker state must never be treated as GO.
OPEN_BLOCKERS="$(GH_REPO="$GITHUB_REPOSITORY" gh issue list --state open --label server --limit 200 \
  --json number,title --jq '.[] | select(.title | test("\\[P[01]\\]"; "i")) | "#\\(.number) \\(.title)"')"
[ -z "$OPEN_BLOCKERS" ] || {
  echo "ERRO: há P0/P1 Server aberta; publicação bloqueada:" >&2
  echo "$OPEN_BLOCKERS" >&2
  exit 1
}

if [ "$CHECK_ONLY" -eq 1 ]; then
  echo "Bundle válido; nenhum arquivo foi enviado."
  exit 0
fi

KNOWN_HOSTS="$REPO_ROOT/kiwi/.kiwi/sourceforge-known-hosts"
mkdir -p "$(dirname "$KNOWN_HOSTS")"
printf '%s\n' 'frs.sourceforge.net ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOQD35Ujalhh+JJkPvMckDlhu4dS7WH6NsOJ15iGCJLC' >"$KNOWN_HOSTS"
chmod 0600 "$KNOWN_HOSTS"
rsync -avP --partial -e "ssh -o UserKnownHostsFile=$KNOWN_HOSTS -o StrictHostKeyChecking=yes" "${FILES[@]}" "$REMOTE"

DOWNLOAD_DIR="$(mktemp -d /tmp/lyra-server-beta1-1-download.XXXXXX)"
trap 'rm -rf -- "$DOWNLOAD_DIR"' EXIT
curl --fail --location --retry 5 --output "$DOWNLOAD_DIR/$PREFIX.iso.sha256" "$DOWNLOAD_URL/$PREFIX.iso.sha256"
curl --fail --location --retry 5 --output "$DOWNLOAD_DIR/$PREFIX.iso.sha256.asc" "$DOWNLOAD_URL/$PREFIX.iso.sha256.asc"
curl --fail --location --retry 5 --output "$DOWNLOAD_DIR/$PREFIX.iso" "$DOWNLOAD_URL/$PREFIX.iso"
(cd "$DOWNLOAD_DIR" && sha256sum -c "$PREFIX.iso.sha256")
verify_release_signature "$DOWNLOAD_DIR/$PREFIX.iso.sha256.asc" \
  "$DOWNLOAD_DIR/$PREFIX.iso.sha256"
echo "Publicação Server 1.1 Beta 1.1 verificada após download."
