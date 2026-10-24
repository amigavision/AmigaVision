import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import Mock, patch

import fetch_windows_installer as fetch


class WindowsInstallerTests(unittest.TestCase):
    def test_explicit_installer_requires_no_authentication(self):
        with tempfile.TemporaryDirectory() as directory:
            installer = Path(directory) / fetch.INSTALLER_NAME
            installer.write_bytes(b"MZ test installer")
            with patch.object(fetch, "GitHub", side_effect=AssertionError("Network access")):
                self.assertEqual(fetch.resolve_windows_installer(installer, directory), installer.resolve())

    def test_repository_copy_requires_no_authentication(self):
        with tempfile.TemporaryDirectory() as directory:
            installer = Path(directory) / fetch.INSTALLER_NAME
            installer.write_bytes(b"MZ test installer")
            with patch.object(fetch, "LOCAL_INSTALLER", installer), \
                 patch.object(fetch, "GitHub", side_effect=AssertionError("Network access")):
                self.assertEqual(fetch.resolve_windows_installer(None, directory), installer.resolve())

    def test_rejects_non_executable(self):
        with tempfile.TemporaryDirectory() as directory:
            installer = Path(directory) / "invalid.exe"
            installer.write_bytes(b"Not an executable")
            with self.assertRaises(ValueError):
                fetch.validate_installer(installer)

    def test_skips_failed_non_main_and_expired_builds(self):
        client = Mock()
        runs = [dict(id=i, head_branch=branch, conclusion=status) for i, branch, status in (
            (1, "main", "failure"), (2, "feature", "success"),
            (3, "main", "success"), (4, "main", "success"))]
        client.json.side_effect = [
            {"workflow_runs": runs},
            {"artifacts": [dict(id=30, name=fetch.ARTIFACT_NAME, expired=True)]},
            {"artifacts": [dict(id=40, name=fetch.ARTIFACT_NAME, expired=False)]},
        ]
        run, artifact = fetch.latest_artifact(client)
        self.assertEqual((run["id"], artifact["id"]), (4, 40))
        self.assertEqual(client.json.call_count, 3)

    def test_download_extracts_only_expected_executable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            client = Mock()

            def download(endpoint, destination):
                with zipfile.ZipFile(destination, "w") as archive:
                    archive.writestr(fetch.INSTALLER_NAME, b"MZ downloaded installer")
                    archive.writestr("unexpected.txt", "Do not extract")

            client.download.side_effect = download
            with patch.object(fetch, "LOCAL_INSTALLER", root / "missing.exe"), \
                 patch.object(fetch, "GitHub", return_value=client), \
                 patch.object(fetch, "latest_artifact", return_value=(
                     {"html_url": "https://github.com/amigavision/AmigaVision/actions/runs/1"}, {"id": 2})):
                installer = fetch.resolve_windows_installer(None, root)
            self.assertEqual(installer.read_bytes(), b"MZ downloaded installer")
            self.assertFalse((root / "unexpected.txt").exists())

    def test_no_matching_artifact_reports_error(self):
        client = Mock()
        client.json.return_value = {"workflow_runs": []}
        with self.assertRaisesRegex(RuntimeError, "No successful main Windows build"):
            fetch.latest_artifact(client)


if __name__ == "__main__":
    unittest.main()
