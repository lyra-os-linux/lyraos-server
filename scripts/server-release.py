#!/usr/bin/env python3
"""Render and verify Lyra OS Server release metadata from release-server.toml."""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import hashlib
import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
RELEASE_FILE = REPOSITORY / "release-server.toml"


@dataclasses.dataclass(frozen=True)
class ServerRelease:
    product_version: str
    base_distribution: str
    base_version: str
    stage: str
    iteration: int
    image_name: str
    architecture: str
    codename: str
    codename_id: str

    @classmethod
    def from_file(cls, path: Path = RELEASE_FILE) -> "ServerRelease":
        with path.open("rb") as stream:
            document = tomllib.load(stream)
        try:
            values = document["release"]
            release = cls(
                product_version=values["version"],
                base_distribution=values["base_distribution"],
                base_version=values["base_version"],
                stage=values["stage"],
                iteration=values.get("iteration", 0),
                image_name=values["image_name"],
                architecture=values["architecture"],
                codename=values["codename"],
                codename_id=values["codename_id"],
            )
        except (KeyError, TypeError) as error:
            raise ValueError(f"invalid server release manifest: missing {error}") from error
        release.validate()
        return release

    def validate(self) -> None:
        scalar_fields = {
            "product_version": self.product_version,
            "base_distribution": self.base_distribution,
            "base_version": self.base_version,
            "stage": self.stage,
            "image_name": self.image_name,
            "architecture": self.architecture,
            "codename": self.codename,
            "codename_id": self.codename_id,
        }
        if any(not isinstance(value, str) for value in scalar_fields.values()):
            raise ValueError("release text fields must be strings")
        if isinstance(self.iteration, bool) or not isinstance(self.iteration, int):
            raise ValueError("iteration must be an integer")
        if not re.fullmatch(r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)(?:\.(?:0|[1-9]\d*))?", self.product_version):
            raise ValueError("version must use MAJOR.MINOR or MAJOR.MINOR.PATCH")
        if self.base_distribution != "opensuse-leap":
            raise ValueError("base_distribution must be opensuse-leap")
        if not re.fullmatch(r"\d+\.\d+", self.base_version):
            raise ValueError("base_version must use MAJOR.MINOR")
        if self.stage not in {"alpha", "beta", "rc", "release"}:
            raise ValueError("stage must be alpha, beta, rc, or release")
        if self.stage == "release" and self.iteration != 0:
            raise ValueError("a final release must use iteration = 0")
        if self.stage != "release" and self.iteration < 1:
            raise ValueError("beta and rc releases require a positive iteration")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*", self.image_name):
            raise ValueError("image_name must be filename-safe")
        if not re.fullmatch(r"[A-Z][A-Za-z0-9-]*", self.codename):
            raise ValueError("codename must be display-safe")
        if not re.fullmatch(r"[a-z][a-z0-9-]*", self.codename_id):
            raise ValueError("codename_id must be machine-safe")
        if not re.fullmatch(r"[A-Za-z0-9_]+", self.architecture):
            raise ValueError("architecture must be machine-safe")

    @property
    def version_id(self) -> str:
        if self.stage == "release":
            return self.product_version
        return f"{self.product_version}-{self.stage}.{self.iteration}"

    @property
    def stage_label(self) -> str:
        if self.stage == "release":
            return "Release"
        prefix = {"alpha": "Alpha", "beta": "Beta", "rc": "RC"}[self.stage]
        return f"{prefix} {self.iteration}"

    @property
    def display_version(self) -> str:
        if self.stage == "release":
            return self.product_version
        return f"{self.product_version} {self.stage_label}"

    @property
    def pretty_name(self) -> str:
        return f"Lyra OS Server {self.display_version} ({self.codename})"

    @property
    def version_name(self) -> str:
        return f"{self.display_version} ({self.codename})"

    @property
    def tag(self) -> str:
        # "server-v..." keeps this product's git tags in a distinct
        # namespace from the desktop's "vYY.MM-stageN" tags.
        return f"server-v{self.version_id}"

    @property
    def volume_id(self) -> str:
        value = f"LYRA_OS_SERVER_{self.version_id}".upper().replace(".", "_").replace("-", "_")
        if len(value) > 32:
            raise ValueError("generated ISO volume ID exceeds 32 characters")
        return value

    @property
    def iso_filename(self) -> str:
        return f"{self.image_name}-{self.version_id}-{self.architecture}.iso"

    @property
    def specification(self) -> str:
        return (
            f"Lyra OS Server {self.display_version} ({self.codename}) - console/installer ISO, "
            f"openSUSE Leap {self.base_version} base, headless, {self.architecture}"
        )

    def fields(self) -> dict[str, str]:
        return {
            "architecture": self.architecture,
            "product_version": self.product_version,
            "base_distribution": self.base_distribution,
            "base_version": self.base_version,
            "codename": self.codename,
            "codename_id": self.codename_id,
            "display_version": self.display_version,
            "image_name": self.image_name,
            "iso_filename": self.iso_filename,
            "pretty_name": self.pretty_name,
            "release_iteration": str(self.iteration),
            "stage": self.stage,
            "stage_label": self.stage_label,
            "tag": self.tag,
            "version_id": self.version_id,
            "volume_id": self.volume_id,
        }


