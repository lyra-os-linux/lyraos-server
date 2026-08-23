from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("lyra_image_build", ROOT / "scripts/image-build.py")
assert SPEC and SPEC.loader
image_build = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = image_build
SPEC.loader.exec_module(image_build)


class ImagePolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = image_build.Manifest.load()

    def test_recovery_editors_are_available(self) -> None:
        root = ET.parse(ROOT / "kiwi/config.xml").getroot()
        packages = {node.attrib["name"] for node in root.findall("packages/package")}
        self.assertTrue({"vim", "neovim", "nano"}.issubset(packages))

    def test_man_is_available(self) -> None:
        root = ET.parse(ROOT / "kiwi/config.xml").getroot()
        packages = {node.attrib["name"] for node in root.findall("packages/package")}
        self.assertIn("man", packages)

    def test_vega_headless_components_are_installed(self) -> None:
        root = ET.parse(ROOT / "kiwi/config.xml").getroot()
        packages = {node.attrib["name"] for node in root.findall("packages/package")}
        self.assertTrue({"vega-cli", "vegad", "vega-web", "openssh"}.issubset(packages))
        self.assertNotIn("vega-gtk", packages)

    def test_zypper_cache_policy_matches_vega_update_flow(self) -> None:
        config = (
            ROOT / "kiwi/root/etc/zypp/zypp.conf.d/90-lyra-refresh.conf"
        ).read_text(encoding="utf-8")
        self.assertIn("repo.refresh.delay = 2880", config)
        self.assertIn("download.max_concurrent_connections = 5", config)
        self.assertIn("download.use_deltarpm = false", config)

    def test_zram_is_configured(self) -> None:
        config = (ROOT / "kiwi/root/etc/systemd/zram-generator.conf").read_text(
            encoding="utf-8"
        )
        self.assertIn("[zram0]", config)
        self.assertIn("compression-algorithm = zstd", config)

    def test_canonical_sources_pass_repository_and_signature_policy(self) -> None:
        image_build.validate_sources(self.manifest)

    def test_obs_is_restricted_to_ordered_rpm_package_sources(self) -> None:
        self.assertEqual(self.manifest.obs_role, "packages-only")
        projects = [source.project for source in self.manifest.package_sources]
        self.assertEqual(projects, ["home:rodrigosbrito:lyra", "home:rodrigosbrito:vega"])
        self.assertFalse(hasattr(self.manifest, "project"))
        self.assertFalse(hasattr(self.manifest, "package"))

    def test_distribution_policy_uses_github_and_sourceforge(self) -> None:
        self.assertEqual(
            self.manifest.source_repository, "https://github.com/britors/lyra-os-server"
        )
        self.assertEqual(self.manifest.iso_provider, "sourceforge")
        help_text = image_build.parser().format_help()
        self.assertNotIn("publish", help_text)
        self.assertNotIn("check-remote", help_text)

    def test_manifest_rejects_an_obs_image_publication_target(self) -> None:
        source = (ROOT / "image-build-server.toml").read_text(encoding="utf-8")
        source = source.replace(
            'role = "packages-only"',
            'project = "home:rodrigosbrito:lyra:images"\nrole = "packages-only"',
        )
        with tempfile.TemporaryDirectory() as temporary:
            manifest = Path(temporary) / "image-build-server.toml"
            manifest.write_text(source, encoding="utf-8")
            with self.assertRaisesRegex(image_build.PolicyError, "publication targets"):
                image_build.Manifest.load(manifest)

    def test_live_module_is_part_of_the_installed_image(self) -> None:
        root = ET.parse(ROOT / "kiwi/config.xml").getroot()
        image_packages = root.find("packages[@type='image']")
        assert image_packages is not None
        self.assertIsNotNone(image_packages.find("package[@name='dracut-kiwi-live']"))
        self.assertIsNone(root.find("packages[@type='iso']/package[@name='dracut-kiwi-live']"))

    def test_repositories_are_exactly_four_and_all_https(self) -> None:
        root = ET.parse(ROOT / "kiwi/config.xml").getroot()
        repositories = root.findall("repository")
        aliases = {repo.attrib["alias"] for repo in repositories}
        self.assertEqual(aliases, {"repo-oss", "repo-non-oss", "repo-lyra", "repo-vega"})
        for repository in repositories:
            source = repository.find("source")
            self.assertIsNotNone(source)
            assert source is not None
            self.assertTrue(source.attrib["path"].startswith("https://"))

    def test_no_gnome_or_desktop_only_packages_are_installed(self) -> None:
        root = ET.parse(ROOT / "kiwi/config.xml").getroot()
        packages = {node.attrib["name"] for node in root.findall("packages/package")}
        for desktop_only in (
            "gnome-shell",
            "lyra-installer",
            "lyra-upgrade",
            "lyra-welcome",
            "lyra-os-theme",
            "fish",
            "flatpak",
            "btrfsprogs",
            "snapper",
        ):
            self.assertNotIn(desktop_only, packages)
        self.assertIsNone(root.find("namedCollection[@name='gnome']"))


class ExportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = image_build.Manifest.load()

    def test_export_is_derived_from_canonical_kiwi_without_duplicate_package_list(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "export"
            real_git = image_build.git
            with mock.patch.object(
                image_build,
                "git",
                side_effect=lambda *args: "" if args[0] == "status" else real_git(*args),
            ):
                image_build.export(self.manifest, destination, "HEAD", allow_dirty=False)
            image_build.verify_export(self.manifest, destination)
            canonical = ET.parse(ROOT / "kiwi/config.xml").getroot()
            exported = ET.parse(destination / self.manifest.description).getroot()
            canonical_packages = [node.attrib["name"] for node in canonical.findall("packages/package")]
            exported_packages = [node.attrib["name"] for node in exported.findall("packages/package")]
            self.assertEqual(exported_packages, canonical_packages)
            self.assertFalse((destination / "_multibuild").exists())
            self.assertEqual(
                image_build.sha256(
                    destination / "keys/obs-package-signing-keyring.asc"
                ),
                image_build.sha256(image_build.PACKAGE_SIGNING_KEYRING),
            )
            self.assertEqual(
                image_build.sha256(destination / "config.xml"),
                image_build.sha256(ROOT / "kiwi/config.xml"),
            )
            source = json.loads((destination / "build-source.json").read_text(encoding="utf-8"))
            self.assertRegex(source["commit"], r"^[0-9a-f]{40}$")
            self.assertFalse(source["dirty"])
            self.assertTrue((destination / "root.tar.gz").is_file())

    def test_root_archive_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            first = Path(temporary) / "first"
            second = Path(temporary) / "second"
            real_git = image_build.git
            with mock.patch.object(
                image_build,
                "git",
                side_effect=lambda *args: "" if args[0] == "status" else real_git(*args),
            ):
                image_build.export(self.manifest, first, "HEAD", allow_dirty=False)
                image_build.export(self.manifest, second, "HEAD", allow_dirty=False)
            self.assertEqual(
                image_build.sha256(first / "root.tar.gz"),
                image_build.sha256(second / "root.tar.gz"),
            )

    def test_export_refuses_nonempty_destination(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary)
            (destination / "existing").write_text("keep", encoding="utf-8")
            with self.assertRaisesRegex(image_build.PolicyError, "not empty"):
                image_build.export(self.manifest, destination, "HEAD", allow_dirty=True)

    def test_dirty_inspection_export_cannot_pass_verification(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "export"
            real_git = image_build.git
            with mock.patch.object(
                image_build,
                "git",
                side_effect=lambda *args: " M kiwi/config.xml" if args[0] == "status" else real_git(*args),
            ):
                image_build.export(self.manifest, destination, "HEAD", allow_dirty=True)
            with self.assertRaisesRegex(image_build.PolicyError, "source identity"):
                image_build.verify_export(self.manifest, destination)


class ArtifactTests(unittest.TestCase):
    def create_artifacts(self, directory: Path) -> None:
        (directory / "lyra.iso").write_bytes(b"iso")
        (directory / "lyra.packages").write_text(
            "vega-cli|(none)|1.2.0|3.1|x86_64|obs://build.opensuse.org/"
            "home:rodrigosbrito:vega/repo/revision-vega-cli|MIT\n",
            encoding="utf-8",
        )
        (directory / "lyra.verified").write_text("verified\n", encoding="utf-8")
        (directory / "lyra.report").write_text("<report/>\n", encoding="utf-8")
        (directory / "lyra.iso.sha256").write_text(
            "checksum  lyra.iso\n", encoding="utf-8"
        )
        (directory / "lyra.iso.sha256.asc").write_text(
            "signature\n", encoding="utf-8"
        )
        (directory / "lyra.cdx.json").write_text("{}\n", encoding="utf-8")
        (directory / "lyra.spdx.json").write_text("{}\n", encoding="utf-8")

    def create_test_results(
        self, manifest: image_build.Manifest, directory: Path
    ) -> list[str]:
        results = []
        for name in manifest.required_test_results:
            path = directory / f"{name}.json"
            if name == "obs-repositories":
                document = {
                    "schema": 1,
                    "status": "passed",
                    "projects": [{"packages": ["vega-cli"], "targets": ["Leap"]}],
                }
            elif name == "hardware-matrix":
                document = {
                    "schema": 1,
                    "status": "passed",
                    "mode": "hardware-matrix",
                    "iso": {
                        "filename": "lyra.iso",
                        "sha256": image_build.sha256(directory / "lyra.iso"),
                    },
                    "coverage": {
                        "desktops": 1,
                        "notebooks": 2,
                        "cpu_vendors": ["amd", "intel"],
                        "gpu_vendors": ["amd", "intel"],
                    },
                    "scenarios": [{"machine": str(index)} for index in range(3)],
                }
            else:
                modes = {
                    "live-session": "live-session",
                    "installer": "installer",
                    "first-boot": "first-boot",
                    "uefi-secure-boot": "uefi-secure-boot",
                }
                document = {
                    "schema": 1,
                    "status": "passed",
                    "mode": modes[name],
                    "checks": [{"id": "fixture", "status": "passed"}],
                }
            path.write_text(json.dumps(document) + "\n", encoding="utf-8")
            results.append(f"{name}={path}")
        return results

    def test_manifest_hashes_all_evidence_and_records_exact_package_sources(self) -> None:
        manifest = image_build.Manifest.load()
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            self.create_artifacts(directory)
            output = directory / "manifest.json"
            tests = self.create_test_results(manifest, directory)
            real_git = image_build.git
            with mock.patch.object(
                image_build,
                "git",
                side_effect=lambda *args: "" if args[0] == "status" else real_git(*args),
            ):
                image_build.artifact_manifest(manifest, directory, output, tests)
            document = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(
                set(document["artifacts"]),
                set(image_build.required_artifact_roles(manifest, image_build.RELEASE)),
            )
            # release-server.toml's current stage is "beta" (not "alpha"),
            # so a detached checksum signature is required and present.
            self.assertIn("checksum_signature", document["artifacts"])
            self.assertEqual(document["packages"][0]["license"], "MIT")
            self.assertIn("revision-vega-cli", document["packages"][0]["source"])
            self.assertEqual(
                set(document["test_results"]), set(manifest.required_test_results)
            )
            self.assertFalse(document["source"]["dirty"])

    def test_alpha_manifest_accepts_checksum_without_detached_signature(self) -> None:
        manifest = image_build.Manifest.load()
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            self.create_artifacts(directory)
            (directory / "lyra.iso.sha256.asc").unlink()
            output = directory / "manifest.json"
            tests = self.create_test_results(manifest, directory)
            real_release_values = image_build.release_values

            def alpha_release(path: Path = image_build.RELEASE) -> dict[str, object]:
                values = real_release_values(path)
                return {**values, "stage": "alpha", "iteration": 1}

            real_git = image_build.git
            with mock.patch.object(image_build, "release_values", side_effect=alpha_release), \
                mock.patch.object(
                    image_build,
                    "git",
                    side_effect=lambda *args: "" if args[0] == "status" else real_git(*args),
                ):
                image_build.artifact_manifest(manifest, directory, output, tests)
            document = json.loads(output.read_text(encoding="utf-8"))
            self.assertNotIn("checksum_signature", document["artifacts"])

    def test_beta_manifest_rejects_missing_detached_signature(self) -> None:
        manifest = image_build.Manifest.load()
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            self.create_artifacts(directory)
            (directory / "lyra.iso.sha256.asc").unlink()
            output = directory / "manifest.json"
            tests = self.create_test_results(manifest, directory)
            with self.assertRaisesRegex(
                image_build.PolicyError, "checksum signature.*found 0"
            ):
                image_build.artifact_manifest(manifest, directory, output, tests)

    def test_manifest_rejects_missing_or_failed_release_evidence(self) -> None:
        manifest = image_build.Manifest.load()
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            self.create_artifacts(directory)
            failed = directory / "obs.json"
            failed.write_text('{"schema":1,"status":"failed"}\n', encoding="utf-8")
            with self.assertRaisesRegex(image_build.PolicyError, "did not pass"):
                image_build.artifact_manifest(
                    manifest,
                    directory,
                    directory / "manifest.json",
                    [f"obs-repositories={failed}"],
                )

    def test_hardware_matrix_with_a_single_machine_still_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            iso = Path(temporary) / "lyra.iso"
            iso.write_bytes(b"iso payload")
            result = image_build.validate_test_result(
                "hardware-matrix",
                {
                    "schema": 1,
                    "status": "passed",
                    "mode": "hardware-matrix",
                    "iso": {
                        "filename": iso.name,
                        "sha256": image_build.sha256(iso),
                    },
                    "coverage": {
                        "desktops": 1,
                        "notebooks": 0,
                        "cpu_vendors": ["amd"],
                        "gpu_vendors": ["amd"],
                        "gap": ["notebooks<2", "cpu:intel", "gpu:intel"],
                    },
                    "scenarios": [{"machine": "only-physical-machine"}],
                },
                iso_path=iso,
            )
            self.assertEqual(result["coverage"]["gap"], ["notebooks<2", "cpu:intel", "gpu:intel"])

    def test_manifest_rejects_empty_passed_or_mislabeled_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            self.create_artifacts(directory)
            empty = directory / "empty.json"
            empty.write_text('{"schema":1,"status":"passed"}\n', encoding="utf-8")
            with self.assertRaisesRegex(image_build.PolicyError, "mode"):
                image_build.validate_test_result(
                    "first-boot",
                    json.loads(empty.read_text(encoding="utf-8")),
                    iso_path=directory / "lyra.iso",
                )


if __name__ == "__main__":
    unittest.main()
