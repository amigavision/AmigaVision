#!/usr/bin/env python3

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path


IGNORED_NAMES = {".DS_Store", ".gitignore", "pack", "__pycache__"}
SEVENZIP_CANDIDATES = ("7zz", "7z", "7za")
SEVENZIP_COMPRESSION_ARGS = ("-mx=5", "-myx=3")
XZ_PRESET = 6


def parse_args():
    parser = argparse.ArgumentParser(
        description="Package uploadable AmigaVision distro artifacts from built images."
    )
    parser.add_argument(
        "package",
        choices=("all", "mister", "cd32-mister", "emulators", "pi", "amiga"),
        help="Package to build.",
    )
    parser.add_argument("--date-stamp", required=True, help="Release date stamp, e.g. 2025.05.05")
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory to write finished artifacts to.",
    )
    parser.add_argument("--mister-root", default="content/distro")
    parser.add_argument("--cd32-root", default="cd32")
    parser.add_argument("--main-hdf", required=True)
    parser.add_argument("--saves-hdf", required=True)
    parser.add_argument("--listings-dir", required=True)
    parser.add_argument("--shared-dir", required=True)
    parser.add_argument("--pi-script", default="build/pi_image.sh")
    parser.add_argument("--replay-base-img")
    parser.add_argument("--replay-payload-dir", default="replay")
    parser.add_argument("--replay-size", default="16g")
    parser.add_argument("--archive-tool")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def echo(message):
    print(message, flush=True)


def timestamp():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def log_step(message):
    echo(f"[{timestamp()}] {message}")


def format_duration(seconds):
    total = int(round(seconds))
    minutes, seconds = divmod(total, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes}m {seconds}s"
    if minutes:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"


def require_file(path, label):
    if not path.is_file():
        raise FileNotFoundError(f"{label} not found: {path}")


def require_dir(path, label):
    if not path.is_dir():
        raise FileNotFoundError(f"{label} not found: {path}")


def resolve_replay_base_img(path_value):
    path = Path(path_value)
    if path.is_file():
        return path
    if path.is_dir():
        matches = sorted(
            path.glob("RePlayOS*.img"),
            key=lambda candidate: candidate.stat().st_mtime,
            reverse=True,
        )
        if matches:
            return matches[0]
        raise FileNotFoundError(f"No RePlayOS*.img found in {path}")
    raise FileNotFoundError(f"RePlayOS base image not found: {path}")


def find_archive_tool(explicit_tool=None):
    if explicit_tool:
        resolved = shutil.which(explicit_tool)
        if resolved:
            return resolved
        raise FileNotFoundError(f"7z archive tool not found on PATH: {explicit_tool}")
    for candidate in SEVENZIP_CANDIDATES:
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    raise FileNotFoundError("No 7z archive tool found on PATH (tried 7zz, 7z, 7za)")


def find_xz_tool():
    resolved = shutil.which("xz")
    if resolved:
        return resolved
    raise FileNotFoundError("xz compression tool not found on PATH")


def copy_tree_contents(src_root, dest_root):
    dest_root.mkdir(parents=True, exist_ok=True)
    for child in sorted(src_root.iterdir()):
        if child.name in IGNORED_NAMES or child.name.startswith("."):
            continue
        dest = dest_root / child.name
        if child.is_dir():
            shutil.copytree(child, dest, dirs_exist_ok=True)
        else:
            shutil.copy2(child, dest)


def replace_path(src, dest):
    if dest.exists():
        if dest.is_dir() and not dest.is_symlink():
            shutil.rmtree(dest)
        else:
            dest.unlink()
    if src.is_dir():
        shutil.copytree(src, dest)
    else:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)


def archive_7z(output_path, input_root, archive_tool, dry_run=False):
    members = [child.name for child in sorted(input_root.iterdir()) if not child.name.startswith(".")]
    if not members:
        raise RuntimeError(f"Nothing to archive in {input_root}")
    log_step(f"Creating 7z archive {output_path.name}")
    if dry_run:
        echo(f"[dry-run] Would create {output_path} from {input_root}")
        return
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        output_path.unlink()
    cmd = [archive_tool, "a", "-t7z", *SEVENZIP_COMPRESSION_ARGS, "-xr!.*", str(output_path)] + members
    subprocess.run(cmd, cwd=input_root, check=True)


