# Lyra OS Server: show IP/CPU/disk/memory on every interactive login
# (console or SSH), since there is no desktop/GNOME session to surface
# this otherwise. /etc/profile.d/*.sh already only runs for login shells,
# so this does not need its own guard for that. Harmless if it also runs
# during the pre-install live session.

case $- in
    *i*) ;;
    *) return 0 2>/dev/null || exit 0 ;;
esac

_lyra_server_ips=$(ip -4 -o addr show scope global 2>/dev/null | awk '{print $2": "$4}' | paste -sd', ' -)
_lyra_server_cpu=$(grep -m1 '^model name' /proc/cpuinfo 2>/dev/null | cut -d: -f2 | sed 's/^ *//')
_lyra_server_cores=$(nproc 2>/dev/null)
_lyra_server_mem=$(free -h 2>/dev/null | awk '/^Mem:/ {print $3" usados / "$2" total"}')
_lyra_server_disk=$(df -h / 2>/dev/null | awk 'NR==2 {print $3" usados / "$2" total ("$5")"}')

echo
echo "== $(hostname) =="
echo "IP:       ${_lyra_server_ips:-sem endereço IPv4}"
echo "CPU:      ${_lyra_server_cpu:-desconhecida} (${_lyra_server_cores:-?} núcleos)"
echo "Memória:  ${_lyra_server_mem:-indisponível}"
echo "Disco (/): ${_lyra_server_disk:-indisponível}"
echo

unset _lyra_server_ips _lyra_server_cpu _lyra_server_cores _lyra_server_mem _lyra_server_disk
