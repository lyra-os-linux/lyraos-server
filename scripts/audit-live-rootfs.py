#!/usr/bin/env python3
"""Fail closed when an extracted Server live rootfs contains build-host data."""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path


HOST_PATH = re.compile(rb"/(?:home|Users)/[A-Za-z0-9._-]+/(?:Git|Projects|src|workspace)/")
SCAN_LIMIT = 8 * 1024 * 1024


def scan(rootfs: Path) -> dict[str, object]:
    if not rootfs.is_dir():
        raise ValueError(f"rootfs does not exist: {rootfs}")
    findings: list[dict[str, str]] = []
    home = rootfs / "home"
    homes = sorted("/home/" + path.name for path in home.iterdir()) if home.is_dir() else []
    for path in homes:
        if path != "/home/liveuser":
            findings.append({"kind": "unexpected-home", "path": path})

    for path in rootfs.rglob("*"):
        relative = "/" + path.relative_to(rootfs).as_posix()
        try:
            if path.is_symlink():
                if HOST_PATH.search(os.readlink(path).encode(errors="replace")):
                    findings.append({"kind": "host-path-symlink", "path": relative})
            elif path.is_file() and path.stat().st_size <= SCAN_LIMIT:
                if HOST_PATH.search(path.read_bytes()):
                    findings.append({"kind": "host-path-content", "path": relative})
        except OSError:
            findings.append({"kind": "unreadable", "path": relative})

    findings.sort(key=lambda item: (item["path"], item["kind"]))
    return {"schema_version": 1, "result": "fail" if findings else "pass", "homes": homes, "findings": findings}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rootfs", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = scan(args.rootfs)
    except ValueError as error:
        parser.error(str(error))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"{report['result']}: {args.rootfs} -> {args.output}")
    return 0 if report["result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
