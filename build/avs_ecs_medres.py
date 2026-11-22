"""Build the ECS med-res alternative using cached 16-color artwork conversions."""
from concurrent.futures import ProcessPoolExecutor
import hashlib
import os
from pathlib import Path
import shutil

from PIL import Image
from ecs_artwork import decode_artwork, encode_ecs
from ecs_palette import quantize_perceptual
from repair_hires_palettes import read_chunks

VERSION = 'ecs-medres-13-rgb4-v1'
# A quantizer/encoder change must also invalidate existing converted outputs.
ENCODER_FILES = ('avs_ecs_medres.py', 'ecs_palette.py', 'ecs_artwork.py', 'iff_ilbm.py')
UI = [0, 153, 187, 0, 0, 0, 255, 255, 255]


def convert(job):
    source, destination, skin = job
    source, destination = Path(source), Path(destination)
    original, mode = decode_artwork(read_chunks(source))
    if skin:
        # The med-res UI remains monochrome cyan/black, independent of pictures.
        rgb = original.convert('RGB').tobytes()
        pixels = bytes(13 if max(rgb[i:i+3]) > 17 else 14 for i in range(0, len(rgb), 3))
        indexed = Image.frombytes('P', original.size, pixels)
        indexed.putpalette([0]*39 + UI + [0]*720)
    else:
        indexed = quantize_perceptual(original)
    blob = encode_ecs(indexed, mode & ~4)  # medium-resolution, non-interlaced
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix('.tmp')
    temporary.write_bytes(blob)
    decoded, _ = decode_artwork(read_chunks(temporary))
    assert decoded.tobytes() == indexed.tobytes()
    assert decoded.getpalette()[39:48] == UI
    assert max(decoded.tobytes()) < (16 if skin else 13)
    temporary.replace(destination)
    return str(destination)


def build_launcher(source, destination, cache=None, jobs=None):
    """Clone the generated ECS menu before its art is replaced by hi-res art."""
    source, destination = Path(source), Path(destination)
    if source.resolve() == destination.resolve() or source.resolve() in destination.resolve().parents:
        raise ValueError('Med-res destination must be separate from the source tree')
    if cache is None:
        from avs_paths import cache_root
        cache = Path(cache_root())/'ecs-medres-artwork'
    cache = Path(cache)
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination)
    launcher = Path('data/avs-ecs-medres')
    for name in ('AVSMenu', 'AVSHelper', 'AVS.conf'):
        shutil.copyfile(launcher/name, destination/name)
    shutil.copyfile(launcher/'AVS.conf', destination/'AVS.conf.base')
    # Add the original medium layout, never the 256-color palette itself.
    for name in ('skin-bg.iff', 'skin-empty.iff'):
        shutil.copyfile(launcher/name, destination/name)
    identity = VERSION.encode() + b''.join(
        (Path(__file__).parent/name).read_bytes() for name in ENCODER_FILES)
    assets = []
    unique = {}
    for path in sorted(destination.rglob('*.iff')):
        skin = path.name.startswith('skin-') or path.stem.lower().endswith(('-qr', '-qr2'))
        digest = hashlib.sha256(identity + bytes([skin]) + path.read_bytes()).hexdigest()
        cached = cache/(digest+'.iff')
        assets.append((cached, path))
        if not cached.is_file():
            unique.setdefault(digest, (str(path), str(cached), skin))
    workers = jobs or min(4, os.cpu_count() or 1)
    print(f' > ECS med-res: converting {len(unique)} unique images; {len(assets)} menu image paths', flush=True)
    if workers == 1:
        for job in unique.values():
            convert(job)
    elif unique:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            for completed, _ in enumerate(pool.map(convert, unique.values(), chunksize=8), 1):
                if completed % 250 == 0 or completed == len(unique):
                    print(f' > ECS med-res: converted {completed}/{len(unique)} images', flush=True)
    for cached, path in assets:
        shutil.copyfile(cached, path)
    return len(unique), len(assets)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--cache', type=Path)
    parser.add_argument('--jobs', type=int, default=min(4, os.cpu_count() or 1))
    args = parser.parse_args()
    if args.jobs < 1:
        parser.error('--jobs must be positive')
    build_launcher(args.source, args.destination, args.cache, args.jobs)
