"""Shared title artwork rules for all launcher resolutions."""
from pathlib import Path
import re
import shutil
import struct

HIRES_THUMBNAIL_SIZE = (404, 280)


def validate_hires_thumbnail_size(size, source):
    if tuple(size) != HIRES_THUMBNAIL_SIZE:
        raise ValueError(f"Invalid hi-res thumbnail {source}: {size[0]}x{size[1]}; required 404x280")


def validate_hires_artwork(root):
    """Reject oversized or incorrectly sized artwork before building the launcher."""
    for path in Path(root).rglob('*.iff'):
        if path.stem.lower().endswith(('-qr', '-qr2')):
            continue  # QR overlays have their own dimensions, separate from thumbnails.
        with path.open('rb') as stream:
            if stream.read(12)[8:] != b'ILBM':
                raise ValueError(f"Not an ILBM thumbnail: {path}")
            while True:
                header = stream.read(8)
                if len(header) != 8:
                    raise ValueError(f"Missing BMHD in thumbnail: {path}")
                tag, length = struct.unpack('>4sI', header)
                if tag == b'BMHD':
                    validate_hires_thumbnail_size(struct.unpack('>HH', stream.read(4)), path)
                    break
                stream.seek(length + length % 2, 1)


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
