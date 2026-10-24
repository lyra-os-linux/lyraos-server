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
        "product_version": "1.1",
        "base_distribution": "opensuse-leap",
        "base_version": "16.1",
        "stage": "alpha",
        "iteration": 1,
        "revision": 0,
        "image_name": "lyra-os-server",
        "architecture": "x86_64",
        "codename": "Delos",
        "codename_id": "delos",
    }
    values.update(overrides)
    release = ServerRelease(**values)
    release.validate()
    return release


class ServerReleaseConventionTests(unittest.TestCase):
    def test_alpha_identifiers(self) -> None:
        release = sample_release()
        self.assertEqual(release.version_id, "1.1-alpha.1")
        self.assertEqual(release.tag, "server-v1.1-alpha.1")
        self.assertEqual(release.iso_filename, "lyra-os-server-1.1-alpha.1-x86_64.iso")
        self.assertEqual(release.volume_id, "LYRA_OS_SERVER_1_1_ALPHA_1")
        self.assertEqual(release.pretty_name, "Lyra OS Server 1.1 Alpha 1 (Delos)")

    def test_beta_point_candidate_identifiers(self) -> None:
        release = sample_release(stage="beta", iteration=1, revision=1)
        self.assertEqual(release.version_id, "1.1-beta.1.1")
        self.assertEqual(release.stage_label, "Beta 1.1")
        self.assertEqual(release.tag, "server-v1.1-beta.1.1")
        self.assertEqual(
            release.iso_filename, "lyra-os-server-1.1-beta.1.1-x86_64.iso"
        )
        self.assertEqual(release.pretty_name, "Lyra OS Server 1.1 Beta 1.1 (Delos)")

    def test_codename_is_shared_with_the_generation(self) -> None:
        release = sample_release()
        self.assertEqual(release.codename, "Delos")
        self.assertIn("Delos", release.pretty_name)

    def test_final_identifiers(self) -> None:
        release = sample_release(stage="release", iteration=0)
        self.assertEqual(release.version_id, "1.1")
        self.assertEqual(release.tag, "server-v1.1")
        self.assertEqual(release.pretty_name, "Lyra OS Server 1.1 (Delos)")

    def test_prerelease_requires_iteration(self) -> None:
        with self.assertRaisesRegex(ValueError, "positive iteration"):
            sample_release(iteration=0)

    def test_final_rejects_iteration(self) -> None:
        with self.assertRaisesRegex(ValueError, "iteration = 0"):
            sample_release(stage="release", iteration=1)

    def test_final_rejects_revision(self) -> None:
        with self.assertRaisesRegex(ValueError, "revision = 0"):
            sample_release(stage="release", iteration=0, revision=1)

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
            self.assertEqual(document["channel_iteration"], 2)
            self.assertEqual(document["channel_revision"], 0)
            self.assertEqual(document["product"], "Lyra OS Server")
            self.assertEqual(document["iso"]["filename"], release.iso_filename)
            self.assertRegex(document["source"]["commit"], r"^[0-9a-f]{40}$")