def build_cd32_archive(args, output_path, archive_tool, dry_run=False):
    cd32_root = Path(args.cd32_root)
    require_dir(cd32_root, "CD32 distro root")
    with tempfile.TemporaryDirectory(prefix="amigavision-cd32-") as tmp_dir:
        stage_root = Path(tmp_dir)
        log_step(f"Staging CD32-for-MiSTer payload from {cd32_root}")
        copy_tree_contents(cd32_root, stage_root)
        archive_7z(output_path, stage_root, archive_tool, dry_run=dry_run)


def compress_xz(src_path, dest_path, xz_tool, dry_run=False):
    log_step(f"Compressing {src_path.name} -> {dest_path.name}")
    if dry_run:
        echo(f"[dry-run] Would compress {src_path} -> {dest_path}")
        return
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    if dest_path.exists():
        dest_path.unlink()
    with dest_path.open("wb") as dest:
        subprocess.run(
            [xz_tool, "-T0", f"-{XZ_PRESET}", "-v", "-k", "-c", str(src_path)],
            check=True,
            stdout=dest,
        )


def run_command(cmd, dry_run=False):
    display = " ".join(map(str, cmd))
    log_step(f"Running command: {display}")
    if dry_run:
        echo(f"[dry-run] Would run: {display}")
        return
    subprocess.run(cmd, check=True)


def package_mister(args, output_dir, archive_tool):
    mister_root = Path(args.mister_root)
    main_hdf = Path(args.main_hdf)
    listings_dir = Path(args.listings_dir)
    require_dir(mister_root, "MiSTer distro root")
    require_file(main_hdf, "Main AmigaVision HDF")
    require_dir(listings_dir, "Generated listings directory")

    output_path = output_dir / f"AmigaVision-MiSTer-{args.date_stamp}.7z"
    with tempfile.TemporaryDirectory(prefix="amigavision-mister-") as tmp_dir:
        stage_root = Path(tmp_dir)
        log_step(f"Staging MiSTer payload from {mister_root}")
        copy_tree_contents(mister_root, stage_root)
        log_step("Injecting built AmigaVision.hdf into MiSTer package")
        replace_path(main_hdf, stage_root / "games" / "Amiga" / "AmigaVision.hdf")
        log_step("Injecting generated listings into MiSTer package")
        replace_path(listings_dir, stage_root / "games" / "Amiga" / "listings")
        nested_cd32_name = f"AmigaVision-CD32-Setup-for-MiSTer-{args.date_stamp}.7z"
        log_step(f"Embedding optional CD32 setup archive {nested_cd32_name} into MiSTer package")
        build_cd32_archive(args, stage_root / nested_cd32_name, archive_tool, dry_run=args.dry_run)
        archive_7z(output_path, stage_root, archive_tool, dry_run=args.dry_run)
    return output_path


def package_cd32_mister(args, output_dir, archive_tool):
    output_path = output_dir / f"AmigaVision-CD32-Setup-for-MiSTer-{args.date_stamp}.7z"
    build_cd32_archive(args, output_path, archive_tool, dry_run=args.dry_run)
    return output_path


def package_emulators(args, output_dir, archive_tool):
    main_hdf = Path(args.main_hdf)
    saves_hdf = Path(args.saves_hdf)
    listings_dir = Path(args.listings_dir)
    shared_dir = Path(args.shared_dir)
    require_file(main_hdf, "Main AmigaVision HDF")
    require_file(saves_hdf, "AmigaVision saves HDF")
    require_dir(listings_dir, "Generated listings directory")
    require_dir(shared_dir, "Shared support directory")

    output_path = output_dir / f"AmigaVision-Emulators-{args.date_stamp}.7z"
    with tempfile.TemporaryDirectory(prefix="amigavision-emulators-") as tmp_dir:
        stage_root = Path(tmp_dir) / "AmigaVision"
        stage_root.mkdir(parents=True, exist_ok=True)
        log_step("Staging emulator payload")
        replace_path(main_hdf, stage_root / "AmigaVision.hdf")
        replace_path(saves_hdf, stage_root / "AmigaVision-Saves.hdf")
        replace_path(listings_dir, stage_root / "listings")
        replace_path(shared_dir, stage_root / "shared")
        archive_7z(output_path, Path(tmp_dir), archive_tool, dry_run=args.dry_run)
    return output_path


