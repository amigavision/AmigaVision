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

VERSION = 'ecs-13-rgb4-v8-aga-canonical-404x280-cyan-ui'


def encode_ecs(image, mode):
    width, height = image.size
    stride = ((width + 15) // 16) * 2
    raw = image.tobytes()
    padded = b''.join(raw[y*width:(y+1)*width].ljust(stride*8, b'\x00') for y in range(height))
    planes = []
    for plane in range(4):
        table = bytes(48 + ((value >> plane) & 1) for value in range(256))
        planes.append(int(padded.translate(table), 2).to_bytes(stride * height, 'big'))
    body = b''.join(iff_ilbm.packbits(planes[p][y*stride:(y+1)*stride]) for y in range(height) for p in range(4))
    palette = iff_ilbm.palette_data(image.getpalette()[:48])
    _, bmhd, cmap, camg = iff_ilbm.header(width, height, palette, mode, 1)
    return iff_ilbm.chunk('FORM', b'ILBM', bmhd, cmap, camg, iff_ilbm.chunk('BODY', body))


def quantize_ecs(source, skin=False):
    rgb = source.convert('RGB')
    if skin:
        # Original skin has black, almost-black (1,1,1), and the blue border.
        pixels = bytes(13 if max(color) > 17 else 14 for color in rgb.getdata())
        indexed = Image.frombytes('P', source.size, pixels)
        # Skin and QR use steady cyan and black; white is reserved for Copper text.
        indexed.putpalette([0]*39 + [0,153,187,0,0,0,255,255,255] + [0]*720)
        return indexed
    from ecs_palette import quantize_perceptual
    return quantize_perceptual(source)


def decode_artwork(chunks):
    """Decode standard planar artwork with vectorized bitplane expansion."""
    import numpy as np
    header = chunks[b'BMHD']
    width, height = struct.unpack_from('>HH', header)
    depth, masking, compression = header[8:11]
    mode = struct.unpack('>I', chunks.get(b'CAMG', bytes(4)))[0]
    if masking or depth > 8 or mode & 0x880:
        return decode(chunks)
    body = chunks[b'BODY']
    if compression == 0:
        raw = body
    elif compression == 1:
        raw = bytearray()
        pos = 0
        while pos < len(body):
            count = body[pos]; pos += 1
            if count < 128:
                raw.extend(body[pos:pos+count+1]); pos += count+1
            elif count > 128:
                raw.extend(body[pos:pos+1]*(257-count)); pos += 1
    else:
        return decode(chunks)
    stride = ((width+15)//16)*2
    planes = np.frombuffer(raw, dtype=np.uint8).reshape(height, depth, stride)
    bits = np.unpackbits(planes, axis=2)[:, :, :width]
    pixels = np.bitwise_or.reduce(bits << np.arange(depth, dtype=np.uint8)[None, :, None], axis=1)
    image = Image.frombytes('P', (width,height), pixels.tobytes())
    image.putpalette(chunks[b'CMAP'])
    return image, mode


def convert(job):
    source, dest, skin = job
    source, dest = Path(source), Path(dest)
    original, mode = decode_artwork(read_chunks(source))
    is_qr = source.parent.name.lower() == 'qr' or source.stem.lower().endswith('-qr')
    # Preserve canonical AGA dimensions, including 404x280 thumbnails.
    indexed = quantize_ecs(original, skin or is_qr)
    blob = encode_ecs(indexed, mode)
    dest.parent.mkdir(parents=True, exist_ok=True)
    temporary = dest.with_suffix('.iff.tmp')
    temporary.write_bytes(blob)
    result, _ = decode_artwork(read_chunks(temporary))
    assert result.tobytes() == indexed.tobytes()
    assert result.getpalette()[39:48] == [0,153,187,0,0,0,255,255,255]
    assert result.getpalette()[:3] == [0,0,0]
    if skin or is_qr:
        assert set(result.tobytes()) <= {13,14}
    temporary.replace(dest)
    return str(dest)



def cache_manifest_path(output, launcher_output):
    """Conversion state is local bookkeeping, never a checked-in build input."""
    import avs_paths
    identity = hashlib.sha256(json.dumps([
        str(Path(output).resolve()), str(Path(launcher_output).resolve())
    ]).encode('utf-8')).hexdigest()
    return Path(avs_paths.cache_root())/'ecs-artwork'/identity/'manifest.json'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('data/img_ecs'))
    parser.add_argument('--launcher-output', type=Path, default=Path('data/avs-ecs'))
    parser.add_argument('--jobs', type=int, default=min(4, os.cpu_count() or 1))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    manifest_path = cache_manifest_path(args.output, args.launcher_output)
    try:
        previous = json.loads(manifest_path.read_text())
    except (OSError, ValueError):
        previous = {}
    jobs = []
    duplicates = []
    representatives = {}
    manifest = {'version': VERSION, 'sources': {}}
    # Navigation artwork lives alongside the high-resolution title masters.
    sources = [(p, args.output/p.relative_to('data/img_highres'), False)
               for p in sorted(Path('data/img_highres').rglob('*.iff'))]
    sources += [(p, args.launcher_output/p.name, p.name.startswith('skin-'))
                for p in sorted(Path('data/avs-highres').glob('*.iff'))
                if p.name not in {'skin-bg-highres.iff', 'AmigaVisionBG.iff'} and not p.stem.lower().endswith('-qr2')]
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
        identity = (digest, skin, source.parent.name.lower() == 'qr' or source.stem.lower().endswith('-qr'))
        if identity in representatives:
            duplicates.append((representatives[identity], dest))
        else:
            representatives[identity] = dest
            jobs.append((str(source), str(dest), skin))
    print(f'Converting {len(jobs)} unique ECS images; copying {len(duplicates)} duplicates; reusing {len(sources)-len(jobs)-len(duplicates)}', flush=True)
    with ProcessPoolExecutor(max_workers=args.jobs) as executor:
        for index, _ in enumerate(executor.map(convert, jobs, chunksize=8), 1):
            if index % 500 == 0:
                print(f'Converted {index}/{len(jobs)}', flush=True)
    import shutil
    for representative, dest in duplicates:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(representative, dest)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = manifest_path.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(manifest, indent=2)+'\n')
    temporary.replace(manifest_path)
    print(f'Static ECS artwork ready: {len(sources)} images', flush=True)


if __name__ == '__main__':
    main()
