#!/usr/bin/env python3
"""Pre-render static ECS IFFs. Normal image builds only copy these files."""
import argparse
import hashlib
import json
import os
import struct
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from PIL import Image
import iff_ilbm
from repair_hires_palettes import decode, read_chunks

VERSION = 'ecs-13-rgb4-v6-copper-ui'


def encode_ecs(image, mode):
    width, height = image.size
    stride = ((width + 15) // 16) * 2
    raw = image.tobytes()
    padded = b''.join(raw[y*width:(y+1)*width].ljust(stride*8, b'\x00') for y in range(height))
    planes = []
    for plane in range(4):
        table = bytes(48 + ((value >> plane) & 1) for value in range(256))
        planes.append(int(padded.translate(table), 2).to_bytes(stride * height, 'big'))
    body = b''.join(planes[p][y*stride:(y+1)*stride] for y in range(height) for p in range(4))
    palette = iff_ilbm.palette_data(image.getpalette()[:48])
    _, bmhd, cmap, camg = iff_ilbm.header(width, height, palette, mode, 0)
    return iff_ilbm.chunk('FORM', b'ILBM', bmhd, cmap, camg, iff_ilbm.chunk('BODY', body))


def quantize_ecs(source, skin=False):
    rgb = source.convert('RGB')
    if skin:
        # Original skin has black, almost-black (1,1,1), and the blue border.
        pixels = bytes(13 if max(color) > 17 else 14 for color in rgb.getdata())
        indexed = Image.frombytes('P', source.size, pixels)
        # Skin and QR foreground use steady slot 13, never gradient slot 15.
        indexed.putpalette([0]*39 + [0,153,187,0,0,0,255,255,255] + [0]*720)
        return indexed
    from ecs_palette import quantize_perceptual
    return quantize_perceptual(source)


def convert(job):
    source, dest, skin = job
    source, dest = Path(source), Path(dest)
    original, mode = decode(read_chunks(source))
    is_qr = source.parent.name.lower() == 'qr' or source.stem.lower().endswith('-qr')
    indexed = quantize_ecs(original, skin or is_qr)
    blob = encode_ecs(indexed, mode)
    dest.parent.mkdir(parents=True, exist_ok=True)
    temporary = dest.with_suffix('.iff.tmp')
    temporary.write_bytes(blob)
    result, _ = decode(read_chunks(temporary))
    assert result.tobytes() == indexed.tobytes()
    assert result.getpalette()[39:48] == [0,153,187,0,0,0,255,255,255]
    assert result.getpalette()[:3] == [0,0,0]
    if skin or is_qr:
        assert set(result.tobytes()) <= {13,14}
    temporary.replace(dest)
    return str(dest)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('data/img_ecs'))
    parser.add_argument('--launcher-output', type=Path, default=Path('data/avs-ecs'))
    parser.add_argument('--jobs', type=int, default=min(4, os.cpu_count() or 1))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    manifest_path = args.output/'manifest.json'
    previous = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    jobs = []
    manifest = {'version': VERSION, 'sources': {}}
    # Navigation artwork lives alongside the high-resolution title masters.
    sources = [(p, args.output/p.relative_to('data/img_highres'), False)
               for p in sorted(Path('data/img_highres').rglob('*.iff'))]
    sources += [(p, args.launcher_output/p.name, p.name.startswith('skin-'))
                for p in sorted(Path('data/avs-highres').glob('*.iff'))
                if p.name != 'skin-bg-highres.iff']
    # The ECS monochrome background is maintained separately; preserve it even
    # when its AGA counterpart changes or the generated artwork is rebuilt.
    for source, dest, skin in sources:
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        key = str(source)
        manifest['sources'][key] = digest
        previous_digest = previous.get('sources', {}).get(key)
        # Preserve the one-time skin lettering conversion when migrating its
        # historical fingerprint to the normal source hash. Changed sources
        # still regenerate normally.
        legacy_skin = skin and previous_digest == hashlib.sha256(
            source.read_bytes()+b'ecs-skin-enclosed-lettering-black-v2').hexdigest()
        if (previous.get('version') == VERSION and dest.is_file()
                and (previous_digest == digest or legacy_skin)):
            continue
        jobs.append((str(source), str(dest), skin))
    print(f'Converting {len(jobs)} changed/missing ECS images; reusing {len(sources)-len(jobs)}', flush=True)
    with ProcessPoolExecutor(max_workers=args.jobs) as executor:
        for index, _ in enumerate(executor.map(convert, jobs, chunksize=8), 1):
            if index % 500 == 0:
                print(f'Converted {index}/{len(jobs)}', flush=True)
    temporary = manifest_path.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(manifest, indent=2)+'\n')
    temporary.replace(manifest_path)
    print(f'Static ECS artwork ready: {len(sources)} images', flush=True)


if __name__ == '__main__':
    main()
