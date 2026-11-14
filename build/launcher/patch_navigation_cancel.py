#!/usr/bin/env python3
"""Pair menu navigation cancellation with generation-checked helper rendering.

Apply after the Workbench exit menu patch and the helper QUIT patch. The new
command 7 does no I/O in the software interrupt. The helper's normal task owns
IFF cleanup and discards stale staging before returning to its native loop.
"""
import argparse
import hashlib
from pathlib import Path
import struct
import subprocess
import tempfile

TAG = b'AVSCANC1'
BASELINES = {
    'menu': '38d14ff46fd9b86c4c6d5ea584aee1de9924a3bcb4edc4b0fdde2ebaf2d03ddf',
    'helper': '248169abdde01ada281279e07b4757254e7774ababbd7774bb705a024cd1b4e7',
}
HOOKS = {
    'menu': ((0x4c08, '600071b6'), (0x6e12, '20472068000c')),
    'helper': (
        (0x3a0c, '7006b085'), (0x39c4, '206d0008'),
        (0x3e38, '202dffe4'), (0x4208, '2f2dffb0'),
        (0x4222, '206dfffc'), (0x4254, '206dffc4'),
        (0x4276, '60001400'), (0x43fa, '60000fe2'),
        (0x45dc, '600013744e71'),
        (0x3340, '206d0010'), (0x349a, '206d0010'),
        (0x37b0, '206d0010'),
        (0x4440, '2f2dffb8'), (0x445a, '206dffe0'),
        (0x448c, '4feffff8'), (0x4572, '206dffc4'),
    ),
}


def remove_patch(data, kind):
    end = 32 + struct.unpack_from('>I', data, 28)[0]*4
    if data[end-12:end-4] != TAG:
        return data
    size = struct.unpack_from('>I', data, end-4)[0]
    result = bytearray(data[:32+size] + data[end:])
    for offset in (20, 28):
        struct.pack_into('>I', result, offset, size//4)
    for address, original in HOOKS[kind]:
        result[32+address:32+address+len(bytes.fromhex(original))] = bytes.fromhex(original)
    if hashlib.sha256(result).hexdigest() != BASELINES[kind]:
        raise ValueError('Unknown navigation-cancel baseline')
    return bytes(result)


def patch(data, kind, assembler='/tmp/av-vasm/vasmm68k_mot'):
    if remove_patch(data, kind) != data:
        return data
    if hashlib.sha256(data).hexdigest() != BASELINES[kind]:
        raise ValueError(f'Unknown {kind}; revalidate navigation hooks')
    size = struct.unpack_from('>I', data, 28)[0]*4
    end = 32+size
    defines = [f'-DPATCH_BASE={size}']
    def branch_target(address):
        return address+2+struct.unpack_from('>h', data, 32+address+2)[0]
    if kind == 'menu':
        defines += ['-DMENU_PATCH=1', f'-DOLD_NAVIGATION={branch_target(0x4c08)}']
    else:
        # Peel the outer QUIT footer only to locate the compositor's table.
        composite_end = 32 + struct.unpack_from('>I', data, end-4)[0]
        assert data[composite_end-12:composite_end-4] == b'QRCOMP06'
        composite_base = struct.unpack_from('>I', data, composite_end-4)[0]
        state = composite_base + struct.unpack_from('>I', data, 32+composite_base+24)[0]
        defines += [f'-DCOMPOSITE_STATE={state}',
                    f'-DOLD_STAGE={branch_target(0x4276)}',
                    f'-DOLD_PUBLISH={branch_target(0x45dc)}']
    for address, expected in HOOKS[kind]:
        assert data[32+address:32+address+len(bytes.fromhex(expected))] == bytes.fromhex(expected), hex(address)
    with tempfile.TemporaryDirectory() as temp:
        output = Path(temp)/'cancel.bin'
        subprocess.run([assembler, '-Fbin', '-m68000', '-quiet', *defines,
                        '-o', str(output), str(Path(__file__).with_name('navigation_cancel.s'))], check=True)
        blob = output.read_bytes()
    entries = struct.unpack_from('>' + 'I' * (len(HOOKS[kind])+1), blob)
    result = bytearray(data[:end]+blob+data[end:])
    for offset in (20, 28):
        struct.pack_into('>I', result, offset, (size+len(blob))//4)
    for (address, expected), entry in zip(HOOKS[kind], entries):
        original = bytes.fromhex(expected)
        replacement = struct.pack('>Hh', 0x6000, size+entry-(address+2))
        replacement += bytes.fromhex('4e71')*((len(original)-4)//2)
        result[32+address:32+address+len(original)] = replacement
    return bytes(result)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('kind', choices=BASELINES)
    parser.add_argument('input', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.write_bytes(patch(args.input.read_bytes(), args.kind))
