"""Regression checks for archive promotion and stable title IDs."""
import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from PIL import Image

from ags_index import renamed_container_rows
from ags_screenshot import iff_screenshot
from repair_hires_palettes import decode, read_chunks
from pull_archives import is_non_aga_whdload_path
from promote_newer_archives import (
    archive_revision_key, choose_preferred_new_candidate, parse_archive_name,
    promote_archives, report_pending_archives, suffixes_compatible, version_key, find_candidates,
)


class ArchiveUpdatesTest(unittest.TestCase):
    def test_normal_update_does_not_promote_ecs_review_staging(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder)
            review = source / 'ecs-backfill'; review.mkdir()
            (review / 'Example_v2.0.lha').write_bytes(b'review')
            (source / 'Other_v1.0.lha').write_bytes(b'normal')
            _, basenames = find_candidates(source)
            self.assertEqual(set(basenames), {'Other_v1.0.lha'})

    def test_ecs_backfill_excludes_other_packaging_and_aga(self):
        root = '/WHDLoad/Commodore Amiga - '
        for collection, archive in [
            ('WHDLoad - Games', 'Example_v1.0.lha'),
            ('WHDLoad - Games', 'FirstSamurai_v2.1_A1200Version_NONAGA.lha'),
            ('WHDLoad - Demos', 'Example_v1.0_ECS.lha'),
        ]:
            self.assertTrue(is_non_aga_whdload_path(root + collection + '/E/' + archive))
        for collection, archive in [
            ('JST - Games', 'Example_v1.0.lha'),
            ('HD Loaders - Games', 'Example_v1.0.lha'),
            ('WHDLoad - Games', 'Example_v1.0_JST.lha'),
            ('WHDLoad - Games', 'Example_v1.0_AGA.lha'),
            ('WHDLoad - Games', 'Example_v1.0_CD32.lha'),
        ]:
            self.assertFalse(is_non_aga_whdload_path(root + collection + '/E/' + archive))

    def test_dated_revisions(self):
        old = parse_archive_name("Castlevania_v1.2_AGA_November2025.lha")
        new = parse_archive_name("Castlevania_v1.2_AGA_September2026.lha")
        self.assertGreater(archive_revision_key(new), archive_revision_key(old))
        self.assertEqual(choose_preferred_new_candidate([(Path("old"), old), (Path("new"), new)])[0], Path("new"))

    def test_variants_remain_separate(self):
        for left, right in [("_AGA", "_AGA_2358"), ("_Fr_2236", "_Fr")]:
            self.assertTrue(suffixes_compatible(left, right))
        for left, right in [("_AGA", "_AGA_68040"), ("_De", ""), ("_AGA", ""),
                            ("_1MB", "_2MB"), ("_AGA", "_AGA_Decrunched")]:
            self.assertFalse(suffixes_compatible(left, right))
        self.assertEqual(parse_archive_name("MissionAndromeda_v1.1.De.lha")["suffix"], "_De")
        self.assertEqual(parse_archive_name("DoubleDragon_Beta4_AGA.lha")["version"], "Beta4")
        self.assertLess(version_key("Beta4"), version_key("1.0"))

    def test_promotion_preserves_previous_package_and_reports_unknowns(self):
        with tempfile.TemporaryDirectory() as folder:
            titles = Path(folder)
            stage = titles / "manual-downloads"
            game = titles / "game"
            stage.mkdir()
            game.mkdir()
            old = "Example_v1.2_AGA_November2025.lha"
            new = "Example_v1.2_AGA_September2026.lha"
            (game / old).write_bytes(b"old")
            (stage / new).write_bytes(b"new")
            promoted, added, _, _, pending = promote_archives(titles, stage, apply=True)
            self.assertEqual((len(promoted), len(added), len(pending)), (1, 0, 0))
            self.assertEqual((game / new).read_bytes(), b"new")
            self.assertEqual((game / "retired" / old).read_bytes(), b"old")
            (stage / "UnknownPackage.lha").write_bytes(b"unknown")
            with contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(report_pending_archives(titles, stage), 1)
            self.assertIn("UnknownPackage.lha", output.getvalue())

    def test_renamed_container_keeps_existing_id(self):
        row = {"id": "game--oldname--oldname", "archive_path": "game/NewName_v1.1.lha",
               "slave_path": "NewName/NewName.slave"}
        arc = dict(row, id="game--newname--newname")
        with tempfile.TemporaryDirectory() as folder:
            package = Path(folder) / row["archive_path"]
            package.parent.mkdir()
            package.touch()
            matches = renamed_container_rows({row["id"]: row}, {arc["id"]: arc}, folder)
        self.assertEqual(matches[arc["id"]], [row])

    def test_new_screenshots_use_rle_and_keep_black_padding(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "source.png"
            Image.new("RGB", (320, 256), "white").save(source)
            blob, expected = iff_screenshot(source, 240, (640, 512), (640, 512), (360, 288))
            output = Path(folder) / "image.iff"
            output.write_bytes(blob)
            chunks = read_chunks(output)
            image, _ = decode(chunks)
        self.assertEqual(chunks[b"BMHD"][10], 1)
        self.assertEqual(chunks[b"CMAP"][:3], bytes(3))
        self.assertEqual(image.size, (360, 288))
        self.assertEqual(image.tobytes(), expected.tobytes())
        self.assertLess(max(image.tobytes()), 240)


if __name__ == "__main__":
    unittest.main()
