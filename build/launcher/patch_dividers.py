#!/usr/bin/env python3
"""Append menu layout support to known AVS binaries; preserve HUNK relocations."""
from pathlib import Path
import argparse
import hashlib
import struct
import subprocess
import tempfile

BASELINES = {
    'avs': '67e88746564f5448bfd583741523dac7316525c341636cf5ebf0bba897df5431',
    'avs-ecs': '5f73a946e70d8f25a8c9f334556d353901ca19392e09ddea4191509183193843',
    'avs-highres': '79a7d4398111171d27b8c461cff996655635416b7e34a3a0168e80df8283824e',
}


def remove_previous_patch(data, end, version):
    """Recover the validated baseline when upgrading earlier divider prototypes."""
    base = struct.unpack_from('>I', data, end - (20 if version == 1 else 24 if version in (3, 4) else 36 if version in (7, 8) else 40 if version == 9 else 28))[0]
    result = bytearray(data[:32 + base] + data[end:])
    for offset in (20, 28):
        struct.pack_into('>I', result, offset, base // 4)
    for offset, original in [(0x2700, '6000fefe'), (0x6b38, '4e550000'),
                             (0x635a, 'b0ad0010'), (0x6a92, '4eaeffc4'),
                             (0x2ae2, '4e914a80')]:
        result[offset:offset + 4] = bytes.fromhex(original)
    if base == 0xa46c:
        result[0x9250:0x9254] = bytes.fromhex('4eaeffbe')
        result[0x6d62:0x6d66] = bytes.fromhex('4eaefda2')
    else:
        struct.pack_into('>Hh', result, 0x9250, 0x6100, 0xa640 - (0x9250 - 30))
        struct.pack_into('>Hh', result, 0x6d62, 0x6100, 0xa4b4 - (0x6d62 - 30))
        struct.pack_into('>Hh', result, 0x6cb4, 0x6100, 0xa480 - (0x6cb4 - 30))
        result[0xa54e:0xa552] = bytes.fromhex('4eaeffdc')
        result[0xa48c:0xa494] = bytes.fromhex('0000001400000048')
    return bytes(result)


def patch(data, assembler):
    end = 32 + struct.unpack_from('>I', data, 28)[0] * 4
    if data[end - 52:end - 44] == b'AVSDIV10':
        base, *entries = struct.unpack_from('>11I', data, end - 44)
        return data, base, tuple(entries)
    if data[end - 48:end - 40] == b'AVSDIV09':
        data = remove_previous_patch(data, end, 9)
    elif data[end - 44:end - 36] == b'AVSDIV08':
        data = remove_previous_patch(data, end, 8)
    elif data[end - 44:end - 36] == b'AVSDIV07':
        data = remove_previous_patch(data, end, 7)
    elif data[end - 36:end - 28] == b'AVSDIV06':
        data = remove_previous_patch(data, end, 6)
    elif data[end - 36:end - 28] == b'AVSDIV05':
        data = remove_previous_patch(data, end, 5)
    elif data[end - 32:end - 24] == b'AVSDIV04':
        data = remove_previous_patch(data, end, 4)
    elif data[end - 32:end - 24] == b'AVSDIV03':
        data = remove_previous_patch(data, end, 3)
    elif data[end - 36:end - 28] == b'AVSDIV02':
        data = remove_previous_patch(data, end, 2)
    elif data[end - 28:end - 20] == b'AVSDIV01':
        data = remove_previous_patch(data, end, 1)
    if hashlib.sha256(data).hexdigest() not in BASELINES.values():
        raise ValueError('Unknown launcher baseline; inspect instruction offsets before patching')
    for offset, expected in [(0x2700, '6000fefe'), (0x6b38, '4e550000'),
                             (0x635a, 'b0ad0010'), (0x6a92, '4eaeffc4'),
                             (0x2ae2, '4e914a80')]:
        assert data[offset:offset + 4] == bytes.fromhex(expected), hex(offset)
    old_close = data[0x9250:0x9254]
    assert old_close[:2] == bytes.fromhex('6100') or old_close == bytes.fromhex('4eaeffbe')
    old_select = data[0x6d62:0x6d66]
    assert old_select[:2] == bytes.fromhex('6100') or old_select == bytes.fromhex('4eaefda2')
    base = struct.unpack_from('>I', data, 28)[0] * 4
    args = [assembler, '-Fbin', '-m68000', '-quiet', f'-DPATCH_BASE={base}']
    if old_select[:2] == bytes.fromhex('6100'):
        original = 0x6d62 - 30 + struct.unpack('>h', old_select[2:])[0]
        args.append(f'-DORIGINAL_SELECT={original}')
        args.append('-DDIRECT_NAV=1')
    if old_close[:2] == bytes.fromhex('6100'):
        original = 0x9250 - 30 + struct.unpack('>h', old_close[2:])[0]
        args.append(f'-DORIGINAL_CLOSE={original}')
    with tempfile.TemporaryDirectory() as folder:
        output = Path(folder) / 'dividers.bin'
        subprocess.run(args + ['-o', str(output), str(Path(__file__).with_name('dividers.s'))], check=True)
        blob = output.read_bytes()
    entries = struct.unpack_from('>10I', blob)
    result = bytearray(data[:32 + base] + blob + data[32 + base:])
    for offset in (20, 28):
        struct.pack_into('>I', result, offset, (base + len(blob)) // 4)
    # The hi-res overlay's build-time entry table is not read at runtime.
    # Its first slots supply nearby trampolines for the earlier parser hooks.
    trampoline = 0xa46c
    for offset, index, opcode in [(0x2700, 0, 0x6000), (0x6b38, 1, 0x6000),
                                  (0x635a, 2, 0x6100), (0x6d62, 3, 0x6100),
                                  (0x2ae2, 4, 0x6100), (0x6a92, 5, 0x6100), (0x9250, 7, 0x6100)]:
        target = base + entries[index]
        if target - (offset - 30) > 32767:
            assert data[trampoline + 32:trampoline + 36] in (bytes.fromhex('00000014'), bytes.fromhex('00000048'))
            struct.pack_into('>Hh', result, trampoline + 32, 0x6000, target - (trampoline + 2))
            target = trampoline
            trampoline += 4
        struct.pack_into('>Hh', result, offset, opcode, target - (offset - 30))
    if old_select[:2] == bytes.fromhex('6100'):
        assert data[0xa54e:0xa552] == bytes.fromhex('4eaeffdc')
        target = base + entries[9]
        struct.pack_into('>Hh', result, 0x6cb4, 0x6100, target - (0x6cb4 - 30))
        target = base + entries[8]
        struct.pack_into('>Hh', result, 0xa54e, 0x6100, target - (0xa54e - 30))
    return bytes(result), base, entries


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('binary', type=Path)
    parser.add_argument('--assembler', default='/tmp/av-vasm/vasmm68k_mot')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result, _, _ = patch(args.binary.read_bytes(), args.assembler)
    args.output.write_bytes(result)
    print(f'{args.output}: {len(result)} bytes')
