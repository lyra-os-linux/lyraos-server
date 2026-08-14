#!/usr/bin/env bash
# Validate and publish Lyra OS Server Alpha 2 artifacts to SourceForge FRS.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
ARTIFACT_DIR="$REPO_ROOT/kiwi/.kiwi/test-$(id -u)-server/iso"
EXPECTED_VERSION="2026.08-alpha2"
REMOTE_USER="rodrigobritosoa"
REMOTE_HOST="frs.sourceforge.net"
REMOTE_DIR="/home/frs/project/lyra/releases/1.0/server/alpha2/"
REMOTE="$REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR"
PUBLIC_URL="https://sourceforge.net/projects/lyra/files/releases/1.0/server/alpha2/"
DOWNLOAD_URL="https://downloads.sourceforge.net/project/lyra/releases/1.0/server/alpha2"
KNOWN_HOSTS="$REPO_ROOT/kiwi/.kiwi/sourceforge-known-hosts"
CHECK_ONLY=0
VERIFY_DOWNLOAD=0

usage() {
  cat <<EOF
Uso: ./scripts/upload-server-alpha2-sourceforge.sh [opções]

Opções:
  --check-only       valida tudo sem enviar arquivos
  --verify-download  após o upload, baixa novamente a ISO e verifica o SHA-256
  -h, --help         mostra esta ajuda

Destino fixo:
  $REMOTE
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --check-only) CHECK_ONLY=1 ;;
    --verify-download) VERIFY_DOWNLOAD=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "ERRO: opção desconhecida: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

if [ "$CHECK_ONLY" -eq 1 ] && [ "$VERIFY_DOWNLOAD" -eq 1 ]; then
  echo "ERRO: --verify-download não pode ser usado com --check-only." >&2
  exit 2
fi

for command in git python3 rsync sha256sum ssh; do
  command -v "$command" >/dev/null 2>&1 || {
    echo "ERRO: comando obrigatório ausente: $command" >&2
    exit 1
  }
done
if [ "$VERIFY_DOWNLOAD" -eq 1 ]; then
  command -v curl >/dev/null 2>&1 || {
    echo "ERRO: curl é obrigatório para --verify-download." >&2
    exit 1
  }
fi

cd "$REPO_ROOT"
VERSION="$(./scripts/server-release.py field version_id)"
ISO_NAME="$(./scripts/server-release.py field iso_filename)"
PREFIX="${ISO_NAME%.iso}"
if [ "$VERSION" != "$EXPECTED_VERSION" ]; then
  echo "ERRO: release-server.toml não aponta para $EXPECTED_VERSION." >&2
  exit 1
fi

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

cd "$ARTIFACT_DIR"
for file in "${FILES[@]}"; do
  if [ ! -s "$file" ]; then
    echo "ERRO: artefato ausente ou vazio: $ARTIFACT_DIR/$file" >&2
    exit 1
  fi
done

echo "Validando checksum da ISO..."
sha256sum -c "$PREFIX.iso.sha256"

DOWNLOAD_DIR=""
cleanup() {
  if [ -n "$DOWNLOAD_DIR" ]; then
    case "$DOWNLOAD_DIR" in
      /tmp/lyra-server-alpha2-download.*) rm -rf -- "$DOWNLOAD_DIR" ;;
      *) echo "ERRO: diretório de download inesperado: $DOWNLOAD_DIR" >&2 ;;
    esac
  fi
}
trap cleanup EXIT

echo "AVISO: Server Alpha 2 é publicada somente com SHA-256, sem assinatura GPG da ISO."
echo "A assinatura de artefatos começa na Beta 1 (ADR 0005)."

echo "Validando identidade e consistência dos metadados..."
python3 - "$PREFIX.iso.manifest.json" "$PREFIX.report" "$PREFIX.iso.sha256" <<'PY'
import hashlib
import json
import pathlib
import re
import subprocess
import sys

manifest_path, report_path, checksum_path = map(pathlib.Path, sys.argv[1:])
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
report = json.loads(report_path.read_text(encoding="utf-8"))
checksum_line = checksum_path.read_text(encoding="utf-8").strip()
match = re.fullmatch(r"([0-9a-f]{64})  (.+\.iso)", checksum_line)
if not match:
    raise SystemExit("ERRO: formato inválido no arquivo SHA-256")
checksum, filename = match.groups()
source = manifest.get("source", {})
commit = source.get("commit", "")
if source.get("dirty") is not False:
    raise SystemExit("ERRO: manifesto registra árvore de origem suja")
if manifest.get("version") != "2026.08-alpha2":
    raise SystemExit("ERRO: versão inesperada no manifesto")
if report.get("version") != manifest.get("version"):
    raise SystemExit("ERRO: versão diverge entre manifesto e relatório")
if report.get("product") != "Lyra OS Server":
    raise SystemExit("ERRO: produto inesperado no relatório")
if manifest.get("iso", {}).get("filename") != filename:
    raise SystemExit("ERRO: nome da ISO diverge entre manifesto e checksum")
if manifest.get("iso", {}).get("sha256") != checksum:
    raise SystemExit("ERRO: SHA-256 diverge entre manifesto e checksum")
if report.get("source", {}).get("commit") != commit:
    raise SystemExit("ERRO: commit diverge entre manifesto e relatório")
if report.get("iso", {}).get("sha256") != checksum:
    raise SystemExit("ERRO: SHA-256 diverge entre relatório e checksum")
if not re.fullmatch(r"[0-9a-f]{40}", commit):
    raise SystemExit("ERRO: commit inválido no manifesto")
subprocess.run(["git", "cat-file", "-e", f"{commit}^{{commit}}"], check=True)
with open(filename, "rb") as stream:
    actual = hashlib.file_digest(stream, "sha256").hexdigest()
if actual != checksum:
    raise SystemExit("ERRO: conteúdo da ISO diverge do checksum")
print(f"OK: candidato {filename} do commit {commit}")
PY

if [ "$CHECK_ONLY" -eq 1 ]; then
  echo "Validação concluída; nenhum arquivo foi enviado."
  exit 0
fi

mkdir -p "$(dirname "$KNOWN_HOSTS")"
printf '%s\n' \
  'frs.sourceforge.net ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOQD35Ujalhh+JJkPvMckDlhu4dS7WH6NsOJ15iGCJLC' \
  >"$KNOWN_HOSTS"
chmod 0600 "$KNOWN_HOSTS"

echo "Publicando em: $REMOTE"
echo "A senha ou passphrase, se necessária, será solicitada diretamente pelo SSH."
rsync -avP --partial \
  -e "ssh -o UserKnownHostsFile=$KNOWN_HOSTS -o StrictHostKeyChecking=yes" \
  "${FILES[@]}" "$REMOTE"

if [ "$VERIFY_DOWNLOAD" -eq 1 ]; then
  DOWNLOAD_DIR="$(mktemp -d /tmp/lyra-server-alpha2-download.XXXXXX)"
  echo "Baixando novamente ISO e checksum públicos para verificação..."
  curl --fail --location --retry 5 --retry-delay 10 \
    --output "$DOWNLOAD_DIR/$PREFIX.iso.sha256" "$DOWNLOAD_URL/$PREFIX.iso.sha256"
  curl --fail --location --retry 5 --retry-delay 10 \
    --output "$DOWNLOAD_DIR/$PREFIX.iso" "$DOWNLOAD_URL/$PREFIX.iso"
  (cd "$DOWNLOAD_DIR" && sha256sum -c "$PREFIX.iso.sha256")
  echo "Download público verificado com sucesso."
fi

echo "Publicação concluída:"
echo "$PUBLIC_URL"