class ServerBeta1GateTests(unittest.TestCase):
    def test_builder_requires_a_clean_tree_and_valid_iso_source_commit(self) -> None:
        builder = (ROOT / "scripts/build-server-beta1.sh").read_text(encoding="utf-8")
        self.assertIn("python3 ./scripts/image-build.py validate", builder)
        self.assertIn('git cat-file -e "$COMMIT^{commit}"', builder)
        self.assertIn('git rev-parse HEAD', builder)
        self.assertIn("git status --porcelain --untracked-files=normal", builder)

    def test_uploader_requires_signed_bundle_and_open_blocker_query(self) -> None:
        uploader = (ROOT / "scripts/upload-server-beta1-sourceforge.sh").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("--decision-file", uploader)
        self.assertIn("sha256sum -c", uploader)
        self.assertIn('GITHUB_REPOSITORY="lyra-os-linux/lyraos-server"', uploader)
        self.assertIn('GH_REPO="$GITHUB_REPOSITORY" gh issue list', uploader)
        self.assertIn("gh issue list --state open --label server", uploader)
        self.assertIn('test("\\\\[P[01]\\\\]"; "i")', uploader)
        self.assertNotIn("release-decision.json", uploader)

    def test_release_scripts_target_server_1_1_beta_1_1_not_beta_2(self) -> None:
        builder = (ROOT / "scripts/build-server-beta1.sh").read_text(encoding="utf-8")
        uploader = (ROOT / "scripts/upload-server-beta1-sourceforge.sh").read_text(
            encoding="utf-8"
        )
        for script in (builder, uploader):
            self.assertIn("1.1-beta.1.1", script)
            self.assertNotIn("1.1-beta.2", script)
        self.assertIn("/releases/1.1/beta1.1/server/", uploader)
        self.assertIn("lyra-os-server-1.1-beta.1.1.md", builder)

    def test_gate_does_not_require_collectors_missing_from_the_server_image(self) -> None:
        gate = (ROOT / "docs/server-release-gate.md").read_text(encoding="utf-8")
        self.assertIn("não distribui os coletores", gate)
        self.assertIn("systemctl is-active sshd vega-web firewalld NetworkManager", gate)
        self.assertIn("org.lyraos.Vega1.Firewall Status", gate)
        self.assertIn("zona `public`", gate)

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


class ServerRC1GateTests(unittest.TestCase):
    def test_builder_requires_a_clean_tree_and_valid_iso_source_commit(self) -> None:
        builder = (ROOT / "scripts/build-server-rc1.sh").read_text(encoding="utf-8")
        self.assertIn("python3 ./scripts/image-build.py validate", builder)
        self.assertIn('git cat-file -e "$COMMIT^{commit}"', builder)
        self.assertIn('git rev-parse HEAD', builder)
        self.assertIn("git status --porcelain --untracked-files=normal", builder)

    def test_uploader_requires_signed_bundle_and_open_blocker_query(self) -> None:
        uploader = (ROOT / "scripts/upload-server-rc1-sourceforge.sh").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("--decision-file", uploader)
        self.assertIn("sha256sum -c", uploader)
        self.assertIn('GITHUB_REPOSITORY="lyra-os-linux/lyraos-server"', uploader)
        self.assertIn('GH_REPO="$GITHUB_REPOSITORY" gh issue list', uploader)
        self.assertIn("gh issue list --state open --label server", uploader)
        self.assertIn('test("\\\\[P[01]\\\\]"; "i")', uploader)
        self.assertNotIn("release-decision.json", uploader)

    def test_release_scripts_target_server_16_1_rc_1_not_beta(self) -> None:
        builder = (ROOT / "scripts/build-server-rc1.sh").read_text(encoding="utf-8")
        uploader = (ROOT / "scripts/upload-server-rc1-sourceforge.sh").read_text(
            encoding="utf-8"
        )
        for script in (builder, uploader):
            self.assertIn("16.1-rc.1", script)
            self.assertNotIn("1.1-rc.1", script)
            self.assertNotIn("1.1-beta", script)
        self.assertIn("/releases/16.1/rc1/server/", uploader)
        self.assertIn("lyra-os-server-16.1-rc.1.md", builder)

    def test_gate_does_not_require_collectors_missing_from_the_server_image(self) -> None:
        gate = (ROOT / "docs/server-release-gate.md").read_text(encoding="utf-8")
        self.assertIn("não distribui os coletores", gate)
        self.assertIn("systemctl is-active sshd vega-web firewalld NetworkManager", gate)

    def test_release_scripts_pin_the_canonical_signing_key(self) -> None:
        fingerprint = "01B63EEDBE6B079126A0116EFA7353A131ECEFEB"
        builder = (ROOT / "scripts/build-server-rc1.sh").read_text(encoding="utf-8")
        uploader = (ROOT / "scripts/upload-server-rc1-sourceforge.sh").read_text(
            encoding="utf-8"
        )
        for script in (builder, uploader):
            self.assertIn(fingerprint, script)
            self.assertIn("VALIDSIG", script)
            self.assertIn("verify_release_signature", script)
        self.assertIn('--local-user "$RELEASE_SIGNING_FINGERPRINT"', builder)