def package_rpi(args, output_dir, xz_tool):
    pi_script = Path(args.pi_script)
    replay_base = resolve_replay_base_img(args.replay_base_img or "")
    replay_payload_dir = Path(args.replay_payload_dir)
    main_hdf = Path(args.main_hdf)
    require_file(pi_script, "Raspberry Pi packaging script")
    require_dir(replay_payload_dir, "RePlayOS payload directory")
    require_file(main_hdf, "Main AmigaVision HDF")

    raw_output = output_dir / f"AmigaVision-RPi-{args.date_stamp}.img"
    compressed_output = output_dir / f"AmigaVision-RPi-{args.date_stamp}.img.xz"
    log_step(f"Building Raspberry Pi image from RePlayOS base image {replay_base.name}")
    run_command(
        [
            str(pi_script),
            "--base-img",
            str(replay_base),
            "--hdf",
            str(main_hdf),
            "--output-img",
            str(raw_output),
            "--payload-dir",
            str(replay_payload_dir),
            "--size",
            args.replay_size,
        ],
        dry_run=args.dry_run,
    )
    compress_xz(raw_output, compressed_output, xz_tool, dry_run=args.dry_run)
    if not args.dry_run and raw_output.exists():
        log_step(f"Removing intermediate image {raw_output.name}")
        raw_output.unlink()
    return compressed_output


def package_amiga(args, output_dir, xz_tool):
    main_hdf = Path(args.main_hdf)
    require_file(main_hdf, "Main AmigaVision HDF")

    output_path = output_dir / f"AmigaVision-Amiga-{args.date_stamp}.img.xz"
    log_step("Compressing AmigaVision.hdf for real Amiga hardware")
    compress_xz(main_hdf, output_path, xz_tool, dry_run=args.dry_run)
    return output_path


def main():
    args = parse_args()
    output_dir = Path(args.output_dir)
    continue_on_error = args.package == "all"
    packages = (
        ["mister", "cd32-mister", "emulators", "pi", "amiga"]
        if args.package == "all"
        else [args.package]
    )

    archive_tool = None
    if any(package in {"mister", "cd32-mister", "emulators"} for package in packages):
        archive_tool = find_archive_tool(args.archive_tool)
    xz_tool = None
    if any(package in {"pi", "amiga"} for package in packages):
        xz_tool = find_xz_tool()

    log_step(f"Writing artifacts to {output_dir}")
    created = []
    failures = []
    for package in packages:
        started_at = time.time()
        log_step(f"Starting package: {package}")
        try:
            if package == "mister":
                created.append(package_mister(args, output_dir, archive_tool))
            elif package == "cd32-mister":
                created.append(package_cd32_mister(args, output_dir, archive_tool))
            elif package == "emulators":
                created.append(package_emulators(args, output_dir, archive_tool))
            elif package == "pi":
                created.append(package_rpi(args, output_dir, xz_tool))
            elif package == "amiga":
                created.append(package_amiga(args, output_dir, xz_tool))
            else:
                raise AssertionError(f"Unhandled package type: {package}")
            log_step(f"Finished package: {package} in {format_duration(time.time() - started_at)}")
        except Exception as exc:
            duration = format_duration(time.time() - started_at)
            if not continue_on_error:
                raise
            failures.append((package, exc))
            log_step(f"Failed package: {package} after {duration}")
            echo(f"  Reason: {exc}")

    echo("")
    if failures:
        log_step("Packaging completed with some failures")
    else:
        log_step("Packaging complete")
    echo("Artifacts:")
    for artifact in created:
        echo(f"- {artifact}")
    if failures:
        echo("")
        echo("Failed packages:")
        for package, exc in failures:
            echo(f"- {package}: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
