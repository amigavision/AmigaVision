#!/usr/bin/env python3
"""Allow the AGA overlay QR to redraw after every screenshot; use existing cyan skin pen 244.

Only for the validated v6 high-resolution helper, not ECS/medium-resolution.
The QR now lives within the screenshot rectangle. Its old same-entry suppression
must no longer skip drawing after a new slideshow image overwrites that rectangle.
"""
import argparse
import hashlib
from pathlib import Path

BASELINE_SHA256 = '5a494d16e5be8ee1421471f66ba142d03d509d4be72f2c3e1012ae88e3555850'
# Runtime addresses; executable code starts at file offset 32.
CHANGES = (
    (0x53a4 + 32, bytes.fromhex('660a'), bytes.fromhex('600a')),
    (0x459c + 32, bytes.fromhex('487800f0'), bytes.fromhex('487800f4')),
)


def patch(data):
    # Validate the pre-label helper when the optional caption patch is present.
    from patch_qr_label import remove_patch
    restored = bytearray(remove_patch(data))
    for offset, original, updated in CHANGES:
        current = restored[offset:offset + len(original)]
        if current not in (original, updated) and not (offset == 0x459c + 32 and current == bytes.fromhex('487800fa')):
            raise ValueError(f'Unexpected helper instruction at {offset:#x}')
        restored[offset:offset + len(original)] = original
    if hashlib.sha256(restored).hexdigest() != BASELINE_SHA256:
        raise ValueError('Unknown helper baseline; inspect it before applying offsets')
    result = bytearray(data)
    for offset, _, updated in CHANGES:
        result[offset:offset + len(updated)] = updated
    return bytes(result)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('helper', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.write_bytes(patch(args.helper.read_bytes()))
