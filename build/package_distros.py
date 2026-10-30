#!/usr/bin/env python3

import argparse
import ctypes
import errno
import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path
from functools import lru_cache

from user_paths import normalize_path
from artifact_checksums import write_checksums
from fetch_windows_installer import INSTALLER_NAME, resolve_windows_installer


IGNORED_NAMES = {".DS_Store", ".gitignore", "pack", "__pycache__"}
SEVENZIP_CANDIDATES = ("7zz", "7z", "7za")
SEVENZIP_COMPRESSION_ARGS = ("-mx=5", "-myx=3")
XZ_PRESET = 6
FAT32_MAX_FILE_BYTES = (4 * 1024 * 1024 * 1024) - 1
PLATFORM_DIRECTORIES = {
    "mister": "AmigaVision-MiSTer",
    "cd32-mister": "AmigaVision-CD32-MiSTer",
    "emulators": "AmigaVision-Emulators",
    "mini": "AmigaVision-Mini",
    "pi": "AmigaVision-RPi",
    "amiga": "AmigaVision-Amiga",
    "amiga-ecs": "AmigaVision-Amiga-ECS",
    "pistorm-aga": "AmigaVision-PiStormAGA",
    "pistorm-ecs": "AmigaVision-PiStormECS",
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Package uploadable AmigaVision distro artifacts from built images."
    )
    parser.add_argument(
        "package",
        choices=("all", "mister", "cd32-mister", "emulators", "mini", "pi", "amiga", "amiga-ecs", "pistorm-aga", "pistorm-ecs"),
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
    parser.add_argument("--ecs-hdf", help="Built ECS HDF for the amiga-ecs package")
    parser.add_argument("--saves-hdf", required=True)
    parser.add_argument("--rom-file", required=True)
    parser.add_argument("--listings-dir", required=True)
    parser.add_argument("--shared-dir", required=True)
    parser.add_argument("--visuals-dir", required=True)
    parser.add_argument("--mini-root", default="content/distro_mini")
    parser.add_argument("--mini-hdf")
    parser.add_argument("--mini-uae")
    parser.add_argument("--pi-script", default="build/pi_image.sh")
    parser.add_argument("--amiberry", default=os.environ.get("AMIBERRYBIN", "/Applications/Amiberry.app/Contents/MacOS/Amiberry"))
    parser.add_argument("--pistorm-rom", help="Kickstart ROM for PiStorm images; defaults to --rom-file")
    parser.add_argument("--archive-tool")
    parser.add_argument("--windows-installer", help="Local Windows setup executable; defaults to the checked-in repo copy")
    parser.add_argument("--emulator-archive", action="store_false", dest="skip_emulator_archive",
                        help="Create a 7z archive of the emulator folders.", default=False)
    parser.add_argument("--skip-emulator-archive", action="store_true",
                        help="Keep the emulator folders instead of creating a 7z archive.")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def echo(message):
    print(message, flush=True)


def timestamp():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def log_step(message):
    echo(f"[{timestamp()}] {message}")


def warn_if_exceeds_fat32_limit(path, label):
    path = Path(path)
    if not path.is_file():
        return
    size = path.stat().st_size
    if size <= FAT32_MAX_FILE_BYTES:
        return
    log_step(
        "WARNING: {} is {} bytes ({:.2f} GiB), which exceeds the FAT32 file size "
        "limit of {} bytes ({:.2f} GiB).".format(
            label,
            size,
            size / (1024 ** 3),
            FAT32_MAX_FILE_BYTES,
            FAT32_MAX_FILE_BYTES / (1024 ** 3),
        )
    )


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


@lru_cache(maxsize=1)
def get_clonefile():
    clonefile = getattr(os, "clonefile", None)
    if clonefile is not None:
        return clonefile
    if sys.platform != "darwin":
        return None
    # CPython does not expose clonefile on macOS. Call the native APFS API
    # directly instead of starting a cp process for every staged file.
    library = ctypes.CDLL("/usr/lib/libSystem.B.dylib", use_errno=True)
    native_clonefile = library.clonefile
    native_clonefile.argtypes = (ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int)
    native_clonefile.restype = ctypes.c_int

    def clonefile(src, dest):
        if native_clonefile(os.fsencode(src), os.fsencode(dest), 0) != 0:
            error = ctypes.get_errno()
            raise OSError(error, os.strerror(error), os.fspath(src))

    return clonefile


def copy_portable_stat(src, dest):
    try:
        shutil.copystat(src, dest, follow_symlinks=True)
    except OSError as exc:
        if exc.errno not in {errno.EINVAL, errno.ENOTSUP, errno.ENOSYS}:
            raise
        # exFAT may reject macOS extended attributes/flags. File contents and
        # executable permissions matter for the portable packages.
        for operation in (
            lambda: shutil.copymode(src, dest),
            lambda: os.utime(dest, ns=(src.stat().st_atime_ns, src.stat().st_mtime_ns)),
        ):
            try:
                operation()
            except OSError as metadata_error:
                if metadata_error.errno not in {errno.EINVAL, errno.ENOTSUP, errno.ENOSYS}:
                    raise


def clone_or_copy_file(src, dest):
    src = Path(src)
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    clonefile = get_clonefile()
    if clonefile is not None:
        try:
            clonefile(src, dest)
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
        else:
            copy_portable_stat(src, dest)
            return
    shutil.copyfile(src, dest)
    copy_portable_stat(src, dest)


def clone_or_copy_tree(src, dest, dirs_exist_ok=False):
    shutil.copytree(src, dest, dirs_exist_ok=dirs_exist_ok, copy_function=clone_or_copy_file)


def copy_tree_contents(src_root, dest_root, excluded_names=None):
    excluded = set(excluded_names or ())
    dest_root.mkdir(parents=True, exist_ok=True)
    for child in sorted(src_root.iterdir()):
        if child.name in IGNORED_NAMES or child.name.startswith(".") or child.name in excluded:
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


def purge_macos_metadata(root):
    root = Path(root)
    if not root.exists():
        return
    for candidate in root.rglob("*"):
        if candidate.name == ".DS_Store" or candidate.name.startswith("._"):
            try:
                candidate.unlink()
            except FileNotFoundError:
                pass


def cleanup_stage_dir(path, attempts=5, delay=0.2):
    path = Path(path)
    if not path.exists():
        return
    last_error = None
    for _ in range(attempts):
        purge_macos_metadata(path)
        try:
            shutil.rmtree(path)
            return
        except FileNotFoundError:
            return
        except OSError as exc:
            last_error = exc
            if exc.errno not in {errno.ENOTEMPTY, errno.EBUSY, errno.EPERM, errno.EACCES}:
                raise
            time.sleep(delay)
    if last_error is not None:
        raise last_error


class StageDir:
    def __init__(self, path):
        self.name = str(path)

    def cleanup(self):
        cleanup_stage_dir(self.name)

    def __enter__(self):
        return self.name

    def __exit__(self, exc_type, exc, tb):
        self.cleanup()
        return False


def make_stage_dir(parent, prefix, dry_run=False):
    if dry_run:
        return StageDir(tempfile.mkdtemp(prefix=prefix))
    return StageDir(tempfile.mkdtemp(prefix=prefix, dir=parent))


def write_text(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def ensure_dir(path):
    path.mkdir(parents=True, exist_ok=True)


def pick_mini_launcher_template(root):
    preferred = (
        "Start AmigaVision_ol.uae",
        "Start AmigaVision (Mouse+Joystick)_ol.uae",
        "Start AmigaVision (2 Joysticks)_ol.uae",
    )
    root = Path(root)
    candidates = [root / name for name in preferred if (root / name).is_file()]
    discovered = sorted(
        path for path in root.glob("*_ol.uae") if path.is_file() and path not in candidates
    )
    candidates.extend(discovered)
    return candidates[0] if candidates else None


def generate_mini_launcher(src, dest):
    text = Path(src).read_text(encoding="utf-8")
    text = (
        text.replace("/mnt/AmigaVision-Mini.hdf", "AmigaVision-Mini.hdf")
        .replace("/mnt/AmigaVision-Saves.hdf", "AmigaVision-Saves.hdf")
        .replace("/mnt/Shared", "Shared")
    )
    write_text(dest, text)


def make_amiberry_skeleton(stage_root):
    for relative in (
        "Configurations",
        "ROMs",
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
    env = compression_environment(output_path)
    cmd = [archive_tool, "a", "-t7z", *SEVENZIP_COMPRESSION_ARGS,
           "-w" + env["TMPDIR"], "-xr!.*", str(output_path)] + members
    subprocess.run(cmd, cwd=input_root, check=True, env=env)


def compression_environment(output_path):
    """Keep compressor scratch files on the artifact's destination filesystem."""
    scratch = Path(output_path).resolve().parent / '.build' / 'tmp'
    scratch.mkdir(parents=True, exist_ok=True)
    return dict(os.environ, TMPDIR=str(scratch), TMP=str(scratch), TEMP=str(scratch))


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
    run_command(["bash", str(pack_script), args.date_stamp, str(output_path)], dry_run=dry_run,
                env=None if dry_run else compression_environment(output_path))
    if not dry_run:
        require_file(output_path, "Generated CD32 distro archive")
    return output_path


def compress_xz(src_path, dest_path, xz_tool, dry_run=False, preset=XZ_PRESET):
    log_step(f"Compressing {src_path.name} -> {dest_path.name}")
    if dry_run:
        echo(f"[dry-run] Would compress {src_path} -> {dest_path}")
        return
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    if dest_path.exists():
        dest_path.unlink()
    with dest_path.open("wb") as dest:
        subprocess.run(
            [xz_tool, "-T0", f"-{preset}", "-v", "-k", "-c", str(src_path)],
            check=True,
            stdout=dest,
            env=compression_environment(dest_path),
        )


def run_command(cmd, dry_run=False, env=None):
    display = " ".join(map(str, cmd))
    log_step(f"Running command: {display}")
    if dry_run:
        echo(f"[dry-run] Would run: {display}")
        return
    subprocess.run(cmd, check=True, env=env)


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


def package_mister(args, output_dir, archive_tool):
    mister_root = Path(args.mister_root)
    main_hdf = Path(args.main_hdf)
    built_root = main_hdf.parent.resolve()
    listings_dir = Path(args.listings_dir)
    require_dir(mister_root, "MiSTer distro root")
    require_dir(built_root, "Built MiSTer output root")
    require_file(main_hdf, "Main AmigaVision HDF")
    require_dir(listings_dir, "Generated listings directory")

    output_path = output_dir / f"AmigaVision-MiSTer-{args.date_stamp}.7z"
    with make_stage_dir(output_dir, prefix="amigavision-mister-", dry_run=args.dry_run) as tmp_dir:
        stage_root = Path(tmp_dir)
        log_step(f"Staging MiSTer payload from built output root {built_root}")
        copy_tree_contents(
            built_root,
            stage_root,
            excluded_names={
                "distros",
                ".build",
                stage_root.name,
                output_dir.relative_to(built_root).parts[0]
                if output_dir.is_relative_to(built_root) and output_dir != built_root else output_path.name,
                "CD32-Output",
                "AmigaVision.hdf",
                "AmigaVision-ECS.hdf",
                Path(args.ecs_hdf).name if getattr(args, "ecs_hdf", None) else "AmigaVision-ECS.hdf",
                "AmigaVision-Mini",
                "AmigaVision-Mini.hdf",
                "AmigaVision-Mini.uae",
                "games",
                "listings",
            },
        )
        log_step(f"Overlaying canonical MiSTer content from {mister_root}")
        copy_tree_contents(mister_root, stage_root)
        visuals_dir = stage_root / "games" / "Amiga" / "Visuals"
        if visuals_dir.exists():
            log_step("Removing emulator-only Visuals payload from MiSTer package")
            shutil.rmtree(visuals_dir)
        log_step("Injecting built AmigaVision.hdf into MiSTer package")
        replace_path(main_hdf, stage_root / "games" / "Amiga" / "AmigaVision.hdf")
        log_step("Injecting generated listings into MiSTer package")
        replace_path(listings_dir, stage_root / "games" / "Amiga" / "listings")
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
    emulator_root = Path("content/distro_emulators")
    launcher_template = emulator_root / "Amiberry/AmigaVision-Amiberry.uae"
    amiberry_install = emulator_root / "Amiberry/INSTALL.txt"
    custom_shader_path = Path("Shaders/crt/shaders/crt-easymode-halation/crt-easymode-halation.glsl")
    custom_shader = emulator_root / "Amiberry/Visuals" / custom_shader_path
    winuae_config = emulator_root / "WinUAE/default.uae"
    winuae_shader = emulator_root / "WinUAE/CRT-Pi-SmartRes.fx"
    winuae_install = emulator_root / "WinUAE/INSTALL.txt"
    require_file(main_hdf, "Main AmigaVision HDF")
    require_file(saves_hdf, "AmigaVision saves HDF")
    require_file(rom_file, "AmigaVision ROM")
    require_dir(listings_dir, "Generated listings directory")
    require_dir(shared_dir, "Shared support directory")
    require_dir(visuals_root, "AmigaVision Visuals payload")
    require_file(launcher_template, "Amiberry launcher template")
    require_file(amiberry_install, "Amiberry installation instructions")
    require_file(custom_shader, "Versioned AmigaVision CRT shader")
    require_file(winuae_config, "WinUAE configuration")
    require_file(winuae_shader, "WinUAE CRT shader")
    require_file(winuae_install, "WinUAE installation instructions")

    install_guides = [emulator_root / f"Install on {platform}.html"
                      for platform in ("Mac", "Linux")]
    for guide in install_guides:
        require_file(guide, "Installation guide")
    require_file(emulator_root / "Copperline/AmigaVision.toml", "Copperline configuration")
    require_file(emulator_root / "Copperline/INSTALL.txt", "Copperline installation instructions")
    skip_archive = args.skip_emulator_archive
    output_path = output_dir / (f"AmigaVision-Emulators-{args.date_stamp}" + ("" if skip_archive else ".7z"))
    if skip_archive and output_path.exists():
        raise FileExistsError(f"Emulator output already exists: {output_path}. Choose another output directory or release date.")
    with make_stage_dir(output_dir, prefix="amigavision-windows-installer-", dry_run=args.dry_run) as installer_dir, \
            make_stage_dir(output_dir, prefix="amigavision-emulators-", dry_run=args.dry_run) as tmp_dir:
        installer = resolve_windows_installer(getattr(args, "windows_installer", None), installer_dir, dry_run=args.dry_run)
        if not args.dry_run:
            clone_or_copy_file(installer, Path(tmp_dir) / INSTALLER_NAME)
        for guide in install_guides:
            replace_path(guide, Path(tmp_dir) / guide.name)
        stage_root = Path(tmp_dir) / "Amiberry"
        make_amiberry_skeleton(stage_root)
        harddrives_root = stage_root / "HardDrives"
        roms_root = stage_root / "ROMs"
        mac_conf_root = stage_root / "Configurations"
        log_step("Staging reusable Amiberry payload")
        replace_path(main_hdf, harddrives_root / "AmigaVision.hdf")
        replace_path(saves_hdf, harddrives_root / "AmigaVision-Saves.hdf")
        replace_path(rom_file, roms_root / "AmigaVision.rom")
        replace_path(shared_dir, harddrives_root / "Shared")
        replace_path(listings_dir, harddrives_root / "listings")
        replace_path(visuals_root, stage_root / "Visuals")
        log_step("Applying versioned AmigaVision CRT shader")
        canonical_visuals = emulator_root / "Amiberry/Visuals"
        for shader_asset in sorted(canonical_visuals.rglob("*")):
            if shader_asset.is_file():
                replace_path(shader_asset, stage_root / "Visuals" / shader_asset.relative_to(canonical_visuals))
        replace_path(launcher_template, mac_conf_root / "default.uae")
        clone_or_copy_file(mac_conf_root / "default.uae", mac_conf_root / "AmigaVision.uae")
        replace_path(amiberry_install, stage_root / "INSTALL.txt")
        stage_root = Path(tmp_dir) / "WinUAE"
        log_step("Staging reusable WinUAE payload")
        replace_path(winuae_config, stage_root / "Configurations" / winuae_config.name)
        clone_or_copy_file(stage_root / "Configurations/default.uae", stage_root / "Configurations/AmigaVision.uae")
        replace_path(winuae_shader, stage_root / "plugins/filtershaders/direct3d" / winuae_shader.name)
        replace_path(winuae_install, stage_root / "INSTALL.txt")
        replace_path(emulator_root / "Copperline/AmigaVision.toml", Path(tmp_dir) / "Copperline/configs/AmigaVision.toml")
        replace_path(emulator_root / "Copperline/INSTALL.txt", Path(tmp_dir) / "Copperline/INSTALL.txt")
        if skip_archive:
            if args.dry_run:
                log_step(f"[dry-run] Would keep emulator folders at {output_path}")
            else:
                Path(tmp_dir).rename(output_path)
                log_step(f"Kept emulator folders at {output_path}; skipping 7z compression")
        else:
            archive_7z(output_path, Path(tmp_dir), archive_tool, dry_run=args.dry_run)
    return output_path


def package_mini(args, output_dir, archive_tool):
    mini_root = Path(args.mini_root)
    mini_hdf = Path(args.mini_hdf) if args.mini_hdf else None
    mini_uae = Path(args.mini_uae) if args.mini_uae else None
    saves_hdf = Path(args.saves_hdf)
    require_dir(mini_root, "Mini distro root")
    if mini_hdf is None:
        raise FileNotFoundError("Mini HDF path not provided")
    require_file(mini_hdf, "Mini AmigaVision HDF")
    require_file(saves_hdf, "AmigaVision saves HDF")
    warn_if_exceeds_fat32_limit(mini_hdf, "Mini AmigaVision HDF")

    output_path = output_dir / f"AmigaVision-Mini-{args.date_stamp}.7z"
    with make_stage_dir(output_dir, prefix="amigavision-mini-", dry_run=args.dry_run) as tmp_dir:
        stage_root = Path(tmp_dir)
        log_step(f"Staging Mini payload from canonical Mini content in {mini_root}")
        copy_tree_contents(mini_root, stage_root)
        log_step("Injecting built Mini HDF into Mini package")
        replace_path(mini_hdf, stage_root / "AmigaVision-Mini.hdf")
        log_step("Injecting shared saves HDF into Mini package")
        replace_path(saves_hdf, stage_root / "AmigaVision-Saves.hdf")
        launcher_template = pick_mini_launcher_template(stage_root)
        if launcher_template is not None:
            log_step(f"Generating Mini UAE launcher from {launcher_template.name}")
            generate_mini_launcher(launcher_template, stage_root / "AmigaVision-Mini.uae")
        elif mini_uae is not None and mini_uae.is_file():
            log_step("Injecting prebuilt Mini UAE launcher into Mini package")
            replace_path(mini_uae, stage_root / "AmigaVision-Mini.uae")
        else:
            log_step("No Mini UAE launcher template found; skipping generated Mini launcher")
        readme_markdown = stage_root / "AmigaVision-Mini-ReadMe.md"
        readme_text = stage_root / "AmigaVision-Mini-ReadMe.txt"
        if readme_markdown.exists():
            log_step("Renaming Mini README for packaged distro")
            replace_path(readme_markdown, readme_text)
            if not args.dry_run and readme_markdown.exists():
                readme_markdown.unlink()
        archive_7z(output_path, stage_root, archive_tool, dry_run=args.dry_run)
    return output_path


def package_rpi(args, output_dir, xz_tool):
    pi_script = Path(args.pi_script)
    main_hdf = Path(args.main_hdf)
    require_file(pi_script, "Raspberry Pi packaging script")
    require_file(main_hdf, "Main AmigaVision HDF")

    raw_output = output_dir / f"AmigaVision-RPi-{args.date_stamp}.img"
    compressed_output = output_dir / f"AmigaVision-RPi-{args.date_stamp}.img.xz"
    log_step("Building Raspberry Pi image from configured RePlayOS base image")
    run_command(
        [
            str(pi_script),
            "--hdf",
            str(main_hdf),
            "--output-img",
            str(raw_output),
        ],
        dry_run=args.dry_run,
    )
    compress_xz(raw_output, compressed_output, xz_tool, dry_run=args.dry_run, preset=1)
    if not args.dry_run and raw_output.exists():
        log_step(f"Removing intermediate image {raw_output.name}")
        raw_output.unlink()
    return compressed_output


def package_amiga(args, output_dir, xz_tool, ecs=None):
    if ecs is None:
        ecs = args.package == "amiga-ecs"
    if ecs and not args.ecs_hdf:
        raise ValueError("--ecs-hdf is required for amiga-ecs")
    main_hdf = Path(args.ecs_hdf if ecs else args.main_hdf)
    require_file(main_hdf, "ECS AmigaVision HDF" if ecs else "Main AmigaVision HDF")

    variant = "Amiga-ECS" if ecs else "Amiga"
    output_path = output_dir / f"AmigaVision-{variant}-{args.date_stamp}.img.xz"
    log_step(f"Compressing {main_hdf.name} for real Amiga hardware")
    compress_xz(main_hdf, output_path, xz_tool, dry_run=args.dry_run)
    return output_path


def package_pistorm(args, output_dir, ecs=False):
    hdf = args.ecs_hdf if ecs else args.main_hdf
    if not hdf:
        raise ValueError("--ecs-hdf is required for PiStorm ECS")
    require_file(Path(hdf), "PiStorm source HDF")
    variant = "PiStormECS" if ecs else "PiStormAGA"
    output = output_dir / f"AmigaVision-{variant}-{args.date_stamp}.img.xz"
    run_command([
        sys.executable, str(Path(__file__).with_name("pistorm_image.py")),
        "--model", "pistorm" if ecs else "pistorm32lite",
        "--hdf", str(hdf), "--rom", str(args.pistorm_rom or args.rom_file),
        "--amiberry", str(args.amiberry), "--date-stamp", args.date_stamp,
        "--output", str(output), "--output-dir", str(output_dir),
        "--cache", str(output_dir / ".build/cache/pistorm"),
    ], dry_run=args.dry_run,
       env=None if args.dry_run else compression_environment(output))
    if not args.dry_run:
        require_file(output, "PiStorm image")
    return output


def main():
    args = parse_args()
    output_dir = Path(normalize_path(args.output_dir)).resolve()
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        echo(f"Cannot create output directory {output_dir}: {exc.strerror}")
        return 1
    continue_on_error = args.package == "all"
    packages = (
        # Mini is temporarily standalone until its image fits the 4 GB target.
        ["mister", "cd32-mister", "emulators", "pi", "amiga", "amiga-ecs", "pistorm-aga", "pistorm-ecs"]
        if args.package == "all"
        else [args.package]
    )

    archive_tool = None
    if any(package in {"mister", "mini"} or
           (package == "emulators" and not args.skip_emulator_archive) for package in packages):
        archive_tool = find_archive_tool(args.archive_tool)
    xz_tool = None
    if any(package in {"pi", "amiga", "amiga-ecs", "pistorm-aga", "pistorm-ecs"} for package in packages):
        xz_tool = find_xz_tool()

    log_step(f"Writing artifacts to {output_dir}")
    created = []
    failures = []
    cd32_release_state = {"artifact": None, "error": None, "temp_dir": None}
    try:
        for package in packages:
            platform_dir = output_dir / PLATFORM_DIRECTORIES[package]
            if not args.dry_run:
                platform_dir.mkdir(parents=True, exist_ok=True)
            started_at = time.time()
            log_step(f"Starting package: {package}")
            try:
                if package == "cd32-mister":
                    if cd32_release_state["error"] is not None:
                        raise cd32_release_state["error"]
                    if cd32_release_state["artifact"] is None:
                        try:
                            if "cd32-mister" in packages:
                                cd32_output_path = platform_dir / f"!AmigaVision-CD32-MiSTer-{args.date_stamp}.zip"
                            else:
                                cd32_release_state["temp_dir"] = make_stage_dir(
                                    platform_dir,
                                    prefix="amigavision-cd32-release-",
                                    dry_run=args.dry_run,
                                )
                                cd32_output_path = Path(cd32_release_state["temp_dir"].name) / f"!AmigaVision-CD32-MiSTer-{args.date_stamp}.zip"
                            cd32_release_state["artifact"] = build_cd32_release(args, cd32_output_path, dry_run=args.dry_run)
                        except Exception as exc:
                            cd32_release_state["error"] = exc
                            raise
                if package == "mister":
                    created.append(package_mister(args, platform_dir, archive_tool))
                elif package == "cd32-mister":
                    created.append(package_cd32_mister(args, platform_dir, cd32_release_state["artifact"]))
                elif package == "emulators":
                    created.append(package_emulators(args, platform_dir, archive_tool))
                elif package == "mini":
                    created.append(package_mini(args, platform_dir, archive_tool))
                elif package == "pi":
                    created.append(package_rpi(args, platform_dir, xz_tool))
                elif package in {"amiga", "amiga-ecs"}:
                    created.append(package_amiga(args, platform_dir, xz_tool, ecs=package == "amiga-ecs"))
                elif package in {"pistorm-aga", "pistorm-ecs"}:
                    created.append(package_pistorm(args, platform_dir, ecs=package == "pistorm-ecs"))
                else:
                    raise AssertionError(f"Unhandled package type: {package}")
                unpacked_emulators = package == "emulators" and args.skip_emulator_archive
                if not unpacked_emulators:
                    list_archive_contents(created[-1], archive_tool=archive_tool, xz_tool=xz_tool, dry_run=args.dry_run)
                if unpacked_emulators:
                    log_step("Uncompressed emulator folders ready; archive checksums skipped")
                elif args.dry_run:
                    log_step(f"[dry-run] Would write SHA-256 and MD5 checksums for {created[-1].name}")
                else:
                    write_checksums(created[-1])
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
    finally:
        if cd32_release_state["temp_dir"] is not None:
            cd32_release_state["temp_dir"].cleanup()


if __name__ == "__main__":
    sys.exit(main())
