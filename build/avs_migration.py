"""Adapt launcher-owned files from an older native base during staging.

The source AV-Base tree stays untouched. MiSTer's core-owned protocol filenames
remain unchanged so its boot and now-playing integration keeps working.
"""
from pathlib import Path
import os
import re

from av_base_tree import ignored_name

_LEGACY = re.compile(r'(?<![A-Za-z])(?:AGS2?|ags2?)')

def visible_paths(parent):
    for current, dirs, files in os.walk(parent):
        dirs[:] = [name for name in dirs if not ignored_name(name)]
        for name in dirs + files:
            if not ignored_name(name):
                yield Path(current) / name


def rename_reference(value):
    value = _LEGACY.sub(lambda match: 'AVS' if match[0].isupper() else 'avs', value)
    return value.replace('MiSTer:avs_boot', 'MiSTer:ags_boot').replace(
        'MiSTer:avs_current', 'MiSTer:ags_current')


def migrate_staged_base(root):
    root = Path(root)
    # These are our scripts and environment files, not third-party applications.
    for directory in ('S', 'Prefs/Env-Archive'):
        parent = root / directory
        for path in visible_paths(parent):
            if not path.is_file():
                continue
            data = path.read_bytes()
            if b'\0' not in data:
                text = data.decode('latin-1')
                updated = rename_reference(text).encode('latin-1')
                if updated != data:
                    path.write_bytes(updated)
    app = root / 'Apps/AmigaVision'
    if app.is_file():
        app.write_bytes(rename_reference(app.read_bytes().decode('latin-1')).encode('latin-1'))
    # Rename bundled commands/fonts and their UAE metadata sidecars as a unit.
    for directory in ('C', 'S', 'Fonts', 'Prefs/Env-Archive'):
        parent = root / directory
        # Renaming on macOS also renames its ._ sidecar. Never process a
        # snapshot of those host files as if they were launcher commands.
        for path in sorted(visible_paths(parent), key=lambda p: len(p.parts), reverse=True):
            name = rename_reference(path.name)
            if name == path.name:
                continue
            target = path.with_name(name)
            if target.exists():
                raise ValueError(f'Conflicting launcher files in staged base: {path} and {target}')
            path.rename(target)
    for font in (root / 'Fonts').glob('AVS*.font'):
        data = font.read_bytes()
        font.write_bytes(data.replace(b'AGS', b'AVS'))
