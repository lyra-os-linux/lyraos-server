from __future__ import annotations

import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scripts/server-install.sh"
PINNED_COPY = ROOT / "kiwi/server/usr/sbin/lyra-server-install"


class ServerInstallerIdentityTests(unittest.TestCase):
    def test_kiwi_overlay_copy_is_byte_identical_to_the_repo_script(self) -> None:
        # kiwi/<profile>/ overlays are static files copied verbatim by KIWI
        # at build time (kiwi.system.setup.import_overlay_files) - there is
        # no build step that regenerates this copy from scripts/server-install.sh,
        # so drift has to be caught here instead, the same way
        # kiwi/config.xml's comment on the Lyra Installer overlay requires
        # its pinned wrapper/launcher/icon to stay byte-identical to their
        # package sources.
        self.assertTrue(SOURCE.exists())
        self.assertTrue(PINNED_COPY.exists())
        self.assertEqual(SOURCE.read_bytes(), PINNED_COPY.read_bytes())

    def test_both_copies_are_executable(self) -> None:
        for path in (SOURCE, PINNED_COPY):
            mode = path.stat().st_mode
            self.assertTrue(mode & stat.S_IXUSR, f"{path} is not executable")


class ServerInstallerContentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.text = SOURCE.read_text(encoding="utf-8")

    def test_refuses_non_uefi_firmware(self) -> None:
        self.assertIn("/sys/firmware/efi", self.text)

    def test_keymap_options_are_valid_console_keymaps_not_x11_layouts(self) -> None:
        # Real bug found in a VM install: systemd-vconsole-setup.service
        # failed at boot because "br-abnt2" is an X11/XKB layout+variant
        # name, not a valid Linux console keymap (loadkeys/vconsole.conf
        # use a different naming scheme). Confirmed against this repo's own
        # dev machine: `localectl list-keymaps | grep ^br` never lists
        # anything named "abnt2" - plain "br" is the real console keymap
        # for a standard Brazilian ABNT2 keyboard.
        self.assertIn('dialog_menu KEYMAP_VALUE "Layout de teclado (console):" "us" "br"', self.text)

    def test_wipes_signatures_before_repartitioning(self) -> None:
        # Same real bug the desktop installer hit and fixed (commit
        # 9be2782): sgdisk alone can leave stale signatures behind.
        wipefs_index = self.text.index("wipefs -a")
        sgdisk_index = self.text.index("sgdisk --zap-all")
        self.assertLess(wipefs_index, sgdisk_index)

    def test_sys_bind_mount_is_recursive(self) -> None:
        # A plain non-recursive bind of /sys does not propagate the live
        # session's efivarfs, which is exactly the bug the desktop
        # installer's README documents having fixed (MountVirtualFs).
        self.assertIn('mount --rbind /sys "$TARGET/sys"', self.text)
        self.assertNotIn('mount --bind /sys "$TARGET/sys"', self.text)

    def test_console_loglevel_is_lowered_and_restored_around_the_gauge(self) -> None:
        # Real bug found once services were confirmed working: kernel
        # messages (partition table re-reads, mount/udev events) print
        # straight to the console device, bypassing every stdout/stderr
        # redirection in this script entirely, and visibly corrupted the
        # dialog --gauge display. dmesg -n lowers/restores the console log
        # level; the original value is read back from
        # /proc/sys/kernel/printk instead of hardcoding a default so the
        # restore is exact regardless of what the image ships as default.
        lower_index = self.text.index("dmesg -n 1")
        restore_index = self.text.index('dmesg -n "$ORIGINAL_CONSOLE_LOGLEVEL"')
        self.assertLess(lower_index, restore_index)
        self.assertIn(
            'ORIGINAL_CONSOLE_LOGLEVEL="$(cut -d\' \' -f1 /proc/sys/kernel/printk)"',
            self.text,
        )

    def test_firewall_opens_only_ssh_and_vega_web(self) -> None:
        self.assertIn("--add-service=ssh", self.text)
        self.assertIn("--add-port=9090/tcp", self.text)

    def test_vega_services_are_enabled_on_the_target(self) -> None:
        self.assertIn("systemctl enable vegad", self.text)
        self.assertIn("systemctl enable vega-web", self.text)

    def test_wheel_group_is_created_before_useradd(self) -> None:
        # Real bug found in a VM install: "useradd: grupo 'wheel' não
        # existe". The desktop image ends up with a pre-existing wheel
        # group through some path that isn't traceable to any single
        # package (checked: no installed package's RPM scriptlets create
        # it); the server profile's minimal package set doesn't get it for
        # free, so this script creates it itself instead of assuming it.
        groupadd_index = self.text.index("groupadd -f wheel")
        useradd_index = self.text.index("useradd -m -G wheel")
        self.assertLess(groupadd_index, useradd_index)

    def test_sudo_disables_vendor_targetpw(self) -> None:
        # Real bug found in a VM install: "sudo pediu senha do root". Leap's
        # vendor /usr/etc/sudoers ships "Defaults targetpw" active (asks for
        # the *target* user's password, root's by default) plus a matching
        # "ALL ALL=(ALL) ALL" that only makes sense paired with it - without
        # overriding it, sudo is unusable for the account this script just
        # created, since root has no usable password (locked, "root
        # disabled" model). Same fix already applied by the desktop's Rust
        # installer (installer/src/service/operations/deploy.rs).
        self.assertIn("Defaults !targetpw", self.text)
        targetpw_index = self.text.index("Defaults !targetpw")
        wheel_rule_index = self.text.index("%wheel ALL=(ALL) ALL")
        self.assertLess(targetpw_index, wheel_rule_index)

    def test_password_never_reaches_argv(self) -> None:
        # Same rule as the desktop installer (installer/README.md): the
        # password is piped to chpasswd's stdin, never passed as an
        # argument. Every "chpasswd" occurrence that isn't prose in a
        # comment must be the pipe form.
        chpasswd_lines = [
            line for line in self.text.splitlines()
            if "chpasswd" in line and not line.strip().startswith("#")
        ]
        self.assertTrue(chpasswd_lines)
        for line in chpasswd_lines:
            self.assertIn("| chpasswd", line, line)

    def test_live_only_artifacts_are_removed_from_the_target(self) -> None:
        # The autologin override in particular would otherwise leave an
        # unauthenticated root console shell on every boot of the
        # installed system.
        self.assertIn('rm -f "$TARGET/etc/systemd/system/getty@tty1.service.d/override.conf"', self.text)
        self.assertIn('rm -f "$TARGET/root/.bash_profile"', self.text)

    def test_no_set_dash_x_that_could_leak_the_password_to_logs(self) -> None:
        self.assertNotIn("set -x", self.text)
        self.assertNotIn("set -eux", self.text)

    @unittest.skipUnless(shutil.which("shellcheck"), "shellcheck not installed")
    def test_shellcheck_is_clean(self) -> None:
        result = subprocess.run(
            ["shellcheck", str(SOURCE)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(shutil.which("bash"), "bash not installed")
    def test_syntax_is_valid(self) -> None:
        result = subprocess.run(
            ["bash", "-n", str(SOURCE)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


@unittest.skipUnless(shutil.which("dialog"), "dialog not installed")
class DialogMenuBehaviorTests(unittest.TestCase):
    # Real bug found running --profile server end to end in a VM (2026-08-11):
    # the original read-based choose_from_menu used a local variable named
    # "choice" for its own read loop, and choose_disk called it as
    # `choose_from_menu choice ...` - passing the literal name "choice" as
    # the output variable. Bash resolves unqualified names to the nearest
    # enclosing *local* scope, so choose_from_menu's own local "choice"
    # shadowed the caller's, and choose_disk's "choice" was never actually
    # assigned ("choice: unbound variable" under set -u). shellcheck did not
    # catch this. The prompts were rewritten to use dialog afterward (still
    # per docs/server-edition.md's decision on a standalone shell installer,
    # just with a real TUI instead of bare `read -p`); this test now
    # reproduces the same collision pattern against dialog_menu, the
    # function that replaced choose_from_menu, to make sure the fix (the
    # __-prefixed internal names) carried over and not just the symptom.
    #
    # dialog runs fine without a real controlling terminal (verified: it
    # only needs $TERM and a byte stream on stdin/stdout, confirmed here by
    # running it through subprocess.run the same way this test does), so
    # this is a real behavioral test, not a text-content check.

    def setUp(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        start = text.index("# --- prompts")
        end = text.index("# lsblk -e 7,11")
        self.functions = text[start:end]

    def _run(self, driver: str, stdin: str) -> subprocess.CompletedProcess:
        script = (
            "set -euo pipefail\n"
            "LYRA_PRETTY_NAME='Test'\n"
            'fail() { echo "FAIL: $*" >&2; exit 1; }\n'
            f"{self.functions}\n{driver}\n"
        )
        return subprocess.run(
            ["bash", "-c", script],
            input=stdin,
            capture_output=True,
            text=True,
            env={**__import__("os").environ, "TERM": "xterm"},
        )

    def test_output_variable_named_choice_is_not_shadowed(self) -> None:
        # Same call pattern as choose_disk: a local variable literally
        # named "choice" passed as the out_var.
        driver = (
            'pick() {\n'
            '    local choice\n'
            '    dialog_menu choice "Pick:" "alpha" "beta" "gamma"\n'
            '    echo "RESULT=$choice"\n'
            '}\n'
            'pick'
        )
        result = self._run(driver, "2\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("RESULT=beta", result.stdout)

    def test_output_variable_with_an_unrelated_name_still_works(self) -> None:
        driver = 'dialog_menu picked "Pick:" "alpha" "beta" "gamma"\necho "RESULT=$picked"'
        result = self._run(driver, "3\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("RESULT=gamma", result.stdout)

    def test_dialog_inputbox_retries_on_invalid_input(self) -> None:
        driver = (
            "dialog_inputbox HOST 'Hostname:' '^[a-z0-9-]+$' 'invalid'\n"
            'echo "RESULT=$HOST"'
        )
        # First answer fails the pattern (uppercase/underscore) and pops an
        # error msgbox, which needs its own Enter to dismiss (the blank
        # line) before the retried inputbox gets the second, valid answer.
        result = self._run(driver, "Bad_Name\n\nvalid-host\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("RESULT=valid-host", result.stdout)

    def test_dialog_yesno_exit_status_drives_the_caller(self) -> None:
        driver = (
            'if dialog_yesno "Confirm?" 8 40; then echo RESULT=yes; else echo RESULT=no; fi'
        )
        result = self._run(driver, "\n")  # Enter accepts the focused "Yes" button.
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("RESULT=yes", result.stdout)


@unittest.skipUnless(shutil.which("bash"), "bash not installed")
class TarExitStatusToleranceTests(unittest.TestCase):
    # Real bug found running --profile server end to end in a VM
    # (2026-08-11), on the very first attempt to fix the *previous* real
    # bug: GNU tar exits 1 (not 2) for non-fatal warnings ("tar: ./sys:
    # file changed as we read it" reading a live sysfs mountpoint), and the
    # first fix attempt only wrapped the pipe in `set +e` before checking
    # PIPESTATUS. That was not enough: bash's ERR trap fires on any
    # nonzero-returning command independently of errexit state (`set +e`
    # does not suppress it - only if/while/&&/|| conditions and `!` do),
    # and `pipefail` is a separate option `set +e` does not touch either,
    # so the pipe's overall nonzero status still reached the *trap*, which
    # ran and exited before the PIPESTATUS check ever executed. A first,
    # too-narrow local repro with `bash -c '...'` failed to catch this
    # (subtle quoting bug in the repro itself deferred $LINENO wrong);
    # extracting the actual shipped code, like this test does, is what
    # actually exercises the real bug.
    #
    # Verified against a fake `tar` on PATH instead of copying the real
    # filesystem - the point under test is the trap/errexit/pipefail
    # interaction around the pipe, not tar's own behavior.

    def setUp(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        # log()/fail()/the initial trap registration, then just the tar
        # copy step (now nested inside the dialog --gauge subshell - see
        # GaugePipeErrorDetectionTests below for that outer wrapper) -
        # skipping the root/UEFI checks, the interactive dialog wizard and
        # the partitioning/mount steps before it, none of which this test
        # needs or can satisfy in a sandbox (no root, no real disks).
        utilities = text[text.index("log() {") : text.index("if [ \"$(id -u)\"")]
        tar_step_end = text.index('fail "cópia do sistema para o disco falhou')
        tar_step_end = text.index("done", tar_step_end) + len("done")
        tar_step = text[text.index("    echo 25\n") : tar_step_end]
        self.functions = utilities + tar_step

    def _run(self, fake_tar_write_exit: int, fake_tar_read_exit: int) -> subprocess.CompletedProcess:
        with tempfile.TemporaryDirectory() as bin_dir, tempfile.TemporaryDirectory() as work_dir:
            fake_tar = Path(bin_dir) / "tar"
            fake_tar.write_text(
                "#!/bin/bash\n"
                "for arg in \"$@\"; do\n"
                '    if [ "$arg" = "-cf" ]; then exit "$FAKE_TAR_WRITE_EXIT"; fi\n'
                '    if [ "$arg" = "-xf" ]; then exit "$FAKE_TAR_READ_EXIT"; fi\n'
                "done\n"
                "exit 0\n"
            )
            fake_tar.chmod(0o755)
            script = (
                "set -euo pipefail\n"
                f"TARGET={work_dir}\n"
                f"LOG={work_dir}/install.log\n"
                ": > \"$LOG\"\n"
                f"{self.functions}\n"
                'echo "REACHED_END"\n'
            )
            env = {
                "PATH": f"{bin_dir}:/usr/bin:/bin",
                "FAKE_TAR_WRITE_EXIT": str(fake_tar_write_exit),
                "FAKE_TAR_READ_EXIT": str(fake_tar_read_exit),
            }
            return subprocess.run(
                ["bash", "-c", script], capture_output=True, text=True, env=env
            )

    def test_warning_exit_status_one_does_not_abort_the_install(self) -> None:
        result = self._run(fake_tar_write_exit=1, fake_tar_read_exit=0)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("REACHED_END", result.stdout)

    def test_fatal_exit_status_two_aborts_with_the_specific_message(self) -> None:
        result = self._run(fake_tar_write_exit=2, fake_tar_read_exit=0)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("cópia do sistema para o disco falhou", result.stderr)
        self.assertNotIn("REACHED_END", result.stdout)
        # The generic trap message must NOT be what the user sees here -
        # that was exactly the symptom of the bug this test locks in.
        self.assertNotIn("instalação interrompida", result.stderr)


@unittest.skipUnless(shutil.which("dialog"), "dialog not installed")
class GaugePipeErrorDetectionTests(unittest.TestCase):
    # Adding the dialog --gauge progress bar hit the *same* trap/errexit/
    # pipefail bug class as TarExitStatusToleranceTests above, twice, in
    # the same sitting:
    #
    # 1. The whole `{ install steps } | dialog --gauge` pipeline needs the
    #    same treatment as the tar pipe: pipefail makes the pipeline's own
    #    exit status nonzero whenever the subshell (left side of any pipe
    #    is always a subshell in bash) fails, and the outer ERR trap fires
    #    on that before the PIPESTATUS check ever runs.
    # 2. Disabling the outer trap/errexit to avoid (1) is *inherited by
    #    the subshell itself* (options and traps are copied at fork time),
    #    which silently turned off error detection for every real command
    #    inside it - a real command failing (e.g. a bad mkfs) would have
    #    been swallowed entirely, reported as a successful install. The
    #    subshell has to re-enable both for itself, first thing, to get
    #    real detection back.
    #
    # This test extracts the actual shipped wrapper (trap/set +e before
    # the pipe, the subshell's own set -e/trap re-registration, and the
    # PIPESTATUS check after) and drives it with a minimal fake gauge body
    # instead of the real (destructive, root-only) install steps.

    def setUp(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        self.prefix = text[
            text.index("trap - ERR\nset +e\n")
            : text.index("\n\n    echo 5")
        ]
        end_marker = "avoid a second, redundant message here.\n    exit 1\nfi"
        self.suffix = text[
            text.index('} | dialog --backtitle "$DIALOG_BACKTITLE" --gauge')
            : text.index(end_marker) + len(end_marker)
        ]

    def _run(self, body: str) -> subprocess.CompletedProcess:
        script = (
            "set -euo pipefail\n"
            "LOG=/dev/null\n"
            "DIALOG_BACKTITLE='Test'\n"
            'fail() { echo "FAIL: $*" >&2; exit 1; }\n'
            "trap 'fail \"instalação interrompida (linha $LINENO)\"' ERR\n"
            f"{self.prefix}\n{body}\n{self.suffix}\n"
            'echo "REACHED_END"\n'
        )
        return subprocess.run(
            ["bash", "-c", script],
            capture_output=True,
            text=True,
            env={**__import__("os").environ, "TERM": "xterm"},
        )

    def test_a_failing_step_inside_the_subshell_is_actually_detected(self) -> None:
        body = 'echo 50\necho "XXX"\necho "Fake step"\necho "XXX"\nfalse'
        result = self._run(body)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("REACHED_END", result.stdout)

    def test_a_successful_run_reaches_past_the_gauge(self) -> None:
        body = 'echo 50\necho "XXX"\necho "Fake step"\necho "XXX"\ntrue'
        result = self._run(body)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("REACHED_END", result.stdout)


if __name__ == "__main__":
    unittest.main()
