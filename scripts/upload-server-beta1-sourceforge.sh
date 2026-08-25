#!/usr/bin/env bash
# Validate and publish the signed Server Beta 1 bundle to SourceForge.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
ARTIFACT_DIR="${LYRA_TEST_WORK_DIR:-/var/tmp/lyraos-server-test-$(id -u)}/iso"
REMOTE="rodrigobritosoa@frs.sourceforge.net:/home/frs/project/lyra/releases/27.02/server/beta1/"
DOWNLOAD_URL="https://downloads.sourceforge.net/project/lyra/releases/27.02/server/beta1"
CHECK_ONLY=0
DECISION_FILE=""
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
  echo "Uso: $0 [--check-only] --decision-file ARQUIVO.json" >&2
}
while [ "$#" -gt 0 ]; do
  case "$1" in
    --check-only) CHECK_ONLY=1 ;;
    --decision-file) shift; DECISION_FILE="${1:-}" ;;
    -h|--help) usage; exit 0 ;;
    *) echo "ERRO: opção desconhecida: $1" >&2; usage; exit 2 ;;
  esac
  shift
done
[ -n "$DECISION_FILE" ] || { echo "ERRO: registro formal de GO ausente." >&2; usage; exit 2; }
DECISION_FILE="$(readlink -f "$DECISION_FILE")"
[ -s "$DECISION_FILE" ] || { echo "ERRO: registro de GO ausente: $DECISION_FILE" >&2; exit 1; }

cd "$REPO_ROOT"
VERSION="$(./scripts/server-release.py field version_id)"
ISO_NAME="$(./scripts/server-release.py field iso_filename)"
[ "$VERSION" = 27.02-beta1 ] || { echo "ERRO: versão não é Beta 1" >&2; exit 1; }
PREFIX="${ISO_NAME%.iso}"
FILES=(README.md "$PREFIX.cdx.json" "$PREFIX.evidence.json" "$PREFIX.iso"
  "$PREFIX.iso.manifest.json" "$PREFIX.iso.sha256" "$PREFIX.iso.sha256.asc"
  "$PREFIX.packages" "$PREFIX.report" "$PREFIX.spdx.json" "$PREFIX.verified")
for file in "${FILES[@]}"; do
  [ -s "$ARTIFACT_DIR/$file" ] || { echo "ERRO: artefato ausente: $file" >&2; exit 1; }
done

cd "$ARTIFACT_DIR"
sha256sum -c "$PREFIX.iso.sha256"
verify_release_signature "$PREFIX.iso.sha256.asc" "$PREFIX.iso.sha256"
python3 - "$PREFIX.evidence.json" "$DECISION_FILE" "$PREFIX" <<'PY'
import datetime, json, pathlib, re, sys
d = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
decision = json.loads(pathlib.Path(sys.argv[2]).read_text(encoding="utf-8"))
prefix = sys.argv[3]
required = {"obs-repositories", "live-session", "installer", "first-boot", "uefi-secure-boot", "hardware-matrix"}
if d.get("source", {}).get("dirty") is not False or set(d.get("test_results", {})) != required:
    raise SystemExit("ERRO: manifesto final incompleto ou originado de árvore suja")
if any(v.get("status") != "passed" for v in d["test_results"].values()):
    raise SystemExit("ERRO: há evidência obrigatória não aprovada")
iso = d.get("artifacts", {}).get("iso", {})
expected = {
    "decision": "GO",
    "source_commit": d.get("source", {}).get("commit"),
    "iso_filename": iso.get("filename"),
    "iso_sha256": iso.get("sha256"),
    "evidence_manifest": f"{prefix}.evidence.json",
}
if decision.get("schema") != 1 or any(decision.get(k) != v for k, v in expected.items()):
    raise SystemExit("ERRO: registro de GO não corresponde exatamente ao candidato")
if not isinstance(decision.get("coordinator"), str) or not decision["coordinator"].strip():
    raise SystemExit("ERRO: registro de GO sem coordenador")
if not re.fullmatch(r"[0-9a-f]{40}", decision["source_commit"] or ""):
    raise SystemExit("ERRO: commit inválido no registro de GO")
if not re.fullmatch(r"[0-9a-f]{64}", decision["iso_sha256"] or ""):
    raise SystemExit("ERRO: SHA-256 inválido no registro de GO")
try:
    decided_at = datetime.datetime.fromisoformat(decision.get("decided_at_utc", "").replace("Z", "+00:00"))
except ValueError as error:
    raise SystemExit("ERRO: horário UTC inválido no registro de GO") from error
if decided_at.utcoffset() != datetime.timedelta(0):
    raise SystemExit("ERRO: decisão deve registrar horário UTC")
for field in ("accepted_p2_p3", "residual_risks"):
    if not isinstance(decision.get(field), list) or not all(isinstance(v, str) for v in decision[field]):
        raise SystemExit(f"ERRO: registro de GO sem lista válida: {field}")
PY

# GitHub is authoritative. Failure to query it also blocks publication because
# an unknown blocker state must never be treated as GO.
OPEN_BLOCKERS="$(gh issue list --state open --label server --limit 200 \
  --json number,title --jq '.[] | select(.title | test("\\[P[01]\\]"; "i")) | "#\\(.number) \\(.title)"')"
[ -z "$OPEN_BLOCKERS" ] || {
  echo "ERRO: há P0/P1 Server aberta; publicação bloqueada:" >&2
  echo "$OPEN_BLOCKERS" >&2
  exit 1
}

install -m 0644 "$DECISION_FILE" "$ARTIFACT_DIR/$PREFIX.release-decision.json"
FILES+=("$PREFIX.release-decision.json")

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
verify_release_signature "$DOWNLOAD_DIR/$PREFIX.iso.sha256.asc" \
  "$DOWNLOAD_DIR/$PREFIX.iso.sha256"
echo "Publicação Beta 1 verificada após download."
