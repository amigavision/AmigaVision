"""Verify ECS gradient palette isolation."""
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image
from ecs_artwork import quantize_ecs, convert
from repair_hires_palettes import decode, read_chunks

ROOT = Path(__file__).resolve().parents[1]


class ECSGradientTests(unittest.TestCase):
    def test_graphics_do_not_use_reserved_ui_slots(self):
        source = Image.fromarray(np.random.default_rng(42).integers(
            0, 256, (32, 32, 3), dtype=np.uint8))
        image = quantize_ecs(source)
        self.assertLessEqual(max(image.tobytes()), 12)
        self.assertEqual(image.getpalette()[39:48], [0,153,187,0,0,0,255,255,255])
        self.assertEqual(image.tobytes(), quantize_ecs(source).tobytes())

    def test_skin_roundtrip_avoids_gradient_pen(self):
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp)/'skin.iff'
            convert((ROOT/'data/avs-highres/skin-bg-highres.iff', destination, True))
            image, _ = decode(read_chunks(destination))
            self.assertLessEqual(set(image.tobytes()), {13,14})
            self.assertEqual(image.getpalette()[39:48], [0,153,187,0,0,0,255,255,255])



if __name__ == '__main__':
    unittest.main()
