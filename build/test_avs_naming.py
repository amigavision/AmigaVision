"""Check the launcher naming contract across assets and staged native bases."""
from pathlib import Path
import tempfile
import unittest

from avs_migration import migrate_staged_base, rename_reference

ROOT = Path(__file__).resolve().parent.parent


class LauncherNamingTests(unittest.TestCase):
    def test_runtime_binaries_use_matching_avs_paths_and_ports(self):
        for directory in ('avs', 'avs-highres', 'avs-ecs'):
            for binary in (ROOT / 'data' / directory).glob('AVS*'):
                data = binary.read_bytes()
                if data[:4] != bytes.fromhex('000003f3'):
                    continue
                with self.subTest(binary=binary):
                    self.assertNotIn(b'AGS', data)
                    self.assertNotIn(b'agsilport', data)
                    self.assertNotIn(b'.ags', data)
                    if binary.name in ('AVSMenu', 'AVSHelper'):
                        self.assertIn(b'AVS:AVSHelper\0', data)
                        self.assertIn(b'avsilport\0', data)
                    if binary.name == 'AVSMenu':
                        self.assertIn(b'AVS:AVS.conf\0', data)
                        self.assertIn(b'.avs', data)

    def test_configs_resolve_their_local_artwork(self):
        for config in (ROOT / 'data').glob('avs*/AVS.conf'):
            for line in config.read_text().splitlines():
                if line.startswith(('background =', 'empty_screenshot =')):
                    value = line.split('=', 1)[1].strip()
                    self.assertTrue(value.startswith('AVS:'), value)
                    self.assertTrue((config.parent / value[4:]).is_file(), value)

    def test_staged_base_migration_is_idempotent_and_preserves_core_protocol(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for directory in ('C', 'S', 'Fonts/AGSml', 'Apps', 'Prefs/Env-Archive'):
                (root / directory).mkdir(parents=True, exist_ok=True)
            (root / 'S/ags-launch').write_text('AGS:AGS2\nags-vadjust\nMiSTer:ags_boot\nMiSTer:ags_current\n')
            (root / 'S/ags-launch.uaem').write_text('metadata')
            (root / 'C/ags-vadjust').write_bytes(b'command')
            (root / 'Fonts/AGSml.font').write_bytes(b'\0AGSml/7\0')
            (root / 'Apps/AmigaVision').write_text('AGS:AGS2\n')
            (root / 'Prefs/Env-Archive/AGSVMode').write_text('PAL')
            migrate_staged_base(root)
            migrate_staged_base(root)
            self.assertEqual((root / 'S/avs-launch').read_text(),
                             'AVS:AVS\navs-vadjust\nMiSTer:ags_boot\nMiSTer:ags_current\n')
            self.assertTrue((root / 'S/avs-launch.uaem').is_file())
            self.assertTrue((root / 'C/avs-vadjust').is_file())
            self.assertTrue((root / 'Fonts/AVSml').is_dir())
            self.assertEqual((root / 'Fonts/AVSml.font').read_bytes(), b'\0AVSml/7\0')
            self.assertTrue((root / 'Prefs/Env-Archive/AVSVMode').is_file())
            self.assertEqual((root / 'Apps/AmigaVision').read_text(), 'AVS:AVS\n')

    def test_unrelated_words_and_archive_names_are_preserved(self):
        text = 'Flags FLAGS tags TAGS Disk Mags mags--42issue1 .ags AGS2 AGSCONTENT ags_make'
        self.assertEqual(rename_reference(text),
                         'Flags FLAGS tags TAGS Disk Mags mags--42issue1 .avs AVS AVSCONTENT avs_make')


if __name__ == '__main__':
    unittest.main()