if __name__ == "__main__":
    unittest.main()


class ServerRCGateTests(unittest.TestCase):
    """The generic RC scripts serve every 16.1 candidate from release-server.toml."""

    def setUp(self) -> None:
        self.builder = (ROOT / "scripts/build-server-rc.sh").read_text(encoding="utf-8")
        self.uploader = (ROOT / "scripts/upload-server-rc-sourceforge.sh").read_text(
            encoding="utf-8"
        )

    def test_scripts_take_the_candidate_from_release_metadata(self) -> None:
        for script in (self.builder, self.uploader):
            self.assertIn("./scripts/server-release.py field release_iteration", script)
            self.assertIn("./scripts/server-release.py field stage", script)
            self.assertIn('[ "$PRODUCT_VERSION" = 16.1 ] && [ "$STAGE" = rc ]', script)
            self.assertNotIn("16.1-rc.1", script)
            self.assertNotIn("1.1-rc.1", script)
            self.assertNotIn("1.1-beta", script)
        self.assertIn('"$REPO_ROOT/docs/releases/lyra-os-server-$VERSION.md"', self.builder)
        self.assertIn("/releases/$PRODUCT_VERSION/rc$ITERATION/server/", self.uploader)
        self.assertIn("releases/$PRODUCT_VERSION/rc$ITERATION/server", self.uploader)

    def test_builder_requires_a_clean_tree_and_valid_iso_source_commit(self) -> None:
        self.assertIn("python3 ./scripts/image-build.py validate", self.builder)
        self.assertIn('git cat-file -e "$COMMIT^{commit}"', self.builder)
        self.assertIn("git rev-parse HEAD", self.builder)
        self.assertIn("git status --porcelain --untracked-files=normal", self.builder)
        self.assertIn('if d.get("version") != sys.argv[2]', self.builder)

    def test_uploader_requires_signed_bundle_of_the_current_candidate(self) -> None:
        self.assertIn("sha256sum -c", self.uploader)
        self.assertIn('GITHUB_REPOSITORY="lyra-os-linux/lyraos-server"', self.uploader)
        self.assertIn('GH_REPO="$GITHUB_REPOSITORY" gh issue list', self.uploader)
        self.assertIn("gh issue list --state open --label server", self.uploader)
        self.assertIn('test("\\\\[P[01]\\\\]"; "i")', self.uploader)
        self.assertIn('if d.get("version") != sys.argv[2]', self.uploader)
        self.assertNotIn("release-decision.json", self.uploader)

    def test_scripts_pin_the_canonical_signing_key(self) -> None:
        fingerprint = "01B63EEDBE6B079126A0116EFA7353A131ECEFEB"
        for script in (self.builder, self.uploader):
            self.assertIn(fingerprint, script)
            self.assertIn("VALIDSIG", script)
            self.assertIn("verify_release_signature", script)
        self.assertIn('--local-user "$RELEASE_SIGNING_FINGERPRINT"', self.builder)

    def test_current_candidate_has_release_notes_and_documented_schedule(self) -> None:
        notes = ROOT / "docs/releases/lyra-os-server-16.1-rc.2.md"
        self.assertTrue(notes.is_file())
        text = notes.read_text(encoding="utf-8")
        self.assertIn("`16.1-rc.2`", text)
        self.assertIn("`server-v16.1-rc.2`", text)
        self.assertIn("vegad 5.1.38", text)
        self.assertIn("vega-cli 5.1.26", text)
        self.assertIn("vega-web 5.1.25", text)
        versioning = (ROOT / "docs/release-versioning.md").read_text(encoding="utf-8")
        self.assertIn("A candidata atual é a RC 2, `16.1-rc.2`", versioning)
        self.assertIn("RC 3 (`16.1-rc.3`): publicada em 05/11/2026", versioning)
        self.assertIn("19/11/2026", versioning)
        gate = (ROOT / "docs/server-release-gate.md").read_text(encoding="utf-8")
        self.assertIn("scripts/build-server-rc.sh", gate)
        self.assertIn("RC 3 (`16.1-rc.3`) é publicada\nem 05/11/2026", gate)

