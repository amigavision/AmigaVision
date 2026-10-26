from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

import avs_util
from avs_image_update import amiga_path


class LhaExtractTests(unittest.TestCase):
    def test_root_directory_entries_do_not_become_escaped_dot_paths(self):
        names = ['./', '.', 'Tutankham/', './Tutankham/Tutankham']
        archive = SimpleNamespace(
            infolist=lambda: [SimpleNamespace(filename=n) for n in names],
            read=lambda name: b'game executable',
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            destination = root / 'DH1/WHD/N'
            with patch.object(avs_util, 'LhaFile', return_value=archive), \
                    patch.object(avs_util, 'native_lha_extract') as fallback:
                avs_util.lha_extract('test.lha', str(destination))
            fallback.assert_not_called()
            self.assertEqual((destination / 'Tutankham/Tutankham').read_bytes(),
                             b'game executable')
            self.assertFalse((destination / '%2e').exists())
            for path in root.rglob('*'):
                if len(path.relative_to(root).parts) > 1:
                    amiga_path(path.relative_to(root).as_posix())


if __name__ == '__main__':
    unittest.main()
