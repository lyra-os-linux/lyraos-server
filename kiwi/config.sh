#!/bin/bash
#
# Lyra OS Server
# KIWI config.sh: runs chrooted into the image after packages are
# installed. See kiwi/config.xml's top comment and docs/server-edition.md
# for what this image is.

set -euo pipefail

test -f /.kconfig && . /.kconfig
test -f /.profile && . /.profile

echo "Configuring image: [$kiwi_iname]..."

RELEASE_METADATA=/usr/lib/lyra-os/server-release
if [ ! -r "$RELEASE_METADATA" ]; then
    echo "Missing generated release metadata: $RELEASE_METADATA" >&2
    exit 1
fi
# shellcheck source=/dev/null
. "$RELEASE_METADATA"

if [ "$kiwi_iversion" != "$LYRA_ARTIFACT_VERSION" ]; then
    echo "KIWI version $kiwi_iversion does not match $LYRA_ARTIFACT_VERSION" >&2
    exit 1
fi

BUILD_SOURCE_METADATA=/usr/lib/lyra-os/build-source
if [ -r "$BUILD_SOURCE_METADATA" ]; then
    # OBS receives this generated file with the exported KIWI description.
    # Local builds keep using the environment fallbacks below.
    # shellcheck source=/dev/null
    . "$BUILD_SOURCE_METADATA"
fi

LYRA_BUILD_SOURCE_COMMIT="${LYRA_BUILD_SOURCE_COMMIT:-unknown}"
LYRA_BUILD_SOURCE_EPOCH="${LYRA_BUILD_SOURCE_EPOCH:-unknown}"
LYRA_IMAGE_BUILT_AT="${LYRA_IMAGE_BUILT_AT:-unknown}"
LYRA_BUILD_SOURCE_DIRTY="${LYRA_BUILD_SOURCE_DIRTY:-unknown}"
if ! [[ "$LYRA_BUILD_SOURCE_COMMIT" =~ ^[0-9a-f]{40}$ ]]; then
    LYRA_BUILD_SOURCE_COMMIT=unknown
fi
if [[ "$LYRA_BUILD_SOURCE_EPOCH" =~ ^[0-9]+$ ]]; then
    LYRA_BUILD_ID="$(date -u -d "@$LYRA_BUILD_SOURCE_EPOCH" +%Y%m%d)"
else
    LYRA_BUILD_ID="$(date -u +%Y%m%d)"
fi
if [[ "$LYRA_BUILD_SOURCE_DIRTY" != 0 && "$LYRA_BUILD_SOURCE_DIRTY" != 1 ]]; then
    LYRA_BUILD_SOURCE_DIRTY=unknown
fi
if ! [[ "$LYRA_BUILD_SOURCE_EPOCH" =~ ^[0-9]+$ ]]; then
    LYRA_BUILD_SOURCE_EPOCH=unknown
fi
cat > /usr/lib/lyra-os/build-info <<EOF
# Generated during the KIWI build; do not edit.
LYRA_SOURCE_COMMIT="$LYRA_BUILD_SOURCE_COMMIT"
LYRA_SOURCE_DIRTY="$LYRA_BUILD_SOURCE_DIRTY"
LYRA_SOURCE_EPOCH="$LYRA_BUILD_SOURCE_EPOCH"
LYRA_IMAGE_BUILT_AT="$LYRA_IMAGE_BUILT_AT"
EOF

# Leap's filesystem package does not own /etc/mtab, and a KIWI-built root can
# therefore leave the path absent. Point it at the kernel's live mount
# table, as on a normally installed system. The relative target keeps the
# link valid both in the live image and in the installer's target root.
ln -sfn ../proc/self/mounts /etc/mtab

# Networking / firewall - Leap defaults, enabled explicitly for the live boot
suseInsertService NetworkManager
suseInsertService firewalld

# No GDM/graphical session on this image. The console opens via a systemd
# getty autologin as root instead (overlaid by
# kiwi/server/etc/systemd/system/getty@tty1.service.d/ - a static drop-in
# needs no service-enable step here), which then runs
# scripts/server-install.sh (pinned as
# kiwi/server/usr/sbin/lyra-server-install) from root's .bash_profile. Both
# the getty override and the installer script are live-only and get
# stripped by the installer itself once a disk is in place - see
# scripts/server-install.sh's "strip live-only artifacts" step.

# zram-generator activates its own systemd generator at boot from
# /etc/systemd/zram-generator.conf - no service to enable here.

# Product identity: "Lyra OS Server", not an alternate name - everything
# user-visible follows this convention, matching the desktop product's
# "Lyra OS" naming discipline. ID_LIKE keeps openSUSE/SUSE tooling that
# branches on it (package managers, some installers) working correctly.
# Overwrites whatever openSUSE-release just installed.
#
# VERSION_CODENAME belongs to the shared Lyra OS generation. ID remains
# distinct from the desktop's "lyra-os" so
# tooling branching on os-release can tell the two products apart, matching
# IMAGE_ID already being "lyra-os-server" here (LYRA_IMAGE_NAME, from
# release-server.toml).
#
# Deliberately no HOME_URL/BUG_REPORT_URL/LOGO here: there's no confirmed
# project website, issue tracker, or a matching icon name to point them at -
# adding guessed URLs/icon names felt worse than leaving these optional
# fields out.
cat > /etc/os-release <<EOF
NAME="Lyra OS Server"
PRETTY_NAME="$LYRA_PRETTY_NAME"
ID=lyra-os-server
ID_LIKE="opensuse suse"
VERSION="$LYRA_VERSION_NAME"
VERSION_ID="$LYRA_VERSION_ID"
VERSION_CODENAME="$LYRA_CODENAME_ID"
BUILD_ID="$LYRA_BUILD_ID"
IMAGE_ID="$LYRA_IMAGE_NAME"
IMAGE_VERSION="$LYRA_ARTIFACT_VERSION"
CPE_NAME="cpe:/o:rodrigosbrito:lyra_os_server:$LYRA_VERSION_ID"
EOF

exit 0
