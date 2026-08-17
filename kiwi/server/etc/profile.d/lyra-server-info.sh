# shellcheck shell=bash disable=SC2317
# Lyra OS Server: show IP/CPU/disk/memory on every interactive login
# (console or SSH), since there is no desktop/GNOME session to surface
# this otherwise. /etc/profile.d/*.sh already only runs for login shells,
# so this does not need its own guard for that. Harmless if it also runs
# during the pre-install live session.

case $- in
    *i*) ;;
    *) return 0 2>/dev/null || exit 0 ;;
esac

# Follow the locale selected during installation. The live image defaults to
# en_US, so its pre-installer login never falls back to fixed Portuguese.
_lyra_server_locale=${LC_ALL:-${LC_MESSAGES:-${LANG:-en_US}}}
case "$_lyra_server_locale" in
    pt_BR*)
        _lyra_server_no_ip="sem endereço IPv4"
        _lyra_server_unknown="desconhecida"
        _lyra_server_unavailable="indisponível"
        _lyra_server_cores_label="núcleos"
        _lyra_server_memory_label="Memória"
        _lyra_server_disk_label="Disco"
        _lyra_server_used_label="usados"
        _lyra_server_total_label="total"
        ;;
    *)
        _lyra_server_no_ip="no IPv4 address"
        _lyra_server_unknown="unknown"
        _lyra_server_unavailable="unavailable"
        _lyra_server_cores_label="cores"
        _lyra_server_memory_label="Memory"
        _lyra_server_disk_label="Disk"
        _lyra_server_used_label="used"
        _lyra_server_total_label="total"
        ;;
esac

_lyra_server_ips=$(ip -4 -o addr show scope global 2>/dev/null | awk '{print $2": "$4}' | paste -sd', ' -)
_lyra_server_cpu=$(grep -m1 '^model name' /proc/cpuinfo 2>/dev/null | cut -d: -f2 | sed 's/^ *//')
_lyra_server_cores=$(nproc 2>/dev/null)
_lyra_server_mem=$(free -h 2>/dev/null | awk -v used="$_lyra_server_used_label" -v total="$_lyra_server_total_label" '/^Mem:/ {print $3" "used" / "$2" "total}')
_lyra_server_disk=$(df -h / 2>/dev/null | awk -v used="$_lyra_server_used_label" -v total="$_lyra_server_total_label" 'NR==2 {print $3" "used" / "$2" "total" ("$5")"}')

echo
echo "== $(uname -n) =="
echo "IP:       ${_lyra_server_ips:-$_lyra_server_no_ip}"
echo "CPU:      ${_lyra_server_cpu:-$_lyra_server_unknown} (${_lyra_server_cores:-?} $_lyra_server_cores_label)"
echo "$_lyra_server_memory_label:  ${_lyra_server_mem:-$_lyra_server_unavailable}"
echo "$_lyra_server_disk_label (/): ${_lyra_server_disk:-$_lyra_server_unavailable}"
echo

unset _lyra_server_locale _lyra_server_no_ip _lyra_server_unknown
unset _lyra_server_unavailable _lyra_server_cores_label
unset _lyra_server_memory_label _lyra_server_disk_label
unset _lyra_server_used_label _lyra_server_total_label
unset _lyra_server_ips _lyra_server_cpu _lyra_server_cores
unset _lyra_server_mem _lyra_server_disk
