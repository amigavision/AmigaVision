import errno
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import package_distros


class PackagingCloneTests(unittest.TestCase):
    @unittest.skipUnless(sys.platform == "darwin", "macOS native clonefile")
    def test_native_clone_preserves_metadata_and_writes_are_independent(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source image.hdf"
            source.write_bytes(b"original" * 1024)
            source.chmod(0o640)
            os.utime(source, (1700000000, 1700000000))
            destination = root / "staging/image.hdf"
            clonefile = package_distros.get_clonefile()
            self.assertIsNotNone(clonefile)
            with patch.object(package_distros, "get_clonefile", return_value=clonefile), \
                 patch.object(package_distros.shutil, "copy2", side_effect=AssertionError("Full copy used")):
                package_distros.clone_or_copy_file(source, destination)
            self.assertEqual(source.read_bytes(), destination.read_bytes())
            self.assertNotEqual(source.stat().st_ino, destination.stat().st_ino)
            self.assertEqual(source.stat().st_mode, destination.stat().st_mode)
            self.assertEqual(source.stat().st_mtime_ns, destination.stat().st_mtime_ns)
            with destination.open("r+b") as image:
                image.write(b"modified")
            self.assertTrue(source.read_bytes().startswith(b"original"))
            self.assertTrue(destination.read_bytes().startswith(b"modified"))

    def test_unsupported_clone_falls_back_to_independent_copy(self):
        for error in (errno.EXDEV, errno.ENOTSUP):
            with self.subTest(error=error), tempfile.TemporaryDirectory() as temporary:
                source = Path(temporary) / "source"
                destination = Path(temporary) / "destination"
                source.write_bytes(b"original")
                def unsupported(*args):
                    raise OSError(error, "Clone unavailable")
                with patch.object(package_distros, "get_clonefile", return_value=unsupported):
                    package_distros.clone_or_copy_file(source, destination)
                self.assertEqual(destination.read_bytes(), b"original")
                destination.write_bytes(b"modified")
                self.assertEqual(source.read_bytes(), b"original")

    def test_unexpected_clone_error_is_not_hidden_by_copy(self):
        with tempfile.TemporaryDirectory() as temporary:
            def broken(*args):
                raise OSError(errno.EIO, "I/O failure")
            with patch.object(package_distros, "get_clonefile", return_value=broken), \
                 patch.object(package_distros.shutil, "copy2") as copy:
                with self.assertRaises(OSError):
                    package_distros.clone_or_copy_file(Path(temporary) / "source", Path(temporary) / "dest")
                copy.assert_not_called()


if __name__ == "__main__":
    unittest.main()
