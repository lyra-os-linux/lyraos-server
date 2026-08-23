#!/bin/bash
# KIWI calls this hook outside the chroot, from the final image root, after it
# has generated the live ISO bootloader configuration and before packing the
# squashfs. Its first argument names the ISO media tree; the second is the boot
# partition id. The live /boot layout remains untouched here.

set -euo pipefail

case "${1:-}" in
  iso:*) ;;
  *) echo "Unexpected KIWI boot filesystem: ${1:-missing}" >&2; exit 1 ;;
esac
if [ "${2:-}" != "1" ]; then
  echo "Unexpected KIWI boot partition id: ${2:-missing}" >&2
  exit 1
fi

GRUB_DEFAULTS=etc/default/grub
GRUB_THEME_ASSET=usr/share/grub/themes/Lyra-OS/theme.txt
if [ ! -f "$GRUB_DEFAULTS" ]; then
  echo "Missing GRUB defaults: /$GRUB_DEFAULTS" >&2
  exit 1
fi

# lyra-os-theme (and its GRUB_THEME asset) is desktop-only
# (docs/server-edition.md) - the server profile has no theme package
# installed, so this hook is a no-op for it instead of a hard requirement.
# Presence of the asset, not $kiwi_profiles (unavailable to this
# non-chrooted hook), is what actually distinguishes the two here.
if [ -s "$GRUB_THEME_ASSET" ]; then
  # KIWI's live bootloader writer uses /boot/grub2/themes for the ISO menu
  # and can overwrite the value previously written by the theme RPM/config.sh.
  # The rootfs copied to the installed disk instead owns the theme below
  # /usr/share.
  sed -i '/^[[:space:]]*GRUB_THEME=/d' "$GRUB_DEFAULTS"
  cat >> "$GRUB_DEFAULTS" <<'EOF'

# Lyra installed-system theme; the live ISO has its own /boot layout.
GRUB_THEME="/usr/share/grub/themes/Lyra-OS/theme.txt"
EOF

  grep -Fx 'GRUB_THEME="/usr/share/grub/themes/Lyra-OS/theme.txt"' \
    "$GRUB_DEFAULTS" >/dev/null
fi
