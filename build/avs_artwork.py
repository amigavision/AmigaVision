"""Shared title artwork rules for all launcher resolutions."""
from pathlib import Path
import re
import shutil


def is_nsfw(entry):
    return 'nsfw' in {tag.strip().lower() for tag in (entry.get('subcategory') or '').split(',')}


def install_nsfw_thumbnail(base, profile):
    base = Path(base)
    roots = {'medium': 'data/img', 'hires': 'data/img_highres', 'ecs': 'data/img_ecs'}
    source = Path(roots[profile]) / 'NSFW.iff'
    # Remove all slides and QR artwork, including slots beyond the usual nine.
    for path in base.parent.glob('*.iff'):
        if re.fullmatch(re.escape(base.name) + r'(?:-\d+|-qr)?\.iff', path.name, re.I):
            path.unlink()
    shutil.copyfile(source, str(base) + '.iff')
