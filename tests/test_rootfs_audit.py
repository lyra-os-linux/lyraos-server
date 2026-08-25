from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("server_rootfs_audit", ROOT / "scripts/audit-live-rootfs.py")
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = audit
SPEC.loader.exec_module(audit)


class RootfsAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.rootfs = Path(self.temporary.name)
        (self.rootfs / "home/liveuser").mkdir(parents=True)

    def test_clean_live_rootfs_passes(self) -> None:
        self.assertEqual(audit.scan(self.rootfs)["result"], "pass")

    def test_unexpected_build_home_fails(self) -> None:
        (self.rootfs / "home/rodrigo/Git/Lyra").mkdir(parents=True)
        report = audit.scan(self.rootfs)
        self.assertEqual(report["result"], "fail")
        self.assertIn("unexpected-home", {finding["kind"] for finding in report["findings"]})

    def test_host_path_in_file_or_symlink_fails(self) -> None:
        metadata = self.rootfs / "etc/build-info"
        metadata.parent.mkdir()
        metadata.write_text("/home/builder/Git/Lyra/source\n", encoding="utf-8")
        link = self.rootfs / "opt/source"
        link.parent.mkdir()
        os.symlink("/home/builder/Projects/lyraos-server", link)
        kinds = {finding["kind"] for finding in audit.scan(self.rootfs)["findings"]}
        self.assertTrue({"host-path-content", "host-path-symlink"} <= kinds)

    def test_packaged_generic_home_example_is_not_a_lyra_checkout_leak(self) -> None:
        documentation = self.rootfs / "usr/share/doc/example.txt"
        documentation.parent.mkdir(parents=True)
        documentation.write_text("Example: /home/jdoe/src/plugin\n", encoding="utf-8")
        self.assertEqual(audit.scan(self.rootfs)["result"], "pass")
