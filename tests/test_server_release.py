from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("lyra_server_release", ROOT / "scripts/server-release.py")
assert SPEC and SPEC.loader
server_release_module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = server_release_module
SPEC.loader.exec_module(server_release_module)
ServerRelease = server_release_module.ServerRelease


def sample_release(**overrides: object) -> ServerRelease:
    values: dict[str, object] = {
        "calendar_version": "27.02",
        "stage": "alpha",
        "iteration": 1,
        "image_name": "lyra-os-server",
        "architecture": "x86_64",
    }
    values.update(overrides)
    release = ServerRelease(**values)
    release.validate()
    return release


class ServerReleaseConventionTests(unittest.TestCase):
    def test_alpha_identifiers(self) -> None:
        release = sample_release()
        self.assertEqual(release.version_id, "27.02-alpha1")
        self.assertEqual(release.tag, "server-v27.02-alpha1")
        self.assertEqual(release.iso_filename, "lyra-os-server.x86_64-27.02-alpha1.iso")
        self.assertEqual(release.volume_id, "LYRA_OS_SERVER_27_02_ALPHA1")
        self.assertEqual(release.pretty_name, "Lyra OS Server 27.02 Alpha 1")

    def test_no_codename_field_exists(self) -> None:
        release = sample_release()
        self.assertNotIn("(", release.pretty_name)
        self.assertFalse(hasattr(release, "codename"))

    def test_final_identifiers(self) -> None:
        release = sample_release(stage="release", iteration=0)
        self.assertEqual(release.version_id, "27.02")
        self.assertEqual(release.tag, "server-v27.02")
        self.assertEqual(release.pretty_name, "Lyra OS Server 27.02")

    def test_prerelease_requires_iteration(self) -> None:
        with self.assertRaisesRegex(ValueError, "positive iteration"):
            sample_release(iteration=0)

    def test_final_rejects_iteration(self) -> None:
        with self.assertRaisesRegex(ValueError, "iteration = 0"):
            sample_release(stage="release", iteration=1)

    def test_tag_namespace_does_not_collide_with_desktop(self) -> None:
        release = sample_release()
        self.assertTrue(release.tag.startswith("server-v"))


class ServerRepositoryMetadataTests(unittest.TestCase):
    def test_generated_files_are_current(self) -> None:
        release = ServerRelease.from_file()
        for path, expected in server_release_module.render_files(release).items():
            self.assertTrue(path.exists(), path)
            self.assertEqual(path.read_text(encoding="utf-8"), expected, path)

    def test_version_and_volid_are_unique_in_the_single_profile_config(self) -> None:
        # kiwi/config.xml has a single <preferences> block in this repo (no
        # more per-profile split - docs/server-edition.md's 2026-08-23
        # note), so <version>/volid are each unique file-wide.
        xml_path = ROOT / "kiwi/config.xml"
        xml = xml_path.read_text(encoding="utf-8")
        self.assertEqual(xml.count("<version>"), 1)
        self.assertEqual(xml.count('volid="'), 1)
        self.assertIn("LYRA_OS_SERVER_", xml)

    def test_build_manifest_is_traceable(self) -> None:
        release = ServerRelease.from_file()
        with tempfile.TemporaryDirectory() as directory:
            iso = Path(directory) / release.iso_filename
            iso.write_bytes(b"test server ISO payload")
            output = Path(directory) / "build.json"
            self.assertEqual(server_release_module.write_build_manifest(release, iso, output), 0)
            document = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(document["version"], release.version_id)
            self.assertEqual(document["product"], "Lyra OS Server")
            self.assertEqual(document["iso"]["filename"], release.iso_filename)
            self.assertRegex(document["source"]["commit"], r"^[0-9a-f]{40}$")


class ServerBeta1GateTests(unittest.TestCase):
    def test_builder_requires_a_clean_tree_and_valid_iso_source_commit(self) -> None:
        builder = (ROOT / "scripts/build-server-beta1.sh").read_text(encoding="utf-8")
        self.assertIn('git cat-file -e "$COMMIT^{commit}"', builder)
        self.assertIn("git status --porcelain --untracked-files=normal", builder)

    def test_uploader_requires_signed_bundle_and_open_blocker_query(self) -> None:
        uploader = (ROOT / "scripts/upload-server-beta1-sourceforge.sh").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("--decision-file", uploader)
        self.assertIn("sha256sum -c", uploader)
        self.assertIn("gh issue list --state open --label server", uploader)
        self.assertIn('test("\\\\[P[01]\\\\]"; "i")', uploader)
        self.assertNotIn("release-decision.json", uploader)

    def test_release_scripts_pin_the_canonical_signing_key(self) -> None:
        fingerprint = "01B63EEDBE6B079126A0116EFA7353A131ECEFEB"
        builder = (ROOT / "scripts/build-server-beta1.sh").read_text(encoding="utf-8")
        uploader = (ROOT / "scripts/upload-server-beta1-sourceforge.sh").read_text(
            encoding="utf-8"
        )
        for script in (builder, uploader):
            self.assertIn(fingerprint, script)
            self.assertIn("VALIDSIG", script)
            self.assertIn("verify_release_signature", script)
        self.assertIn('--local-user "$RELEASE_SIGNING_FINGERPRINT"', builder)


if __name__ == "__main__":
    unittest.main()
