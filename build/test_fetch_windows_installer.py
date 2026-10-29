import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import fetch_windows_installer as fetch


class WindowsInstallerTests(unittest.TestCase):
    def test_repository_copy_and_explicit_override(self):
        with tempfile.TemporaryDirectory() as directory:
            local = Path(directory) / fetch.INSTALLER_NAME
            local.write_bytes(b"MZ repository installer")
            override = Path(directory) / "override.exe"
            override.write_bytes(b"MZ override installer")
            with patch.object(fetch, "LOCAL_INSTALLER", local):
                self.assertEqual(fetch.resolve_windows_installer(None), local.resolve())
                self.assertEqual(fetch.resolve_windows_installer(override), override.resolve())

    def test_missing_installer_gives_local_copy_instructions(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(fetch, "LOCAL_INSTALLER", Path(directory) / "missing.exe"):
                with self.assertRaisesRegex(FileNotFoundError, "Copy the tested Windows build"):
                    fetch.resolve_windows_installer(None)

    def test_rejects_non_executable(self):
        with tempfile.TemporaryDirectory() as directory:
            installer = Path(directory) / "invalid.exe"
            installer.write_bytes(b"Not an executable")
            with self.assertRaises(ValueError):
                fetch.validate_installer(installer)


if __name__ == "__main__":
    unittest.main()
