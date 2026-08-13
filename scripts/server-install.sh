#!/bin/bash
#
# Lyra OS Server - console installer.
#
# Single disk, ext4 (no RAID/LVM/Btrfs/Snapper in v1), UEFI + Secure Boot
# (shim), DHCP network (no static IP prompt), vegad/vega-cli/vega-web
# enabled on the target, firewalld opens only ssh and vega-web (9090/tcp).
# See docs/server-edition.md for the full architecture and rationale.
#
# This is a standalone shell implementation - it deliberately does not
# reuse lyra-installer-core/service (installer/), the desktop's Rust
# installer engine, even though that engine already separates domain logic
# from its frontend for exactly this kind of reuse. That was a conscious
# trade-off, not an oversight (see "Instalador em console" in
# docs/server-edition.md); this script re-implements the subset of
# partitioning/deploy/bootloader logic it needs on its own, in particular
# the two real bugs the Rust installer's README records having to fix the
# hard way: wiping old partition signatures before repartitioning, and
# using a *recursive* bind mount of /sys so the chroot actually inherits
# the live session's already-mounted efivarfs (a plain non-recursive bind
# does not propagate it, and Secure Boot's NVRAM entry silently ends up
# missing without it).
#
# First-pass status: exercised by shellcheck and read-review only so far,
# not yet against a real disk in a VM. Per docs/server-edition.md's gate,
# treat this as untrusted until it has been run at least once against
# kiwi/test/build-and-run-vm.sh (or equivalent) end to end.

set -euo pipefail

UI_LANGUAGE=en

msg() {
    local key="$1"
    case "$UI_LANGUAGE:$key" in
        pt:error) echo "Erro" ;; pt:interrupted) echo "instalação interrompida" ;; pt:root_required) echo "este instalador precisa rodar como root" ;;
        pt:uefi_required) echo "firmware não está em modo UEFI — esta imagem só suporta boot UEFI" ;; pt:console_installer) echo "instalador de console" ;;
        pt:cancelled) echo "instalação cancelada pelo usuário" ;; pt:password) echo "Senha:" ;; pt:confirm_password) echo "Confirme a senha:" ;;
        pt:password_short) echo "A senha precisa ter pelo menos 8 caracteres." ;; pt:password_mismatch) echo "As senhas não conferem." ;;
        pt:unnamed) echo "sem nome" ;; pt:no_disk) echo "nenhum disco elegível encontrado (a mídia de instalação não conta)" ;;
        pt:target_disk) echo "Disco de destino (TODO o conteúdo será apagado):" ;; pt:invalid_disk) echo "seleção de disco inválida" ;;
        pt:no_keymap) echo "nenhum layout de teclado de console foi encontrado na imagem" ;; pt:keymap) echo "Layout de teclado (console):" ;;
        pt:no_dialog) echo "o pacote 'dialog' não está instalado nesta imagem" ;; pt:timezone) echo "Fuso horário:" ;; pt:hostname) echo "Hostname:" ;;
        pt:invalid_hostname) echo "Hostname inválido (minúsculas, números e hífen, sem começar/terminar em hífen)." ;;
        pt:admin_user) echo "Usuário administrativo:" ;; pt:invalid_user) echo "Usuário inválido (letra minúscula inicial, depois letras/números/-/_)." ;;
        pt:summary) printf '%s\n' 'Idioma:    %s\nTeclado:   %s\nFuso:      %s\nHostname:  %s\nDisco:     %s (TODO o conteúdo será apagado)\nUsuário:   %s (grupo wheel/sudo)\n\nConfirma a instalação? Esta operação é IRREVERSÍVEL.' ;;
        pt:install_cancelled) echo "Instalação cancelada." ;; pt:partitioning) echo "Particionando %s..." ;; pt:formatting) echo "Formatando partições..." ;;
        pt:copying) echo "Copiando o sistema para o disco (pode levar alguns minutos)..." ;; pt:copy_failed) echo "cópia do sistema para o disco falhou (tar retornou %s)" ;;
        pt:mounting) echo "Montando o ambiente do sistema instalado..." ;; pt:configuring) echo "Configurando usuário, bootloader e serviços..." ;;
        pt:finishing) echo "Finalizando..." ;; pt:completed) echo "Concluído." ;; pt:preparing) echo "Preparando instalação..." ;;
        pt:install_complete) echo "Instalação concluída." ;; pt:restart) echo "Instalação concluída. Reiniciar agora?" ;;
        pt:log_path) echo "Log de diagnóstico: %s" ;;

        *:error) echo "Error" ;; *:interrupted) echo "installation interrupted" ;; *:root_required) echo "this installer must run as root" ;;
        *:uefi_required) echo "firmware is not in UEFI mode — this image only supports UEFI boot" ;; *:console_installer) echo "console installer" ;;
        *:cancelled) echo "installation cancelled by the user" ;; *:password) echo "Password:" ;; *:confirm_password) echo "Confirm password:" ;;
        *:password_short) echo "The password must contain at least 8 characters." ;; *:password_mismatch) echo "The passwords do not match." ;;
        *:unnamed) echo "unnamed" ;; *:no_disk) echo "no eligible disk found (the installation media does not count)" ;;
        *:target_disk) echo "Target disk (ALL contents will be erased):" ;; *:invalid_disk) echo "invalid disk selection" ;;
        *:no_keymap) echo "no console keyboard layout was found in the image" ;; *:keymap) echo "Keyboard layout (console):" ;;
        *:no_dialog) echo "the 'dialog' package is not installed in this image" ;; *:timezone) echo "Time zone:" ;; *:hostname) echo "Device name:" ;;
        *:invalid_hostname) echo "Invalid device name (lowercase letters, numbers and hyphens; no leading or trailing hyphen)." ;;
        *:admin_user) echo "Administrator user:" ;; *:invalid_user) echo "Invalid user (start with a lowercase letter, followed by letters, numbers, - or _)." ;;
        *:summary) printf '%s\n' 'Language:   %s\nKeyboard:   %s\nTime zone:  %s\nDevice:     %s\nDisk:       %s (ALL contents will be erased)\nUser:       %s (wheel/sudo group)\n\nConfirm installation? This operation is IRREVERSIBLE.' ;;
        *:install_cancelled) echo "Installation cancelled." ;; *:partitioning) echo "Partitioning %s..." ;; *:formatting) echo "Formatting partitions..." ;;
        *:copying) echo "Copying the system to disk (this may take several minutes)..." ;; *:copy_failed) echo "copying the system to disk failed (tar returned %s)" ;;
        *:mounting) echo "Mounting the installed system environment..." ;; *:configuring) echo "Configuring user, bootloader and services..." ;;
        *:finishing) echo "Finishing..." ;; *:completed) echo "Completed." ;; *:preparing) echo "Preparing installation..." ;;
        *:install_complete) echo "Installation completed." ;; *:restart) echo "Installation completed. Restart now?" ;;
        *:log_path) echo "Diagnostic log: %s" ;;
        *) echo "$key" ;;
    esac
}

