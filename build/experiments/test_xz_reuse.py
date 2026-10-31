import hashlib
import lzma
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import xz_reuse


@unittest.skipUnless(shutil.which('xz'), 'xz is required')
class ReuseTests(unittest.TestCase):
    def fixture(self, root):
        raw = (bytes(range(256)) * 256 + b'plain data' * 6554) * 4
        source = root / 'source'; source.write_bytes(raw)
        seed = root / 'seed.xz'
        with seed.open('wb') as file:
            subprocess.run(['xz', '-T2', '-1', '--block-size=65536', '-c', str(source)], stdout=file, check=True)
        return raw, seed

    def test_changed_blocks_prefix_and_padding_match_independent_readers(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); raw, seed = self.fixture(root)
            changed = bytearray(raw); changed[70000:70008] = b'patched!'
            target = root / 'target'; target.write_bytes(changed)
            prefix = root / 'prefix'; prefix.write_bytes(b'boot prefix' * 200)
            output = root / 'result.xz'
            result = xz_reuse.reuse(seed, target, output, prefix, 511, workers=2)
            expected = prefix.read_bytes() + changed + bytes(511)
            self.assertEqual(lzma.decompress(output.read_bytes()), expected)
            self.assertEqual(result['changed_blocks'], 1)
            self.assertEqual(result['reused_blocks'], result['blocks'] - 1)
            self.assertEqual(result['sha256_uncompressed'], hashlib.sha256(expected).hexdigest())
            if shutil.which('7zz'):
                read = subprocess.run(['7zz', 'x', '-so', str(output)], capture_output=True, check=True)
                self.assertEqual(read.stdout, expected)
            listing = subprocess.run(['xz', '--robot', '-l', str(output)], capture_output=True, text=True, check=True)
            self.assertIn('file\t1\t', listing.stdout)  # One stream, not concatenated streams.
            # Reused compressed block bytes must be identical, not recompressed.
            old, new = xz_reuse.index(seed), xz_reuse.index(output)[1:-1]
            with seed.open('rb') as a, output.open('rb') as b:
                for i, (before, after) in enumerate(zip(old, new)):
                    if i == 1: continue
                    a.seek(before.offset); b.seek(after.offset)
                    self.assertEqual(a.read(before.packed_size), b.read(after.packed_size))

    def test_identity_and_all_changed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); raw, seed = self.fixture(root)
            for data in (raw, bytes(len(raw))):
                target = root / 'target'; target.write_bytes(data)
                output = root / 'result.xz'
                result = xz_reuse.reuse(seed, target, output, workers=1)
                self.assertEqual(lzma.decompress(output.read_bytes()), data)
                self.assertEqual(result['reused_blocks'] if data == raw else result['changed_blocks'], result['blocks'])

    def test_corruption_or_wrong_target_never_replaces_release(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); raw, seed = self.fixture(root)
            output = root / 'result.xz'; output.write_bytes(b'old release')
            target = root / 'target'; target.write_bytes(raw)
            with seed.open('r+b') as file:
                file.seek(80); value = file.read(1); file.seek(80); file.write(bytes([value[0] ^ 1]))
            with self.assertRaises(lzma.LZMAError):
                xz_reuse.reuse(seed, target, output)
            self.assertEqual(output.read_bytes(), b'old release')
            self.assertFalse(list(root.glob('*.partial.*')))
            target.write_bytes(b'wrong size')
            with self.assertRaisesRegex(ValueError, 'sizes differ'):
                xz_reuse.reuse(seed, target, output)

    def test_rejects_concatenated_streams_and_index_corruption(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); _, seed = self.fixture(root)
            single = seed.read_bytes()
            seed.write_bytes(single + single)
            with self.assertRaises(ValueError): xz_reuse.index(seed)
            broken = bytearray(single); broken[-20] ^= 1; seed.write_bytes(broken)
            with self.assertRaises(ValueError): xz_reuse.index(seed)

    def test_failed_verification_or_input_change_preserves_release(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); raw, seed = self.fixture(root)
            target = root / 'target'; target.write_bytes(raw)
            output = root / 'result.xz'; output.write_bytes(b'old release')
            with self.assertRaises(subprocess.CalledProcessError):
                xz_reuse.reuse(seed, target, output, xz=shutil.which('false'))
            self.assertEqual(output.read_bytes(), b'old release')
            popen = subprocess.Popen

            def change_input(*args, **kwargs):
                stat = target.stat()
                os.utime(target, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1000000))
                return popen(*args, **kwargs)

            with patch.object(xz_reuse.subprocess, 'Popen', side_effect=change_input):
                with self.assertRaisesRegex(ValueError, 'Input changed'):
                    xz_reuse.reuse(seed, target, output)
            self.assertEqual(output.read_bytes(), b'old release')
            self.assertFalse(list(root.glob('*.partial.*')))


if __name__ == '__main__': unittest.main()
