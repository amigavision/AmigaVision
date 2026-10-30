from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import package_distros


class MiSTerSourceTests(unittest.TestCase):
    def test_stages_mister_templates_and_payload_without_unrelated_build_outputs(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            built = root / 'built'
            built.mkdir()
            hdf = built / 'AmigaVision.hdf'
            hdf.write_bytes(b'main HDF')
            (built / 'unrelated-emulator-output').write_bytes(b'excluded')
            content = root / 'distro_mister'
            content.mkdir()
            (content / 'Extras.7z').write_bytes(b'extras')
            listings = root / 'listings'
            listings.mkdir()
            (listings / 'games.txt').write_text('Games')
            args = SimpleNamespace(main_hdf=hdf, mister_root=content, listings_dir=listings,
                                   date_stamp='2026.10.31', dry_run=False)
            output = root / 'output'
            output.mkdir()
            def check(artifact, staged, tool, **kwargs):
                self.assertTrue((staged / '_Computer/Amiga.mgl').is_file())
                self.assertEqual((staged / 'Extras.7z').read_bytes(), b'extras')
                self.assertEqual((staged / 'games/Amiga/AmigaVision.hdf').read_bytes(), b'main HDF')
                self.assertEqual((staged / 'games/Amiga/listings/games.txt').read_text(), 'Games')
                self.assertFalse((staged / 'games/Amiga/Visuals').exists())
                self.assertFalse((staged / 'unrelated-emulator-output').exists())
            with patch.object(package_distros, 'archive_7z', side_effect=check) as archive:
                package_distros.package_mister(args, output, '7zz')
            archive.assert_called_once()


if __name__ == '__main__':
    unittest.main()