def replace_once(text: str, pattern: str, replacement: str, path: Path) -> str:
    # See scripts/release.py's replace_once for why count= is intentionally
    # omitted: it makes re.subn report the true match count instead of
    # always reporting 1.
    updated, count = re.subn(pattern, lambda _: replacement, text, flags=re.MULTILINE)
    if count != 1:
        raise ValueError(f"expected one release field matching {pattern!r} in {path}")
    return updated


def replace_once_in_block(
    text: str, block_pattern: str, inner_pattern: str, replacement: str, path: Path
) -> str:
    matches = list(re.finditer(block_pattern, text, flags=re.DOTALL))
    if len(matches) != 1:
        raise ValueError(f"expected one block matching {block_pattern!r} in {path}")
    block = matches[0]
    updated_inner = replace_once(block.group(0), inner_pattern, replacement, path)
    return text[: block.start()] + updated_inner + text[block.end() :]


def shell_value(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def release_environment(release: ServerRelease) -> str:
    values = {
        "LYRA_ARCHITECTURE": release.architecture,
        "LYRA_ARTIFACT_VERSION": release.version_id,
        "LYRA_PRODUCT_VERSION": release.product_version,
        "LYRA_BASE_DISTRIBUTION": release.base_distribution,
        "LYRA_BASE_VERSION": release.base_version,
        "LYRA_CODENAME": release.codename,
        "LYRA_CODENAME_ID": release.codename_id,
        "LYRA_DISPLAY_VERSION": release.display_version,
        "LYRA_IMAGE_NAME": release.image_name,
        "LYRA_ISO_FILENAME": release.iso_filename,
        "LYRA_PRETTY_NAME": release.pretty_name,
        "LYRA_RELEASE_STAGE": release.stage,
        "LYRA_RELEASE_ITERATION": str(release.iteration),
        "LYRA_RELEASE_TAG": release.tag,
        "LYRA_STAGE_LABEL": release.stage_label,
        "LYRA_VERSION_ID": release.product_version,
        "LYRA_VERSION_NAME": release.version_name,
        "LYRA_VOLUME_ID": release.volume_id,
    }
    lines = [
        "# Generated by scripts/server-release.py from release-server.toml; do not edit.",
        *(f"{key}={shell_value(value)}" for key, value in values.items()),
        "",
    ]
    return "\n".join(lines)


def render_files(release: ServerRelease) -> dict[Path, str]:
    rendered: dict[Path, str] = {}

    xml_path = REPOSITORY / "kiwi/config.xml"
    xml = xml_path.read_text(encoding="utf-8")
    # kiwi/config.xml has a single <preferences> block in this repo (no more
    # per-profile split - see docs/server-edition.md's 2026-08-23 note), so
    # <version>/volid are each unique file-wide.
    xml = replace_once(
        xml,
        r"^[ \t]*<version>[^<]+</version>$",
        f"    <version>{release.version_id}</version>",
        xml_path,
    )
    xml = replace_once(
        xml,
        r'volid="[^"]+"',
        f'volid="{release.volume_id}"',
        xml_path,
    )
    xml = replace_once(
        xml,
        r"^[ \t]*<specification>[^<]+</specification>$",
        f"    <specification>{release.specification}</specification>",
        xml_path,
    )
    rendered[xml_path] = xml

    # kiwi/root/ is the (only) overlay directory KIWI applies on top of the
    # installed packages; kiwi/config.sh sources this path directly.
    rendered[REPOSITORY / "kiwi/root/usr/lib/lyra-os/server-release"] = release_environment(
        release
    )
    return rendered


def render(release: ServerRelease, check: bool) -> int:
    stale: list[Path] = []
    for path, expected in render_files(release).items():
        actual = path.read_text(encoding="utf-8") if path.exists() else None
        if actual == expected:
            continue
        stale.append(path)
        if not check:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(expected, encoding="utf-8")

    if stale and check:
        for path in stale:
            print(f"stale server release metadata: {path.relative_to(REPOSITORY)}", file=sys.stderr)
        print("run ./scripts/server-release.py render", file=sys.stderr)
        return 1
    if stale:
        for path in stale:
            print(f"rendered {path.relative_to(REPOSITORY)}")
    else:
        print("server release metadata is up to date")
    return 0


def git_output(*arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=REPOSITORY,
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    )
    return result.stdout.strip()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_build_manifest(release: ServerRelease, iso: Path, output: Path | None) -> int:
    iso = iso.resolve()
    if not iso.is_file():
        raise ValueError(f"ISO does not exist: {iso}")
    if iso.name != release.iso_filename:
        raise ValueError(f"expected ISO name {release.iso_filename}, got {iso.name}")
    output = output or Path(f"{iso}.manifest.json")
    dirty = bool(git_output("status", "--porcelain", "--untracked-files=normal"))
    document = {
        "schema_version": 1,
        "product": "Lyra OS Server",
        "version": release.version_id,
        "product_version": release.product_version,
        "base_distribution": release.base_distribution,
        "base_version": release.base_version,
        "channel": release.stage,
        "channel_iteration": release.iteration,
        "architecture": release.architecture,
        "release_tag": release.tag,
        "built_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "source": {
            "commit": git_output("rev-parse", "HEAD"),
            "dirty": dirty,
        },
        "iso": {
            "filename": iso.name,
            "size_bytes": iso.stat().st_size,
            "sha256": sha256(iso),
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.new")
    temporary.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(output)
    print(output)
    return 0


def parser() -> argparse.ArgumentParser:
    cli = argparse.ArgumentParser(description=__doc__)
    commands = cli.add_subparsers(dest="command", required=True)
    commands.add_parser("check", help="fail if generated server release metadata is stale")
    commands.add_parser("render", help="update generated server release metadata")
    field = commands.add_parser("field", help="print one derived server release field")
    field.add_argument("name")
    manifest = commands.add_parser("build-manifest", help="write traceability metadata for a server ISO")
    manifest.add_argument("--iso", required=True, type=Path)
    manifest.add_argument("--output", type=Path)
    return cli


def main() -> int:
    args = parser().parse_args()
    try:
        release = ServerRelease.from_file()
        if args.command == "check":
            return render(release, check=True)
        if args.command == "render":
            return render(release, check=False)
        if args.command == "field":
            fields = release.fields()
            if args.name not in fields:
                raise ValueError(f"unknown field {args.name}; choose from: {', '.join(sorted(fields))}")
            print(fields[args.name])
            return 0
        return write_build_manifest(release, args.iso, args.output)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"server release metadata error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
