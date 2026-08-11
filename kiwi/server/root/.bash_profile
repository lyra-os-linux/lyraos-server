# Lyra OS Server live session: auto-runs the console installer after the
# tty1 autologin (systemd/getty@tty1.service.d/override.conf). Exiting or
# interrupting (Ctrl+C) the installer returns here to an interactive root
# shell for diagnostics, matching the desktop live session's model of
# still allowing a terminal for manual disk inspection before installing.
if [ -t 0 ] && [ -x /usr/sbin/lyra-server-install ]; then
    /usr/sbin/lyra-server-install
fi
