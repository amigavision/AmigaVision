import tempfile
from pathlib import Path
import unittest
from ags_artwork import is_nsfw, install_nsfw_thumbnail


class ArtworkTests(unittest.TestCase):
    def test_tags_are_exact_and_case_insensitive(self):
        self.assertTrue(is_nsfw({'subcategory': 'Slide Show, nsFW'}))
        self.assertFalse(is_nsfw({'subcategory': 'Not NSFW'}))
        self.assertFalse(is_nsfw({}))

    def test_each_resolution_replaces_all_slides_and_qr_with_one_image(self):
        for profile, root in [('medium', 'img'), ('hires', 'img_highres'), ('ecs', 'img_ecs')]:
            with self.subTest(profile=profile), tempfile.TemporaryDirectory() as tmp:
                base = Path(tmp) / 'Title (OCS)[en]'
                for suffix in ['.iff', '-1.iff', '-9.iff', '-10.iff', '-QR.iff']:
                    Path(str(base) + suffix).write_bytes(b'old')
                other = Path(tmp) / 'Another title.iff'
                other.write_bytes(b'unrelated')
                install_nsfw_thumbnail(base, profile)
                self.assertEqual(sorted(p.name for p in Path(tmp).glob('*.iff')),
                                 [other.name, base.name + '.iff'])
                self.assertEqual(Path(str(base) + '.iff').read_bytes(),
                                 Path('data', root, 'NSFW.iff').read_bytes())
                self.assertEqual(other.read_bytes(), b'unrelated')


if __name__ == '__main__':
    unittest.main()
