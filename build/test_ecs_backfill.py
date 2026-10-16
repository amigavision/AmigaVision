"""Regression tests for conservative ECS metadata imports."""
import contextlib
import csv
import io
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import backfill_ecs_metadata as importer

FIELDS = ['id', 'title', 'title_short', 'redundant', 'preferred_version',
          'hardware', 'aga', 'ntsc', 'language', 'developer', 'publisher',
          'players', 'country', 'category', 'subcategory', 'archive_path',
          'slave_path', 'slave_version', 'slave_args', 'hol_id']


class ECSBackfillTest(unittest.TestCase):
    def run_import(self, *, name='Example_v1.0_It.lha', slave='ExampleIt/ExampleIt.slave',
                   collection='Games', aga=False, nested=False):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / 'stage'; source.mkdir()
            titles = root / 'titles'; (titles / 'game').mkdir(parents=True)
            (source / name).write_bytes(b'package')
            (titles / 'game/Example_v1.0_AGA.lha').write_bytes(b'canonical')
            inventory = [f'/WHDLoad/Commodore Amiga - WHDLoad - {collection}/E/{name}']
            (source / 'upstream-inventory.json').write_text(json.dumps(inventory))
            donor = dict.fromkeys(FIELDS, '')
            donor.update(id='game--exampleaga--exampleaga', title='Example', title_short='Example',
                         hardware='AGA', aga='1', language='English', developer='Studio',
                         publisher='Publisher', players='1', category='Game',
                         archive_path='game/Example_v1.0_AGA.lha',
                         slave_path='ExampleAGA/ExampleAGA.slave', slave_args='AGA_ONLY', hol_id='123')
            rows = [donor]
            if nested:
                rows.append(dict(donor, id=donor['id']+'--intro', title='Example (Intro)'))
            db = root / 'titles.csv'
            with db.open('w', newline='') as f:
                writer = csv.DictWriter(f, FIELDS, delimiter=';'); writer.writeheader();writer.writerows(rows)
            argv = ['backfill_ecs_metadata.py', '--source', str(source), '--titles-dir', str(titles),
                    '--csv', str(db), '--report', str(root/'report.json'), '--apply']
            signature = b'\x70\xff\x4e\x75WHDLOADS' + struct.pack('>HH', 17, 32 if aga else 0)
            with patch.object(sys, 'argv', argv), patch.object(importer, 'LhaFile') as archive:
                archive.return_value.namelist.return_value = [slave]
                archive.return_value.read.return_value = signature
                with contextlib.redirect_stdout(io.StringIO()):
                    importer.main()
                with db.open() as f:
                    after = list(csv.DictReader(f, delimiter=';'))
                report = json.loads((root/'report.json').read_text())
                once = db.read_bytes()
                with contextlib.redirect_stdout(io.StringIO()):
                    importer.main()
                self.assertEqual(db.read_bytes(), once)
            self.assertEqual(after[:len(rows)], rows)
            return after[len(rows):], report

    def test_translation_clones_shared_fields_but_not_aga_settings(self):
        added, report = self.run_import()
        self.assertEqual(len(added), 1)
        row = added[0]
        self.assertEqual(row['language'], 'Italian')
        self.assertEqual(row['redundant'], '1')
        self.assertEqual(row['preferred_version'], 'game--exampleaga--exampleaga')
        self.assertEqual(row['hardware'], 'OCS')
        self.assertEqual(row['developer'], 'Studio')
        self.assertEqual(row['slave_args'], '')
        self.assertEqual(row['hol_id'], '')
        self.assertEqual(row['aga'], '')

    def test_aga_slave_rejected_even_when_filename_has_no_aga_marker(self):
        added, report = self.run_import(aga=True)
        self.assertEqual(added, [])
        self.assertIn('requires AGA', report[0]['reason'])

    def test_demo_collection_never_uses_same_named_game_metadata(self):
        added, report = self.run_import(collection='Demos')
        self.assertEqual(added, [])
        self.assertEqual(report[0]['status'], 'deferred')

    def test_auxiliary_intro_does_not_make_game_family_ambiguous(self):
        added, _ = self.run_import(nested=True)
        self.assertEqual(len(added), 1)

    def test_unknown_special_variant_is_reported(self):
        added, report = self.run_import(name='Example_v1.0_Hack_by_Someone.lha')
        self.assertEqual(added, [])
        self.assertIn('special variant', report[0]['reason'])


if __name__ == '__main__':
    unittest.main()
