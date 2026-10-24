"""Resolve the checked-in Windows installer or an explicit local override."""
from pathlib import Path

INSTALLER_NAME = "Install on Windows.exe"
LOCAL_INSTALLER = Path(__file__).resolve().parent.parent / "content/distro_emulators" / INSTALLER_NAME


def validate_installer(path):
    path = Path(path).expanduser().resolve()
    with path.open("rb") as source:
        if source.read(2) != b"MZ":
            raise ValueError(f"Not a Windows executable: {path}")
    return path


def resolve_windows_installer(explicit, download_dir=None, dry_run=False):
    path = Path(explicit).expanduser() if explicit else LOCAL_INSTALLER
    if not path.is_file():
        raise FileNotFoundError(
            f"Windows installer missing: {path}. Copy the tested Windows build to "
            f"{LOCAL_INSTALLER}, or supply WINDOWS_INSTALLER=/path/to/setup.exe to make emulators."
        )
    return validate_installer(path)
