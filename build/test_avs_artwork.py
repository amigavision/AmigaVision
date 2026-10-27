import tempfile
from pathlib import Path
import unittest
from avs_artwork import is_nsfw, install_nsfw_thumbnail
from avs_artwork import validate_hires_artwork
from avs_screenshot import iff_screenshot
from PIL import Image


class ArtworkTests(unittest.TestCase):
    def test_converter_rejects_noncanonical_hires_sizes(self):
        for size in [(360, 288), (404, 288), (360, 280)]:
            with self.subTest(size=size), self.assertRaisesRegex(ValueError, 'required 404x280'):
                iff_screenshot('unused.png', 240, (640, 512), size, size)

    def test_conversion_and_build_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'source.png'
            Image.new('RGB', (640, 512), 'red').save(source)
            for size in [(404, 280), (320, 128)]:
                blob, image = iff_screenshot(source, 240, (640, 512), size, size)
                self.assertEqual(image.size, size)
                (root / 'thumbnail.iff').write_bytes(blob)
                if size == (404, 280):
                    validate_hires_artwork(root)
                else:
                    with self.assertRaisesRegex(ValueError, 'required 404x280'):
                        validate_hires_artwork(root)
            (root / 'thumbnail.iff').rename(root / 'manual-qr.iff')
            validate_hires_artwork(root)

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
