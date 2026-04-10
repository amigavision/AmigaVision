#!/usr/bin/env python3

import argparse
import errno
import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
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
    parser.add_argument("--rom-file", required=True)
    parser.add_argument("--listings-dir", required=True)
    parser.add_argument("--shared-dir", required=True)
    parser.add_argument("--visuals-dir", required=True)
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


def clone_or_copy_file(src, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    clonefile = getattr(os, "clonefile", None)
    if clonefile is not None:
        try:
            clonefile(src, dest)
            shutil.copystat(src, dest, follow_symlinks=True)
            return
        except OSError as exc:
            if exc.errno not in {
                errno.EXDEV,
                errno.ENOTSUP,
                errno.EPERM,
                errno.EACCES,
                errno.ENOSYS,
                errno.EINVAL,
            }:
                raise
    shutil.copy2(src, dest)


def clone_or_copy_tree(src, dest, dirs_exist_ok=False):
    shutil.copytree(src, dest, dirs_exist_ok=dirs_exist_ok, copy_function=clone_or_copy_file)


def copy_tree_contents(src_root, dest_root):
    dest_root.mkdir(parents=True, exist_ok=True)
    for child in sorted(src_root.iterdir()):
        if child.name in IGNORED_NAMES or child.name.startswith("."):
            continue
        dest = dest_root / child.name
        if child.is_dir():
            clone_or_copy_tree(child, dest, dirs_exist_ok=True)
        else:
            clone_or_copy_file(child, dest)


def replace_path(src, dest):
    if dest.exists():
        if dest.is_dir() and not dest.is_symlink():
            shutil.rmtree(dest)
        else:
            dest.unlink()
    if src.is_dir():
        clone_or_copy_tree(src, dest)
    else:
        clone_or_copy_file(src, dest)


def make_stage_dir(parent, prefix, dry_run=False):
    if dry_run:
        return tempfile.TemporaryDirectory(prefix=prefix)
    return tempfile.TemporaryDirectory(prefix=prefix, dir=parent)


def write_text(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def ensure_dir(path):
    path.mkdir(parents=True, exist_ok=True)


def make_amiberry_skeleton(stage_root):
    for relative in (
        "Configurations",
        "conf",
        "Harddrives",
        "Roms",
        "Visuals/Shaders",
    ):
        ensure_dir(stage_root / relative)


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


def build_cd32_release(args, output_path, dry_run=False):
    cd32_root = Path(args.cd32_root)
    require_dir(cd32_root, "CD32 distro root")
    generator = cd32_root / "make_cd32_mgl_cfg.py"
    pack_script = cd32_root / "pack"
    require_file(generator, "CD32 config generator")
    require_file(pack_script, "CD32 pack script")

    log_step("Generating CD32 preset variants")
    run_command([sys.executable, str(generator)], dry_run=dry_run)

    if not dry_run and output_path.exists():
        output_path.unlink()

    log_step("Packing CD32 release archive")
    run_command(["bash", str(pack_script), args.date_stamp, str(output_path)], dry_run=dry_run)
    if not dry_run:
        require_file(output_path, "Generated CD32 distro archive")
    return output_path


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


def list_archive_contents(artifact_path, archive_tool=None, xz_tool=None, dry_run=False):
    suffixes = artifact_path.suffixes
    log_step(f"Listing contents of {artifact_path.name}")
    if dry_run:
        echo(f"[dry-run] Would list contents of {artifact_path}")
        return

    if suffixes and suffixes[-1] == ".7z":
        if not archive_tool:
            raise FileNotFoundError(f"No 7z archive tool available to list {artifact_path}")
        run_command([archive_tool, "l", str(artifact_path)])
        return

    if suffixes and suffixes[-1] == ".zip":
        with zipfile.ZipFile(artifact_path) as archive:
            for info in archive.infolist():
                echo(f"{info.file_size:>10}  {info.filename}")
        return

    if suffixes[-2:] == [".img", ".xz"]:
        listing_tool = archive_tool
        if not listing_tool:
            for candidate in SEVENZIP_CANDIDATES:
                resolved = shutil.which(candidate)
                if resolved:
                    listing_tool = resolved
                    break
        if listing_tool:
            run_command([listing_tool, "l", str(artifact_path)])
            return
        if xz_tool:
            run_command([xz_tool, "-lv", str(artifact_path)])
            return
        raise FileNotFoundError(f"No archive tool available to list {artifact_path}")

    raise ValueError(f"Unsupported artifact type for listing: {artifact_path}")


def package_mister(args, output_dir, archive_tool, cd32_release_path):
    mister_root = Path(args.mister_root)
    main_hdf = Path(args.main_hdf)
    listings_dir = Path(args.listings_dir)
    require_dir(mister_root, "MiSTer distro root")
    require_file(main_hdf, "Main AmigaVision HDF")
    require_dir(listings_dir, "Generated listings directory")

    output_path = output_dir / f"AmigaVision-MiSTer-{args.date_stamp}.7z"
    with make_stage_dir(output_dir, prefix="amigavision-mister-", dry_run=args.dry_run) as tmp_dir:
        stage_root = Path(tmp_dir)
        log_step(f"Staging MiSTer payload from {mister_root}")
        copy_tree_contents(mister_root, stage_root)
        log_step("Injecting built AmigaVision.hdf into MiSTer package")
        replace_path(main_hdf, stage_root / "games" / "Amiga" / "AmigaVision.hdf")
        log_step("Injecting generated listings into MiSTer package")
        replace_path(listings_dir, stage_root / "games" / "Amiga" / "listings")
        nested_cd32_name = f"AmigaVision-CD32-MiSTer-{args.date_stamp}.zip"
        log_step(f"Embedding optional CD32 setup archive {nested_cd32_name} into MiSTer package")
        if args.dry_run:
            echo(f"[dry-run] Would embed {cd32_release_path} as {stage_root / nested_cd32_name}")
        else:
            replace_path(cd32_release_path, stage_root / nested_cd32_name)
        archive_7z(output_path, stage_root, archive_tool, dry_run=args.dry_run)
    return output_path


def package_cd32_mister(args, output_dir, cd32_release_path):
    output_path = output_dir / f"!AmigaVision-CD32-MiSTer-{args.date_stamp}.zip"
    if Path(cd32_release_path) == output_path:
        log_step(f"Using prebuilt CD32 release archive {output_path}")
        return output_path
    log_step(f"Copying CD32 release archive to {output_path}")
    if args.dry_run:
        echo(f"[dry-run] Would copy {cd32_release_path} -> {output_path}")
    else:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        clone_or_copy_file(cd32_release_path, output_path)
    return output_path


def package_emulators(args, output_dir, archive_tool):
    main_hdf = Path(args.main_hdf)
    saves_hdf = Path(args.saves_hdf)
    rom_file = Path(args.rom_file)
    listings_dir = Path(args.listings_dir)
    shared_dir = Path(args.shared_dir)
    visuals_root = Path(args.visuals_dir)
    launcher_template = Path("content/distro/games/Amiga/default.uae")
    require_file(main_hdf, "Main AmigaVision HDF")
    require_file(saves_hdf, "AmigaVision saves HDF")
    require_file(rom_file, "AmigaVision ROM")
    require_dir(listings_dir, "Generated listings directory")
    require_dir(shared_dir, "Shared support directory")
    require_dir(visuals_root, "AmigaVision Visuals payload")
    require_file(launcher_template, "Amiberry launcher template")

    output_path = output_dir / f"AmigaVision-Emulators-{args.date_stamp}.7z"
    with make_stage_dir(output_dir, prefix="amigavision-emulators-", dry_run=args.dry_run) as tmp_dir:
        stage_root = Path(tmp_dir) / "Amiberry"
        make_amiberry_skeleton(stage_root)
        harddrives_root = stage_root / "Harddrives"
        roms_root = stage_root / "Roms"
        conf_root = stage_root / "conf"
        mac_conf_root = stage_root / "Configurations"
        log_step("Staging reusable Amiberry payload")
        replace_path(main_hdf, harddrives_root / "AmigaVision.hdf")
        replace_path(saves_hdf, harddrives_root / "AmigaVision-Saves.hdf")
        replace_path(rom_file, roms_root / "AmigaVision.rom")
        replace_path(shared_dir, harddrives_root / "Shared")
        replace_path(listings_dir, harddrives_root / "listings")
        replace_path(visuals_root, stage_root / "Visuals")
        replace_path(launcher_template, conf_root / "default.uae")
        replace_path(launcher_template, mac_conf_root / "default.uae")
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
    output_dir.mkdir(parents=True, exist_ok=True)
    continue_on_error = args.package == "all"
    packages = (
        ["mister", "cd32-mister", "emulators", "pi", "amiga"]
        if args.package == "all"
        else [args.package]
    )

    archive_tool = None
    if any(package in {"mister", "emulators"} for package in packages):
        archive_tool = find_archive_tool(args.archive_tool)
    xz_tool = None
    if any(package in {"pi", "amiga"} for package in packages):
        xz_tool = find_xz_tool()

    log_step(f"Writing artifacts to {output_dir}")
    created = []
    failures = []
    cd32_release_state = {"artifact": None, "error": None, "temp_dir": None}
    for package in packages:
        started_at = time.time()
        log_step(f"Starting package: {package}")
        try:
            if package in {"mister", "cd32-mister"}:
                if cd32_release_state["error"] is not None:
                    raise cd32_release_state["error"]
                if cd32_release_state["artifact"] is None:
                    try:
                        if "cd32-mister" in packages:
                            cd32_output_path = output_dir / f"!AmigaVision-CD32-MiSTer-{args.date_stamp}.zip"
                        else:
                            cd32_release_state["temp_dir"] = make_stage_dir(
                                output_dir,
                                prefix="amigavision-cd32-release-",
                                dry_run=args.dry_run,
                            )
                            cd32_output_path = Path(cd32_release_state["temp_dir"].name) / f"!AmigaVision-CD32-MiSTer-{args.date_stamp}.zip"
                        cd32_release_state["artifact"] = build_cd32_release(args, cd32_output_path, dry_run=args.dry_run)
                    except Exception as exc:
                        cd32_release_state["error"] = exc
                        raise
            if package == "mister":
                created.append(package_mister(args, output_dir, archive_tool, cd32_release_state["artifact"]))
            elif package == "cd32-mister":
                created.append(package_cd32_mister(args, output_dir, cd32_release_state["artifact"]))
            elif package == "emulators":
                created.append(package_emulators(args, output_dir, archive_tool))
            elif package == "pi":
                created.append(package_rpi(args, output_dir, xz_tool))
            elif package == "amiga":
                created.append(package_amiga(args, output_dir, xz_tool))
            else:
                raise AssertionError(f"Unhandled package type: {package}")
            list_archive_contents(created[-1], archive_tool=archive_tool, xz_tool=xz_tool, dry_run=args.dry_run)
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
        if cd32_release_state["temp_dir"] is not None:
            cd32_release_state["temp_dir"].cleanup()
        return 1
    if cd32_release_state["temp_dir"] is not None:
        cd32_release_state["temp_dir"].cleanup()
    return 0


if __name__ == "__main__":
    sys.exit(main())
