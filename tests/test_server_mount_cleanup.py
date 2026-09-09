"""Exercise the shipped install worker, with faults at its external commands.

The same cases can use real mounts in the guarded disposable QEMU guest.
The host run never mounts, partitions, formats, or executes the chroot body.
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
import shlex
import shutil
import signal
import subprocess
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scripts/server-install.sh"
NATIVE = os.environ.get("LYRA_SERVER_CLEANUP_VM") == "1"


@contextmanager
def workspace():
    work = Path(tempfile.mkdtemp(prefix="server-cleanup-"))
    try:
        yield work
    finally:
        if NATIVE:
            remaining = [line for line in Path("/proc/self/mountinfo").read_text().splitlines()
                         if line.split()[4] == str(work) or line.split()[4].startswith(str(work) + "/")]
            if remaining:
                raise RuntimeError("fixture mount remains; refusing directory removal")
        shutil.rmtree(work)


COMMANDS = r'''
validate_target_disk() { :; }
wipefs() { :; }; sgdisk() { :; }; partprobe() { :; }; udevadm() { :; }
dmesg() { printf 'console:%s\n' "$*" >> "$EVENTS"; }
clear() { :; }
mkfs.fat() { if [ "$NATIVE" = 1 ]; then command mkfs.fat "$@"; fi; }
mkfs.ext4() { if [ "$NATIVE" = 1 ]; then command mkfs.ext4 "$@"; fi; }
blkid() { printf '%s\n' fixture-uuid; }
chroot() {
    cat >/dev/null
    if [ "$FAULT" = busy ]; then
        (cd "$TARGET"; exec sleep 30) </dev/null >/dev/null 2>&1 &
        printf '%s\n' "$!" > "$READY"
        # Wait until the process actually holds the target as its cwd.
        while [ ! "$TARGET" -ef "/proc/$!/cwd" ]; do sleep 0.01; done
        return 47
    fi
    if [ "$FAULT" = chroot ]; then return 47; fi
}
dialog() {
    if [ "$FAULT" = gauge-pipe ]; then return 17; fi
    cat >/dev/null
    if [ "$FAULT" = gauge-status ]; then return 17; fi
}
mountpoint() {
    local mnt="${!#}"
    if [ "$NATIVE" = 1 ]; then
        local result=0
        command mountpoint "$@" || result=$?
        printf 'mountpoint:%s:%s\n' "$result" "$mnt" >> "$EVENTS"
        return "$result"
    fi
    [ -f "$STATE/${mnt//\//_}" ]
}
mount() {
    local mnt="${!#}"
    MOUNT_TRY=$((MOUNT_TRY+1))
    export INSTALL_TEST_WORKER_PID=$BASHPID
    printf 'mount:%s\n' "$mnt" >> "$EVENTS"
    if [ "$FAULT" = "mount-$MOUNT_TRY" ]; then return 32; fi
    if [ "$NATIVE" = 1 ]; then
        # A direct kernel boot has no UEFI sysfs tree/NVRAM. Stand in the
        # directory tree for /sys and tmpfs for efivarfs; still use real
        # bind/child mounts, without claiming firmware/boot qualification.
        if [ "${2:-}" = efivarfs ]; then
            command mount -t tmpfs tmpfs "$mnt" || return
        elif [ "${2:-}" = /sys ]; then
            command mount --bind "$FIXTURE/sys" "$mnt" || return
        else
            command mount "$@" || return
        fi
    else
        printf '%s\n' "$mnt" > "$STATE/${mnt//\//_}"
    fi
    if [ "$FAULT" = "partial-$MOUNT_TRY" ]; then return 33; fi
    if [ "$FAULT" = "signal-$MOUNT_TRY" ]; then kill -"$TEST_SIGNAL" "$BASHPID"; fi
    if [ "$FAULT" = "hold-$MOUNT_TRY" ]; then
        # Publish readiness from the foreground child, after it exists.
        # Otherwise group delivery could race with the child being forked.
        bash -c 'printf "%s\n" "$PPID" > "$1"; exec sleep 30' _ "$READY"
    fi
}
umount() {
    local mnt="${!#}" entry value
    printf 'umount:%s\n' "$mnt" >> "$EVENTS"
    if [ "$CLEANUP_FAIL" = 1 ]; then return 71; fi
    if [ "$NATIVE" = 1 ]; then
        local result=0
        command umount "$@" || result=$?
        return "$result"
    fi
    for entry in "$STATE"/*; do
        [ -f "$entry" ] || continue
        read -r value < "$entry"
        if [[ "$value" = "$mnt" || "$value" = "$mnt/"* ]]; then rm -f "$entry"; fi
    done
}
tar() {
    if [[ " $* " = *' -cf '* ]]; then
        if [ "$FAULT" = tar-write ]; then return 23; fi
        if [ "$FAULT" = tar-both ]; then return 141; fi
        if [ "$FAULT" = tar-signal ]; then
            kill -"$TEST_SIGNAL" "$INSTALL_TEST_WORKER_PID"
        fi
        if [ "$FAULT" = tar-hold ]; then
            bash -c 'printf "%s\n" "$PPID" > "$1"; exec sleep 30' _ "$READY"
        fi
        if [ "$FAULT" = tar-invalid ]; then printf 'invalid archive\n'; return; fi
        command tar -cf - -C "$FIXTURE" .
    else
        if [ "$FAULT" = tar-read ] || [ "$FAULT" = tar-both ]; then
            cat >/dev/null
            printf 'partial copy\n' > "$TARGET/partial-copy"
            return 24
        fi
        command tar -xf - -C "$TARGET"
    fi
}
'''


class ServerMountCleanupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if NATIVE:
            # Refuse to format anything unless BOTH the boot marker and
            # dedicated device identities match the runner's scratch disks.
            assert os.geteuid() == 0
            assert "lyra.server-cleanup-test=1" in Path("/proc/cmdline").read_text().split()
            for disk, serial in (("vda", "lyra-srv-root-test"), ("vdb", "lyra-srv-esp-test")):
                observed = Path(f"/sys/block/{disk}/serial").read_text().strip()
                assert observed == serial, (disk, observed, serial)
        text = SOURCE.read_text()
        localization = text[text.index("UI_LANGUAGE=en"):text.index("RELEASE_METADATA=")]
        helpers = text[text.index("log() {"):text.index('if [ "$(id -u)"')]
        mounts = text[text.index("cleanup_mounts() {"):text.index("validate_target_disk() {")]
        worker = text[text.index("trap - ERR\nset +e\nvalidate_target_disk\n"):text.index('log "install finished successfully"')]
        cls.production = localization + helpers + mounts
        cls.worker = worker

    def run_case(self, fault="none", *, cleanup_fail=False, sig="TERM", group_signal=False, preexisting=False):
        with workspace() as work:
            target = work / "target"
            target.mkdir()
            (work / "state").mkdir()
            for name in ("etc", "root", "usr/sbin", "sys/firmware/efi/efivars"):
                (work / "fixture" / name).mkdir(parents=True, exist_ok=True)
            (work / "fixture/etc/fixture").write_text("test system payload\n")
            events = work / "events"
            events.touch()
            if preexisting:
                if NATIVE:
                    subprocess.run(["mount", "-t", "tmpfs", "tmpfs", str(target)], check=True)
                else:
                    (work / "state" / str(target).replace("/", "_")).write_text(str(target))
            values = {
                "TARGET": str(target), "LOG": str(work / "installer.log"), "STATE": str(work / "state"),
                "EVENTS": str(events), "FIXTURE": str(work / "fixture"), "READY": str(work / "ready"),
                "NATIVE": str(int(NATIVE)), "FAULT": fault, "CLEANUP_FAIL": str(int(cleanup_fail)),
                "TEST_SIGNAL": sig, "DISK": "/dev/lyra-test-unused",
                "ROOT_PART": "/dev/vda" if NATIVE else "/dev/lyra-test-root",
                "ESP": "/dev/vdb" if NATIVE else "/dev/lyra-test-esp",
                "MOUNT_TRY": "0", "CURRENT_STAGE": "partitioning", "DIALOG_BACKTITLE": "Test",
                "TIMEZONE_VALUE": "UTC", "LOCALE_VALUE": "en_US.UTF-8", "KEYMAP_VALUE": "us",
                "HOSTNAME_VALUE": "test", "USERNAME_VALUE": "alice", "PASSWORD_VALUE": "test-only-secret",
            }
            setup = "\n".join(f"{key}={shlex.quote(value)}" for key, value in values.items())
            script = "set -euo pipefail\n" + setup + "\n" + self.production + COMMANDS + "\n" + self.worker + '\necho REACHED_END\n'
            process = subprocess.Popen(["bash", "-c", script], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       text=True, start_new_session=True)
            try:
                if group_signal:
                    deadline = time.monotonic() + 15
                    while not (work / "ready").exists():
                        if process.poll() is not None or time.monotonic() > deadline:
                            self.fail("worker did not reach signal checkpoint")
                        time.sleep(0.02)
                    os.killpg(process.pid, getattr(signal, "SIG" + sig))
                stdout, stderr = process.communicate(timeout=30)
                trace = events.read_text().splitlines()
                log = (work / "installer.log").read_text()
                if NATIVE:
                    # Inspect the kernel table, not the command ledger.
                    mounted = [line.split()[4] for line in Path("/proc/self/mountinfo").read_text().splitlines()
                               if line.split()[4] == str(target) or line.split()[4].startswith(str(target) + "/")]
                    self.assertTrue(Path("/proc/self/mountinfo").is_file())
                    self.assertTrue(subprocess.run(["mountpoint", "-q", "/sys"]).returncode == 0)
                    self.assertTrue(subprocess.run(["mountpoint", "-q", "/dev/pts"]).returncode == 0)
                else:
                    mounted = [entry.read_text().strip() for entry in (work / "state").iterdir()]
                if cleanup_fail or preexisting or fault == "busy":
                    self.assertTrue(mounted, (fault, stdout, stderr, log, trace))
                else:
                    self.assertEqual(mounted, [], (fault, stdout, stderr, log, trace))
                if not preexisting:
                    expected = [entry.removeprefix("mount:") for entry in trace if entry.startswith("mount:")]
                    if fault.startswith("mount-"):
                        expected = expected[:-1]
                    self.assertEqual([entry.removeprefix("umount:") for entry in trace if entry.startswith("umount:")], list(reversed(expected)))
                self.assertNotIn("test-only-secret", stdout + stderr + log)
                self.assertTrue(trace[-1].startswith("console:-n "), trace)
                return process.returncode, stdout, stderr, log, trace
            finally:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.communicate()
                if NATIVE:
                    # Fixture teardown only, after assertions. Never use
                    # lazy/forced unmounts to make the production test pass.
                    subprocess.run(["umount", "-R", str(target)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    remaining = [line for line in Path("/proc/self/mountinfo").read_text().splitlines()
                                 if line.split()[4] == str(target) or line.split()[4].startswith(str(target) + "/")]
                    if remaining:
                        raise RuntimeError("fixture mount remains; refusing directory removal")

    def test_each_failed_mount_unwinds_only_completed_mounts(self):
        for number in range(1, 10):
            with self.subTest(mount=number):
                status, out, err, log, _ = self.run_case(f"mount-{number}")
                self.assertEqual(status, 32, err + log)
                self.assertIn("FAIL status=32", log)
                self.assertNotIn("REACHED_END", out)

    def test_mount_completed_before_command_failure_is_also_unmounted(self):
        for number in range(1, 10):
            with self.subTest(mount=number):
                status, _, err, log, _ = self.run_case(f"partial-{number}")
                self.assertEqual(status, 33, err + log)

    def test_copy_failures_preserve_the_original_status(self):
        for fault, expected in (("tar-write", 23), ("tar-read", 24), ("tar-both", 24), ("tar-invalid", 2)):
            with self.subTest(fault=fault):
                status, out, err, log, _ = self.run_case(fault)
                self.assertEqual(status, expected, err + log)
                self.assertIn(f"tar returned {expected}", err)
                self.assertNotIn("REACHED_END", out)

    def test_signals_after_partial_preparation_and_during_copy(self):
        for sig, expected in (("HUP", 129), ("INT", 130), ("TERM", 143)):
            for fault in ("signal-1", "signal-2", "signal-6", "signal-9", "tar-signal"):
                with self.subTest(signal=sig, fault=fault):
                    status, out, err, log, _ = self.run_case(fault, sig=sig)
                    self.assertEqual(status, expected, err + log)
                    self.assertIn(f"signal={sig}", log)
                    self.assertNotIn("REACHED_END", out)

    def test_foreground_group_interruption_restores_console_and_unmounts(self):
        for sig, expected in (("HUP", 129), ("INT", 130), ("TERM", 143)):
            for fault in ("hold-2", "tar-hold", "hold-9"):
                with self.subTest(signal=sig, fault=fault):
                    status, out, err, log, _ = self.run_case(fault, sig=sig, group_signal=True)
                    self.assertEqual(status, expected, err + log)
                    self.assertNotIn("REACHED_END", out)

    def test_cleanup_failure_keeps_primary_error_and_reports_both(self):
        status, out, err, log, _ = self.run_case("tar-read", cleanup_fail=True)
        self.assertEqual(status, 24, err + log)
        self.assertIn("FAIL status=24", log)
        self.assertIn("message=unmount-failed", log)
        self.assertIn("message=cleanup-after-failure", log)
        self.assertNotIn("REACHED_END", out)

    def test_cleanup_failure_alone_prevents_success(self):
        status, out, err, log, _ = self.run_case(cleanup_fail=True)
        self.assertEqual(status, 1, err + log)
        self.assertIn("could not be completely unmounted", err)
        self.assertNotIn("REACHED_END", out)

    def test_late_configuration_failure_also_unmounts(self):
        status, out, err, log, _ = self.run_case("chroot")
        self.assertEqual(status, 47, err + log)
        self.assertNotIn("REACHED_END", out)

    @unittest.skipUnless(NATIVE, "requires guarded QEMU mount namespace")
    def test_real_busy_mount_is_reported_without_hiding_primary_failure(self):
        status, out, err, log, _ = self.run_case("busy")
        self.assertEqual(status, 47, err + log)
        self.assertIn("message=unmount-failed", log)
        self.assertIn("busy", log)
        self.assertNotIn("REACHED_END", out)

    def test_closed_or_failed_gauge_never_reports_success(self):
        for fault in ("gauge-pipe", "gauge-status"):
            with self.subTest(fault=fault):
                status, out, _, _, _ = self.run_case(fault)
                self.assertIn(status, (17, 141))
                self.assertNotIn("REACHED_END", out)

    def test_preexisting_mount_is_preserved(self):
        status, out, err, log, trace = self.run_case(preexisting=True)
        self.assertEqual(status, 1, err + log)
        self.assertIn("already in use", log)
        self.assertFalse(any(entry.startswith("umount:") for entry in trace))
        self.assertNotIn("REACHED_END", out)

    def test_success_and_a_new_attempt_after_failure(self):
        self.assertEqual(self.run_case("tar-invalid")[0], 2)
        status, out, err, log, _ = self.run_case()
        self.assertEqual(status, 0, err + log)
        self.assertIn("REACHED_END", out)


if __name__ == "__main__":
    unittest.main()
