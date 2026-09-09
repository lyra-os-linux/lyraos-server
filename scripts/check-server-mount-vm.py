#!/usr/bin/env python3
"""Qualify the shipped Server worker with real mounts on disposable QEMU disks."""
import argparse
import gzip
from pathlib import Path
import re
import shutil
import subprocess
import sys
import sysconfig
import tempfile

REPO = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kernel", type=Path, required=True)
    parser.add_argument("--modules-dir", type=Path, required=True)
    parser.add_argument("--log", type=Path, required=True)
    args = parser.parse_args()
    if not args.kernel.is_file() or not args.modules_dir.is_dir():
        parser.error("readable kernel and matching modules directory required")
    with tempfile.TemporaryDirectory(prefix="lyra-server-mount-vm-") as directory:
        base = Path(directory)
        root = base / "root"
        for name in ("usr/bin", "dev", "proc", "sys", "tmp", "run/udev", "etc", "test/scripts", "test/tests"):
            (root / name).mkdir(parents=True)
        (root / "bin").symlink_to("usr/bin")
        (root / "sbin").symlink_to("usr/bin")
        (root / "usr/sbin").symlink_to("bin")
        if Path("/etc/ld.so.cache").is_file():
            shutil.copyfile("/etc/ld.so.cache", root / "etc/ld.so.cache")

        def copy(source, destination):
            target = root / str(destination).lstrip("/")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            target.chmod(0o755)

        def binary(source, destination):
            copy(source, destination)
            linked = subprocess.check_output(["ldd", str(source)], text=True)
            for library in re.findall(r"(?:=>\s+|^\s*)(/[^\s]+)", linked, re.M):
                copy(library, library)
                if "/glibc-hwcaps/" in library:
                    dynamic = subprocess.check_output(["readelf", "-d", library], text=True)
                    soname = re.search(r"\(SONAME\).*\[([^]]+)\]", dynamic)
                    if soname:
                        baseline = Path(library.split("/glibc-hwcaps/")[0]) / soname[1]
                        copy(baseline, baseline)

        for name in ("bash", "mount", "umount", "mountpoint", "mkdir", "rmdir", "rm", "cat", "date", "cut",
                     "sleep", "tar", "modprobe", "mkfs.ext4", "mkfs.fat", "systemctl"):
            source = shutil.which(name)
            if not source:
                parser.error("missing VM tool: " + name)
            binary(source, "/usr/bin/" + name)
        (root / "usr/bin/sh").symlink_to("bash")
        binary(sys.executable, "/usr/bin/python3")
        stdlib = Path(sysconfig.get_path("stdlib"))
        destination = root / str(stdlib).lstrip("/")
        shutil.copytree(stdlib, destination, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("__pycache__", "site-packages", "dist-packages", "test", "tests",
                                                      "ensurepip", "idlelib", "tkinter", "turtledemo"))
        # Native extension imports need their linked libraries too.
        for extension in stdlib.glob("lib-dynload/*.so"):
            binary(extension, extension)
        copy("/usr/share/zoneinfo/UTC", "/usr/share/zoneinfo/UTC")
        copy(REPO / "scripts/server-install.sh", "/test/scripts/server-install.sh")
        copy(REPO / "tests/test_server_mount_cleanup.py", "/test/tests/test_server_mount_cleanup.py")
        module_root = root / "usr/lib/modules" / args.modules_dir.name
        module_root.mkdir(parents=True)
        (root / "lib").mkdir(exist_ok=True)
        (root / "lib/modules").symlink_to("../usr/lib/modules")
        for source in args.modules_dir.glob("modules.*"):
            shutil.copyfile(source, module_root / source.name)
        for name in ("ext4", "vfat", "nls_cp437", "nls_iso8859-1", "nls_ascii", "nls_utf8", "virtio_blk", "virtio_pci"):
            # Resolve/copy dependencies on the host; load only in the guest.
            dependencies = subprocess.check_output(["modprobe", "--show-depends", "-S", args.modules_dir.name, name], text=True)
            for line in dependencies.splitlines():
                if line.startswith("insmod "):
                    source = Path(line.split()[1])
                    relative = source.resolve().relative_to(args.modules_dir.resolve())
                    target = module_root / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, target)
        init = root / "init"
        init.write_text('''#!/bin/bash
export PATH=/usr/bin:/bin
export PYTHONDONTWRITEBYTECODE=1
mount -t proc proc /proc || exit 1
mount -t sysfs sysfs /sys || exit 1
mount -t devtmpfs devtmpfs /dev || exit 1
mkdir -p /dev/pts
mount -t devpts devpts /dev/pts || exit 1
modprobe ext4 || exit 1
modprobe vfat || exit 1
modprobe nls_cp437 || exit 1
modprobe nls_iso8859-1 || exit 1
modprobe virtio_pci || exit 1
modprobe virtio_blk || exit 1
export LYRA_SERVER_CLEANUP_VM=1
python3 /test/tests/test_server_mount_cleanup.py -v
result=$?
echo "LYRA_SERVER_MOUNT_VM_EXIT=$result"
systemctl --force --force poweroff
''')
        init.chmod(0o755)
        files = b"\0".join(str(path.relative_to(root)).encode() for path in root.rglob("*")) + b"\0"
        archive = subprocess.run(["cpio", "--null", "-o", "-H", "newc", "--owner=0:0", "--quiet"],
                                 input=files, cwd=root, capture_output=True, check=True)
        initrd = base / "initramfs.cpio.gz"
        with gzip.open(initrd, "wb", compresslevel=1) as stream:
            stream.write(archive.stdout)
        drives = []
        for name, serial, size in (("root", "lyra-srv-root-test", 256), ("esp", "lyra-srv-esp-test", 128)):
            disk = base / (name + ".raw")
            with disk.open("wb") as stream:
                stream.truncate(size * 1024 * 1024)
            drives += ["-drive", f"file={disk},format=raw,if=none,id={name}",
                       "-device", f"virtio-blk-pci,drive={name},serial={serial}"]
        args.log.parent.mkdir(parents=True, exist_ok=True)
        with args.log.open("w") as log:
            result = subprocess.run([
                "qemu-system-x86_64", "-accel", "tcg", "-cpu", "max", "-smp", "2", "-m", "1536",
                "-kernel", str(args.kernel.resolve()), "-initrd", str(initrd),
                "-append", "rdinit=/init console=ttyS0 quiet panic=1 lyra.server-cleanup-test=1",
                *drives, "-display", "none", "-serial", "stdio", "-monitor", "none", "-nic", "none", "-no-reboot",
            ], stdout=log, stderr=subprocess.STDOUT, timeout=300)
        content = args.log.read_text(errors="replace")
        print(content[-12000:])
        if result.returncode or "LYRA_SERVER_MOUNT_VM_EXIT=0" not in content or "\nOK\n" not in content:
            raise SystemExit("VM failed: " + str(args.log))
        print("PASS: Server cleanup on disposable ext4/FAT disks; evidence: " + str(args.log))


if __name__ == "__main__":
    main()
