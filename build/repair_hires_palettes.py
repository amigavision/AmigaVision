#!/usr/bin/env python3
"""Repair high-resolution ILBM palettes that overlap AGS interface colors and remove RLE compression."""
import argparse
import struct
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from PIL import Image
import iff_ilbm


def read_chunks(path):
    data = path.read_bytes()
    if data[:4] != b"FORM" or data[8:12] != b"ILBM":
        raise ValueError(f"Not an ILBM: {path}")
    chunks = {}
    pos = 12
    while pos < len(data):
        tag = data[pos:pos + 4]
        size = struct.unpack_from(">I", data, pos + 4)[0]
        chunks[tag] = data[pos + 8:pos + 8 + size]
        pos += 8 + size + size % 2
    return chunks


def decode(chunks):
    header = chunks[b"BMHD"]
    width, height = struct.unpack_from(">HH", header)
    depth, masking, compression = header[8:11]
    mode = struct.unpack(">I", chunks.get(b"CAMG", bytes(4)))[0]
    if masking or depth > 8 or mode & 0x880:
        raise ValueError("Masked, HAM or EHB images require a different decoder")
    body = chunks[b"BODY"]
    if compression == 0:
        raw = body
    elif compression == 1:
        raw = bytearray()
        pos = 0
        while pos < len(body):
            count = struct.unpack_from("b", body, pos)[0]
            pos += 1
            if count >= 0:
                raw.extend(body[pos:pos + count + 1])
                pos += count + 1
            elif count != -128:
                raw.extend(body[pos:pos + 1] * (1 - count))
                pos += 1
    else:
        raise ValueError(f"Unknown compression {compression}")
    stride = ((width + 15) // 16) * 2
    if len(raw) != height * depth * stride:
        raise ValueError("Invalid planar data size")
    # Expand each bitplane using byte lookup tables, then combine entire planes.
    # This also handles rows padded to the next 16-pixel boundary.
    combined = 0
    for plane in range(depth):
        table = [bytes(((value >> (7 - bit)) & 1) << plane for bit in range(8)) for value in range(256)]
        expanded = b"".join(
            b"".join(table[value] for value in raw[(y * depth + plane) * stride:(y * depth + plane + 1) * stride])[:width]
            for y in range(height)
        )
        combined |= int.from_bytes(expanded, "big")
    image = Image.frombytes("P", (width, height), combined.to_bytes(width * height, "big"))
    image.putpalette(chunks[b"CMAP"])
    return image, mode


def black_padding_palette(image):
    """Reserve color zero for black, including pixels outside the visible width."""
    palette = image.getpalette()
    used = set(image.tobytes())
    black = next((i for i in range(240) if palette[i * 3:i * 3 + 3] == [0, 0, 0]), None)
    if black is None:
        black = next((i for i in range(240) if i not in used), None)
        if black is None:
            image = image.convert("RGB").quantize(colors=239, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
            palette = image.getpalette()
            black = 239
        palette[black * 3:black * 3 + 3] = [0, 0, 0]
    palette[:3], palette[black * 3:black * 3 + 3] = palette[black * 3:black * 3 + 3], palette[:3]
    lookup = list(range(256))
    lookup[0], lookup[black] = black, 0
    image = image.point(lookup)
    image.putpalette(palette)
    return image


def encode_uncompressed(image, mode):
    """Pack eight pixels at a time into planar IFF rows without RLE."""
    image = black_padding_palette(image)
    width, height = image.size
    colors = max(2, max(image.tobytes()) + 1)
    palette = iff_ilbm.palette_data(image.getpalette()[:colors * 3])
    depth, bmhd, cmap, camg = iff_ilbm.header(width, height, palette, mode, 0)
    stride = ((width + 15) // 16) * 2
    pixels = image.tobytes()
    body = bytearray(height * depth * stride)
    for y in range(height):
        row = pixels[y * width:(y + 1) * width]
        for x in range(0, width, 8):
            word = int.from_bytes(row[x:x + 8].ljust(8, b"\x00"), "big")
            for plane in range(depth):
                bits = (word >> plane) & 0x0101010101010101
                body[(y * depth + plane) * stride + x // 8] = ((bits * 0x0102040810204080) >> 56) & 255
    return iff_ilbm.chunk("FORM", b"ILBM", bmhd, cmap, camg, iff_ilbm.chunk("BODY", bytes(body)))


def repair(path):
    chunks = read_chunks(path)
    source, mode = decode(chunks)
    if max(source.tobytes()) >= 240 or any(chunks[b"CMAP"][720:]):
        indexed = source.convert("RGB").quantize(colors=240, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    else:
        indexed = source
    indexed = black_padding_palette(indexed)
    assert max(indexed.getdata()) < 240
    encoded = encode_uncompressed(indexed, mode)
    temporary = path.with_suffix(".iff.tmp")
    temporary.write_bytes(encoded)
    result, _ = decode(read_chunks(temporary))
    assert result.tobytes() == indexed.tobytes()
    assert result.convert("RGB").tobytes() == indexed.convert("RGB").tobytes()
    temporary.replace(path)
    return path.name


def inspect(path):
    chunks = read_chunks(path)
    header = chunks[b"BMHD"]
    if any(chunks[b"CMAP"][720:]) or header[10] != 0:
        return path, True
    width, height = struct.unpack_from(">HH", header)
    depth = header[8]
    stride = ((width + 15) // 16) * 2
    raw = chunks[b"BODY"]
    if header[9] or depth > 8 or len(raw) != height * depth * stride:
        raise ValueError(f"Invalid uncompressed planar image: {path}")
    # AGS can display the bitmap's entire word-aligned storage width.
    # Check the actual padding pixels, not just the visible image palette.
    padding = stride * 8 - width
    if padding:
        palette = chunks[b"CMAP"]
        for y in range(height):
            tails = [int.from_bytes(raw[(y * depth + plane + 1) * stride - 2:(y * depth + plane + 1) * stride], "big") for plane in range(depth)]
            for bit in range(padding):
                index = sum(((tail >> bit) & 1) << plane for plane, tail in enumerate(tails))
                if palette[index * 3:index * 3 + 3] != b"\x00\x00\x00":
                    return path, True
    if depth == 8:
        # Indices 240-255 have all four upper bitplanes set at the same pixel.
        for y in range(height):
            upper = (1 << (stride * 8)) - 1
            for plane in range(4, 8):
                start = (y * depth + plane) * stride
                upper &= int.from_bytes(raw[start:start + stride], "big")
            if upper:
                return path, True
    return path, False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=Path("data/img_highres"))
    parser.add_argument("--pattern", default="*.iff")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    files = sorted(args.directory.rglob(args.pattern))
    affected = []
    print(f"Inspecting palettes and pixel indices in {len(files)} IFFs", flush=True)
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for count, (path, unsafe) in enumerate(pool.map(inspect, files, chunksize=16), 1):
            if unsafe:
                affected.append(path)
            if count % 2000 == 0 or count == len(files):
                print(f"Inspected {count}/{len(files)}; {len(affected)} conflicts", flush=True)
        if args.verify_only:
            if affected:
                raise SystemExit(f"FAIL: {len(affected)} unsafe palettes")
            print("PASS: all screenshot indices are below 240, reserved entries are unused, bitmap padding is black, and all IFFs are uncompressed", flush=True)
            return
        print(f"Repairing {len(affected)} palettes", flush=True)
        for count, _ in enumerate(pool.map(repair, affected, chunksize=4), 1):
            if count % 200 == 0 or count == len(affected):
                print(f"Repaired {count}/{len(affected)}", flush=True)
    print(f"Repaired {len(affected)} palettes", flush=True)


if __name__ == "__main__":
    main()