msgf() {
    local format
    format="$(msg "$1")"
    shift
    # The format comes only from the fixed catalogs above, never user input.
    # shellcheck disable=SC2059
    printf "$format" "$@"
}

RELEASE_METADATA=/usr/lib/lyra-os/server-release
if [ ! -r "$RELEASE_METADATA" ]; then
    echo "Missing release metadata: $RELEASE_METADATA" >&2
    exit 1
fi
# shellcheck source=/dev/null
. "$RELEASE_METADATA"

TARGET=/mnt/lyra-target
LOG=/root/lyra-server-install.log
: > "$LOG"
CURRENT_STAGE=preflight

log() {
    echo "$(date -u '+%Y-%m-%dT%H:%M:%SZ') $*" >> "$LOG"
}

fail() {
    local message
    message="$(redact_command "$*")"
    echo "$(msg error): $message" >&2
    msgf log_path "$LOG" >&2
    echo >&2
    log "FAIL status=1 stage=$CURRENT_STAGE message=$message"
    exit 1
}

redact_command() {
    local command="$1"
    if [ -n "${PASSWORD_VALUE:-}" ]; then
        command=${command//"$PASSWORD_VALUE"/[REDACTED]}
    fi
    printf '%s' "$command"
}

report_error() {
    local status="$1" line="$2" command="$3" safe_command message
    trap - ERR
    safe_command="$(redact_command "$command")"
    message="$(msg interrupted) (line $line)"
    log "FAIL status=$status stage=$CURRENT_STAGE line=$line command=$safe_command"
    echo "$(msg error): $message" >&2
    msgf log_path "$LOG" >&2
    echo >&2
    exit "$status"
}

report_error_with_cleanup() {
    local status="$1" line="$2" command="$3" cleanup_status
    trap - ERR
    set +e
    cleanup_mounts
    cleanup_status=$?
    set -e
    if [ "$cleanup_status" -ne 0 ]; then
        log "WARN status=$cleanup_status stage=cleanup message=cleanup-after-failure"
    fi
    report_error "$status" "$line" "$command"
}

trap 'report_error $? "$LINENO" "$BASH_COMMAND"' ERR

if [ "$(id -u)" -ne 0 ]; then
    fail "$(msg root_required)"
fi

if [ ! -d /sys/firmware/efi ]; then
    fail "$(msg uefi_required)"
fi

# --- prompts -----------------------------------------------------------
#
# Uses dialog (already required - see the package list comment near
# vega-cli/vegad/vega-web in kiwi/config.xml) for every interactive
# question. Every helper's own locals are double-underscore-prefixed
# (__result, __out, ...) on purpose: a real bug here once (choose_from_menu
# using a plain "choice" local, shadowing a caller that also happened to
# name its variable "choice" - see git history) showed that an unqualified
# name can collide with whatever a caller declares, since bash resolves
# unqualified names to the nearest enclosing *local* scope up the call
# stack. The double-underscore prefix makes a collision with any
# realistic caller variable name effectively impossible.

DIALOG_BACKTITLE="$LYRA_PRETTY_NAME - $(msg console_installer)"

# dialog draws to the terminal (fd 1) and writes the widget's result to fd
# 2 by default; the 3>&1 1>&2 2>&3 3>&- swap is the standard idiom to
# capture just the result via command substitution instead. A Cancel/Esc
# (exit status 1 or 255) aborts the whole installer rather than being
# treated as "try again" - dialog already gives its own Cancel button for
# that, a second layer of retry-on-cancel would be confusing.
dialog_run() {
    local __result
    __result=$(dialog --backtitle "$DIALOG_BACKTITLE" "$@" 3>&1 1>&2 2>&3 3>&-) \
        || fail "$(msg cancelled)"
    printf '%s' "$__result"
}

dialog_yesno() {
    dialog --backtitle "$DIALOG_BACKTITLE" --yesno "$1" "${2:-12}" "${3:-70}"
}

dialog_msgbox() {
    dialog --backtitle "$DIALOG_BACKTITLE" --msgbox "$1" "${2:-8}" "${3:-70}"
}

dialog_menu() {
    # dialog_menu <out_var> <prompt> <opt1> <opt2> ...
    local __out="$1" prompt="$2"
    shift 2
    local __labels=("$@") __menu_args=() __i __result __menu_height
    for __i in "${!__labels[@]}"; do
        __menu_args+=("$((__i + 1))" "${__labels[$__i]}")
    done
    __menu_height=${#__labels[@]}
    if [ "$__menu_height" -gt 14 ]; then
        __menu_height=14
    fi
    __result="$(dialog_run --menu "$prompt" 20 70 "$__menu_height" "${__menu_args[@]}")"
    printf -v "$__out" '%s' "${__labels[$((__result - 1))]}"
}

dialog_inputbox() {
    # dialog_inputbox <out_var> <prompt> <validation_regex> <error_message>
    local __out="$1" prompt="$2" __pattern="$3" __error="$4" __result
    while true; do
        __result="$(dialog_run --inputbox "$prompt" 10 70)"
        if [[ "$__result" =~ $__pattern ]]; then
            printf -v "$__out" '%s' "$__result"
            return 0
        fi
        dialog_msgbox "$__error"
    done
}

dialog_passwordbox() {
    local __out="$1" prompt="$2" __result
    __result="$(dialog_run --insecure --passwordbox "$prompt" 10 70)"
    printf -v "$__out" '%s' "$__result"
}

prompt_password() {
    local __first __second
    while true; do
        dialog_passwordbox __first "$(msg password)"
        if [ ${#__first} -lt 8 ]; then
            dialog_msgbox "$(msg password_short)"
            continue
        fi
        dialog_passwordbox __second "$(msg confirm_password)"
        if [ "$__first" != "$__second" ]; then
            dialog_msgbox "$(msg password_mismatch)"
            continue
        fi
        PASSWORD_VALUE="$__first"
        return 0
    done
}

# lsblk -e 7,11 excludes loop devices (major 7 - the live squashfs) and
# optical drives (major 11). A disk is eligible only if none of its
# partitions are currently mounted, which is what actually distinguishes
# the live boot medium (its partition holding the ISO/squashfs is always
# mounted) from every other disk - including a disk that already has old
# partitions on it, which is fine to offer since this is a destructive
# reinstall by design.
list_eligible_disks() {
    local name size model mounted
    while read -r name size model; do
        mounted=$(lsblk -no MOUNTPOINT "/dev/$name" 2>/dev/null | tr -d ' \n')
        if [ -z "$mounted" ]; then
            printf '%s\t%s\t%s\n' "$name" "$size" "${model:-$(msg unnamed)}"
        fi
    done < <(lsblk -dno NAME,SIZE,MODEL -e 7,11 2>/dev/null)
}

choose_disk() {
    local disks=() labels=() line name size model
    while IFS=$'\t' read -r name size model; do
        disks+=("/dev/$name")
        labels+=("/dev/$name ($size, $model)")
    done < <(list_eligible_disks)
    if [ "${#disks[@]}" -eq 0 ]; then
        fail "$(msg no_disk)"
    fi
    local __picked
    dialog_menu __picked "$(msg target_disk)" "${labels[@]}"
    for line in "${!labels[@]}"; do
        if [ "${labels[$line]}" = "$__picked" ]; then
            DISK="${disks[$line]}"
            return 0
        fi
    done
    fail "$(msg invalid_disk)"
}

choose_keymap() {
    # Console keymaps and desktop XKB layouts use different namespaces.
    # Ask systemd for the complete set shipped by this image so every item
    # offered here is accepted by loadkeys and systemd-vconsole-setup.
    local keymaps=() keymap preferred ordered=()
    mapfile -t keymaps < <(localectl list-keymaps --no-pager 2>/dev/null)
    if [ "${#keymaps[@]}" -eq 0 ]; then
        fail "$(msg no_keymap)"
    fi

    # Keep the two most common Lyra choices at the top; the remaining list
    # stays in localectl's stable alphabetical order.
    for preferred in br us; do
        for keymap in "${keymaps[@]}"; do
            if [ "$keymap" = "$preferred" ]; then
                ordered+=("$keymap")
                break
            fi
        done
    done
    for keymap in "${keymaps[@]}"; do
        if [ "$keymap" != br ] && [ "$keymap" != us ]; then
            ordered+=("$keymap")
        fi
    done
    dialog_menu KEYMAP_VALUE "$(msg keymap)" "${ordered[@]}"
}

if ! command -v dialog >/dev/null 2>&1; then
    fail "$(msg no_dialog)"
fi

dialog_menu LOCALE_VALUE "System language / Idioma do sistema:" \
    "en_US.UTF-8" "pt_BR.UTF-8"
UI_LANGUAGE="${LOCALE_VALUE%%_*}"
DIALOG_BACKTITLE="$LYRA_PRETTY_NAME - $(msg console_installer)"
choose_keymap
dialog_menu TIMEZONE_VALUE "$(msg timezone)" "America/Sao_Paulo" "UTC"
dialog_inputbox HOSTNAME_VALUE "$(msg hostname)" \
    '^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$' \
    "$(msg invalid_hostname)"
choose_disk
dialog_inputbox USERNAME_VALUE "$(msg admin_user)" \
    '^[a-z][a-z0-9_-]{0,31}$' \
    "$(msg invalid_user)"
prompt_password

SUMMARY="$(msgf summary "$LOCALE_VALUE" "$KEYMAP_VALUE" "$TIMEZONE_VALUE" \
    "$HOSTNAME_VALUE" "$DISK" "$USERNAME_VALUE")"
if ! dialog_yesno "$SUMMARY" 16 70; then
    clear
    msg install_cancelled
    exit 1
fi

log "starting install on $DISK, hostname=$HOSTNAME_VALUE"
CURRENT_STAGE=partitioning

# --- partitioning / deploy / target configuration -------------------------

partition_path() {
    local disk="$1" number="$2"
    if [[ "$disk" =~ [0-9]$ ]]; then
        echo "${disk}p${number}"
    else
        echo "${disk}${number}"
    fi
}

ESP="$(partition_path "$DISK" 1)"
ROOT_PART="$(partition_path "$DISK" 2)"

cleanup_mounts() {
    local mnt
    for mnt in "$TARGET/run/udev" "$TARGET/run" "$TARGET/proc" "$TARGET/sys" "$TARGET/dev/pts" "$TARGET/dev" "$TARGET/boot/efi" "$TARGET"; do
        if mountpoint -q "$mnt"; then
            umount -R "$mnt" 2>/dev/null || true
        fi
    done
}

# Everything from here down runs inside a dialog --gauge (the left side of
# a pipe always runs in a subshell in bash, which is why cleanup_mounts and
# the ERR trap - both used below - are defined/registered before this
# point, so the subshell inherits them). Every real command sends its own
# stdout/stderr to $LOG instead of the terminal: dialog --gauge only
# understands its own percent/"XXX"/text protocol on stdin, and anything
# else reaching the terminal while it is drawn would corrupt the display.
# A failure anywhere still reaches the (inherited) ERR trap and calls
# fail(), which prints to the *inherited* stderr (visible around the gauge
# - a harmless cosmetic artifact for what should be a rare path) and exits
# just this subshell.
#
# The whole { ... } | dialog pipeline itself needs the exact same
# trap-plus-pipefail treatment already applied to the tar pipe above, one
# level up: pipefail makes the *pipeline's own* exit status nonzero
# whenever the subshell fails, and the outer ERR trap (still active out
# here) fires on that before the PIPESTATUS check below ever runs -
# verified with an isolated repro before shipping this, since it is
# exactly the same bug class the tar fix above exists for. Disabling only
# `set -e` here is not enough for the same reason it wasn't enough there.
#
# That disabling is inherited by the subshell too (options/traps are
# copied at fork time), which would silently turn off error detection for
# every real command below - also verified with the same repro, the hard
# way, before catching it. The subshell re-enables both for itself as its
# first act, independent of whatever the outer script's state was.
trap - ERR
set +e
# Kernel messages (partition table re-reads, mount/filesystem events, udev)
# print straight to the console device, bypassing stdout/stderr and every
# redirection above entirely - real bug found once services were confirmed
# working: the gauge display got visibly corrupted by lines like
# "[  455.135181][  T1187]  vda: vda1" appearing mid-draw. Lowering the
# console log level for the duration of the gauge (only KERN_EMERG still
# gets through) and restoring the original value right after is the
# standard fix; the current value is read back from /proc/sys/kernel/printk
# instead of assuming a default, so restoring it is exact regardless of
# what this particular kernel/image started with.
ORIGINAL_CONSOLE_LOGLEVEL="$(cut -d' ' -f1 /proc/sys/kernel/printk)"
dmesg -n 1
clear
{
    set -euo pipefail
    trap 'report_error $? "$LINENO" "$BASH_COMMAND"' ERR

    echo 5
    echo "XXX"
    msgf partitioning "$DISK"
    echo
    echo "XXX"
    {
        # Wipe old partition signatures before repartitioning - the same
        # real bug the desktop's Rust installer hit and fixed (commit
        # 9be2782): sgdisk alone can leave stale RAID/LVM/filesystem
        # signatures behind that confuse the kernel and mkfs afterward.
        wipefs -a "$DISK"
        sgdisk --zap-all "$DISK"
        sgdisk -n1:0:+512M -t1:ef00 -c1:"Lyra Server ESP" "$DISK"
        sgdisk -n2:0:0 -t2:8300 -c2:"Lyra Server root" "$DISK"
        # partprobe ships in the parted package (kiwi/config.xml, server
        # profile) - `|| true` is defense in depth for a kernel that
        # already re-read the table on its own, not a substitute for
        # having the tool installed.
        partprobe "$DISK" || true
        udevadm settle
    } >>"$LOG" 2>&1

    echo 15
    CURRENT_STAGE=formatting
    echo "XXX"
    msg formatting
    echo "XXX"
    {
        mkfs.fat -F32 -n LYRASRVESP "$ESP"
        mkfs.ext4 -F -L lyra-server-root "$ROOT_PART"
        mkdir -p "$TARGET"
        mount "$ROOT_PART" "$TARGET"
        mkdir -p "$TARGET/boot/efi"
        mount "$ESP" "$TARGET/boot/efi"
    } >>"$LOG" 2>&1

    echo 25
    CURRENT_STAGE=copying
    echo "XXX"
    msg copying
    echo "XXX"
    # --one-file-system copies the live session's own booted root filesystem
    # (squashfs+overlay) without descending into /proc, /sys, /dev, /run or
    # the just-mounted $TARGET itself, since those are all different mounted
    # filesystems than the root overlay - no separate squashfs extraction
    # step needed.
    #
    # GNU tar exits 1 (not 2) for non-fatal warnings, not just success - a
    # real example hit here: "tar: ./sys: file changed as we read it", from
    # tar stat-ing the /sys mountpoint itself (to decide whether to skip it)
    # while the live kernel's sysfs metadata is constantly changing
    # underneath it. set -e + pipefail would otherwise treat that exit 1 as
    # a hard failure of the whole pipe, so both sides are checked explicitly
    # instead and only exit >=2 (tar's own "fatal error" convention) aborts
    # the install.
    #
    # set +e alone is not enough here: the ERR trap fires on any
    # nonzero-returning command regardless of errexit state (it is only
    # exempted inside if/while/&&/|| conditions, not by `set +e`), and
    # `pipefail` - a separate option, unaffected by `set +e` - still makes
    # the pipe itself report nonzero when either side does. Without
    # disabling the trap too, it fired on tar's exit 1 before the
    # exit-status check below ever ran, which is exactly what happened the
    # first time this was tested in a VM (2026-08-11).
    trap - ERR
    set +e
    { tar --one-file-system --xattrs --acls --numeric-owner -cf - -C / . \
        | tar --xattrs --acls --numeric-owner -xf - -C "$TARGET"; } >>"$LOG" 2>&1
    TAR_EXIT_STATUSES=("${PIPESTATUS[@]}")
    set -e
    trap 'report_error $? "$LINENO" "$BASH_COMMAND"' ERR
    for TAR_EXIT_STATUS in "${TAR_EXIT_STATUSES[@]}"; do
        if [ "$TAR_EXIT_STATUS" -gt 1 ]; then
            COPY_ERROR="$(msgf copy_failed "$TAR_EXIT_STATUS")"
            fail "$COPY_ERROR"
        fi
    done

    echo 70
    CURRENT_STAGE=mounting
    echo "XXX"
    msg mounting
    echo "XXX"
    {
        mount --bind /dev "$TARGET/dev"
        mount --bind /dev/pts "$TARGET/dev/pts"
        # Recursive bind: also propagates the live session's already-mounted
        # efivarfs. A plain non-recursive `mount --bind /sys` does not,
        # which is exactly the bug the desktop's Rust installer found and
        # fixed (MountVirtualFs, installer/README.md) - efibootmgr then has
        # nowhere to write the UEFI NVRAM entry and the install "succeeds"
        # with only the removable-media shim fallback, no real boot entry.
        mount --rbind /sys "$TARGET/sys"
        mount --bind /proc "$TARGET/proc"
        mount -t tmpfs tmpfs "$TARGET/run"
        mkdir -p "$TARGET/run/udev"
        mount --bind /run/udev "$TARGET/run/udev"
    } >>"$LOG" 2>&1
    trap 'report_error_with_cleanup $? "$LINENO" "$BASH_COMMAND"' ERR

    {
        esp_uuid=$(blkid -s UUID -o value "$ESP")
        root_uuid=$(blkid -s UUID -o value "$ROOT_PART")
        cat > "$TARGET/etc/fstab" <<EOF
UUID=$root_uuid / ext4 defaults 0 1
UUID=$esp_uuid /boot/efi vfat umask=0077 0 2
EOF
    } >>"$LOG" 2>&1

    echo 85
    CURRENT_STAGE=configuring
    echo "XXX"
    msg configuring
    echo "XXX"
    # root/senha nunca em argv, só via stdin do chpasswd - mesma regra do
    # instalador desktop (installer/README.md).
    {
        chroot "$TARGET" /bin/bash <<CHROOT_SCRIPT
set -euo pipefail

ln -sf "/usr/share/zoneinfo/$TIMEZONE_VALUE" /etc/localtime
echo "$TIMEZONE_VALUE" > /etc/timezone
hwclock --systohc --utc || hwclock --systohc --utc --directisa || true

cat > /etc/locale.conf <<LOCALE_CONF
LANG=$LOCALE_VALUE
LOCALE_CONF

cat > /etc/vconsole.conf <<VCONSOLE_CONF
KEYMAP=$KEYMAP_VALUE
VCONSOLE_CONF

echo "$HOSTNAME_VALUE" > /etc/hostname

# wheel is not guaranteed to pre-exist on this profile (real gap found in a
# VM install: "useradd: grupo 'wheel' não existe" - the desktop image ends
# up with it some other way that isn't traceable to any single package's
# scriptlet or a sysusers.d declaration; the server profile's minimal
# package set doesn't get it for free). -f makes this a no-op if the group
# is ever already present, so it's safe either way.
groupadd -f wheel
useradd -m -G wheel -s /bin/bash "$USERNAME_VALUE"
printf '%s:%s\n' "$USERNAME_VALUE" "$PASSWORD_VALUE" | chpasswd

# Leap's vendor /usr/etc/sudoers ships "Defaults targetpw" active (asks
# for the *target* user's password, i.e. root's, by default) plus a
# matching "ALL ALL=(ALL) ALL" that only makes sense paired with it. Root
# has no usable password (locked, "root disabled" model), so without
# overriding targetpw here sudo becomes unusable for the account just
# created - real bug found in a VM install ("sudo pediu senha do root").
# Same fix the desktop's Rust installer already applies
# (installer/src/service/operations/deploy.rs).
cat > /etc/sudoers.d/10-server-installer <<'SUDOERS'
Defaults !targetpw
%wheel ALL=(ALL) ALL
SUDOERS
chmod 0440 /etc/sudoers.d/10-server-installer
visudo -cf /etc/sudoers.d/10-server-installer

systemctl enable NetworkManager
systemctl enable firewalld
systemctl enable sshd
# vegad/vega-web unit names assumed (not yet verified against the real
# home:rodrigosbrito:vega packages) - confirm before trusting this against
# real hardware, same caution the desktop installer's README applies to
# every package-specific assumption it made.
systemctl enable vegad
systemctl enable vega-web

# Only ssh and vega-web (9090/tcp) are open by default
# (docs/server-edition.md).
firewall-offline-cmd --zone=public --add-service=ssh >/dev/null
firewall-offline-cmd --zone=public --add-port=9090/tcp >/dev/null

dracut --force --regenerate-all

grub2-mkconfig -o /boot/grub2/grub.cfg
# Match the invocation exercised by the desktop installer on Leap. The
# native shim-install creates both the NVRAM entry and fallback
# EFI/BOOT/BOOTX64.EFI loader; the release gate still verifies both after
# booting the installed disk with Secure Boot enabled and disabled.
shim-install --efi-directory=/boot/efi --config-file=/boot/grub2/grub.cfg

: > /etc/machine-id
CHROOT_SCRIPT
    } >>"$LOG" 2>&1

    echo 95
    CURRENT_STAGE=cleanup
    echo "XXX"
    msg finishing
    echo "XXX"
    # Mirrors the desktop installer's LIVE_ONLY_ARTIFACTS removal
    # (installer/README.md): none of this should survive onto the
    # installed system. The autologin override in particular is a real
    # security issue if left in place - it would give anyone with console
    # access an unauthenticated root shell on every subsequent boot.
    {
        rm -f "$TARGET/etc/systemd/system/getty@tty1.service.d/override.conf"
        rmdir "$TARGET/etc/systemd/system/getty@tty1.service.d" 2>/dev/null || true
        rm -f "$TARGET/root/.bash_profile"
        rm -f "$TARGET/usr/sbin/lyra-server-install"
        rm -f "$TARGET/root/lyra-server-install.log"

        trap - ERR
        cleanup_mounts
    } >>"$LOG" 2>&1

    echo 100
    echo "XXX"
    msg completed
    echo "XXX"
} | dialog --backtitle "$DIALOG_BACKTITLE" --gauge "$(msg preparing)" 10 70 0
GAUGE_PIPE_STATUS="${PIPESTATUS[0]}"
dmesg -n "$ORIGINAL_CONSOLE_LOGLEVEL"
set -e
trap 'report_error $? "$LINENO" "$BASH_COMMAND"' ERR
clear

if [ "$GAUGE_PIPE_STATUS" -ne 0 ]; then
    # The subshell's own ERR trap already printed/logged the real reason;
    # avoid a second, redundant message here.
    exit 1
fi

log "install finished successfully"
echo
msg install_complete
if dialog_yesno "$(msg restart)" 8 50; then
    clear
    reboot
fi
clear
