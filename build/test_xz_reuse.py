import hashlib
import json
import lzma
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import xz_reuse as xz


@unittest.skipUnless(shutil.which('xz'), 'xz required')
class ReuseTests(unittest.TestCase):
    def fixture(self, root):
        raw = b'RDSK' + (bytes(range(256)) * (xz.BLOCK_SIZE // 256 * 2 + 1))[4:2*xz.BLOCK_SIZE+123]
        source = root / 'source.hdf'; source.write_bytes(raw)
        seed, manifest = root / 'seed.xz', root / 'hashes.json'
        xz.compress_seed(source, seed, manifest)
        return source, seed, manifest

    def test_capture_hashes_reuse_without_seed_decode_and_single_stream(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); source, seed, manifest = self.fixture(root)
            raw = source.read_bytes(); metadata = json.loads(manifest.read_text())
            self.assertEqual(metadata['hashes'], [hashlib.sha256(raw[i:i+xz.BLOCK_SIZE]).hexdigest()
                                                for i in range(0, len(raw), xz.BLOCK_SIZE)])
            changed = bytearray(raw); changed[xz.BLOCK_SIZE+100:xz.BLOCK_SIZE+108] = b'patched!'
            target = root / 'patched'; target.write_bytes(changed)
            prefix = root / 'prefix'; prefix.write_bytes(b'boot prefix' * 700)
            suffix = root / 'suffix'; suffix.write_bytes(b'filesystem tail')
            output = root / 'release.xz'
            segments = [xz.Segment(prefix, 0, prefix.stat().st_size),
                        xz.Segment(target, 0, len(changed), True),
                        xz.Segment(None, 0, 513), xz.Segment(suffix, 0, suffix.stat().st_size)]
            # A manifest consumer must never decode a seed block in Python.
            with patch.object(xz.lzma, 'decompress', side_effect=AssertionError('Seed decoded')):
                result = xz.reuse(seed, manifest, output, segments)
            expected = prefix.read_bytes() + changed + bytes(513) + suffix.read_bytes()
            self.assertEqual(lzma.decompress(output.read_bytes()), expected)
            self.assertEqual(result['changed_blocks'], 1)
            self.assertEqual(result['reused_blocks'], 2)
            self.assertEqual(result['seed_decoded_bytes'], 0)
            if shutil.which('7zz'):
                self.assertEqual(subprocess.check_output(['7zz', 'x', '-so', str(output)]), expected)
            listing = subprocess.check_output(['xz', '--robot', '-l', str(output)], text=True)
            self.assertIn('file\t1\t', listing)
            before, after = xz.index(seed), xz.index(output)
            with seed.open('rb') as a, output.open('rb') as b:
                for i in (0, 2):
                    a.seek(before[i].offset); b.seek(after[i+1].offset)
                    self.assertEqual(a.read(before[i].packed_size), b.read(after[i+1].packed_size))
                for block in after:
                    b.seek(block.offset+1)
                    self.assertEqual(b.read(1)[0] & 0xc0, 0xc0, 'Block sizes required for threaded decoding')

    def test_stale_missing_and_wrong_size_seeds_are_unavailable(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); source, seed, manifest = self.fixture(root)
            output = root / 'release'; output.write_bytes(b'old release')
            segments = [xz.Segment(source, 0, source.stat().st_size, True)]
            missing = root / 'missing'
            with self.assertRaises(xz.ReuseUnavailable): xz.reuse(seed, missing, output, segments)
            manifest.write_text('{}')
            with self.assertRaises(xz.ReuseUnavailable): xz.reuse(seed, manifest, output, segments)
            self.assertEqual(output.read_bytes(), b'old release')

    def test_forged_hash_mapping_detected_by_full_verification(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); source, seed, manifest = self.fixture(root)
            target = root / 'target'; raw = bytearray(source.read_bytes()); raw[20] ^= 1; target.write_bytes(raw)
            metadata = json.loads(manifest.read_text())
            metadata['hashes'][0] = hashlib.sha256(raw[:xz.BLOCK_SIZE]).hexdigest()
            manifest.write_text(json.dumps(metadata))
            output = root / 'release'; output.write_bytes(b'old release')
            with self.assertRaisesRegex(ValueError, 'differs from intended'):
                xz.reuse(seed, manifest, output, [xz.Segment(target, 0, len(raw), True)])
            self.assertEqual(output.read_bytes(), b'old release')
            self.assertFalse(list(root.glob('*.partial.*')))

    def test_corrupt_packed_seed_cannot_publish(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); source, seed, manifest = self.fixture(root)
            with seed.open('r+b') as file:
                file.seek(80); byte = file.read(1); file.seek(80); file.write(bytes([byte[0] ^ 1]))
            metadata = json.loads(manifest.read_text()); metadata['seed_stamp'] = xz.stamp(seed)
            manifest.write_text(json.dumps(metadata))
            output = root / 'release'; output.write_bytes(b'old release')
            with self.assertRaises(subprocess.CalledProcessError):
                xz.reuse(seed, manifest, output, [xz.Segment(source, 0, source.stat().st_size, True)])
            self.assertEqual(output.read_bytes(), b'old release')
            self.assertFalse(list(root.glob('*.partial.*')))

    def test_source_changes_during_seed_creation_preserve_old_archive(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); source, seed, manifest = self.fixture(root)
            old = seed.read_bytes(); popen = subprocess.Popen

            def change(*args, **kwargs):
                stat = source.stat(); os.utime(source, ns=(stat.st_atime_ns, stat.st_mtime_ns+1000000))
                return popen(*args, **kwargs)

            with patch.object(xz.subprocess, 'Popen', side_effect=change):
                with self.assertRaisesRegex(ValueError, r'Source changed during compression:.*before:.*after:'):
                    xz.compress_seed(source, seed, manifest)
            self.assertEqual(seed.read_bytes(), old)

    def test_compressor_layout_failure_is_distinct_from_source_change(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); source, seed, manifest = self.fixture(root)
            old = seed.read_bytes()
            read_index = xz.index
            with patch.object(xz, 'index', side_effect=lambda path: read_index(path)[:-1]):
                with self.assertRaisesRegex(ValueError, r'Compressor block layout differs: .*blocks vs .*captured hashes'):
                    xz.compress_seed(source, seed, manifest)
            self.assertEqual(seed.read_bytes(), old)
            self.assertFalse(list(root.glob('*.partial.*')))


if __name__ == '__main__': unittest.main()
