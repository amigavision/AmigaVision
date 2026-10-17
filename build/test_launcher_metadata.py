"""Launcher geometry and metadata regression checks."""
import csv
import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from ags_make import (AGS_INFO_HEIGHT, AGS_INFO_WIDTH, make_note, metadata_blocks,
                      metadata_date, metadata_system, metadata_wrap, wrap_note)

ROOT = Path(__file__).resolve().parents[1]


def entry(**values):
    result = dict(title='Example', category='Game', subcategory='Action', hardware='OCS',
                  release_date='1993', developer='Team 17', publisher='Ocean, Team 17',
                  players='2 Players', language='English')
    result.update(values)
    return result


class LauncherMetadataTest(unittest.TestCase):
    def assert_geometry(self, text):
        lines = text.splitlines()
        self.assertLessEqual(len(lines), AGS_INFO_HEIGHT)
        for line in lines:
            self.assertLessEqual(len(line), AGS_INFO_WIDTH)
            self.assertEqual(line, line.strip().center(AGS_INFO_WIDTH).rstrip() if line.strip() else '')
        text.encode('latin-1')

    def test_credits_deduplicate_individual_names_and_empty_fields_compact(self):
        lines = [line.strip() for line in make_note(entry(), None).splitlines()]
        self.assertEqual(lines, ['Example', '', '1993 · Team 17 · Ocean', 'Action · 2 Players', 'OCS·4×PAL'])
        sparse = make_note(entry(release_date='', developer='', publisher='', language='', players='', subcategory=''), None)
        self.assertEqual([line.strip() for line in sparse.splitlines()], ['Example', '', 'OCS·4×PAL'])

    def test_english_only_is_hidden_but_other_language_lists_remain(self):
        for language in ('English', ' english '):
            self.assertNotIn('language', dict(metadata_blocks(entry(language=language), None, 'OCS·4×PAL')))
        for language in ('English, German', 'French'):
            self.assertIn(language, make_note(entry(language=language), None))

    def test_title_spacing_yields_to_seven_and_eight_content_lines(self):
        for extras, content_lines in [({'note': 'Instructions'}, 6),
                                      ({'note': 'Instructions', 'hack': 'Remaster'}, 7),
                                      ({'note': 'Instructions', 'hack': 'Remaster', 'issues': 'Crashes'}, 8)]:
            result = make_note(entry(language='German', **extras), None)
            lines = result.splitlines()
            self.assertEqual('' in lines, content_lines <= 6)
            self.assertEqual(len(lines), content_lines + (content_lines <= 6))
            self.assert_geometry(result)
        wrapped = make_note(entry(language='German', note='Instructions ' * 5), None)
        self.assertEqual(len(wrapped.splitlines()), 7)
        self.assertNotIn('', wrapped.splitlines())

    def test_all_optional_fields_survive_overflow_and_hardware_stays_last(self):
        value = entry(title='Long title ' * 12, developer='Long developer ' * 12,
                      note='Instructions ' * 12, issues='Crashes after intro', hack='Remaster by Example')
        with redirect_stdout(io.StringIO()) as warnings:
            result = make_note(value, None)
        self.assert_geometry(result)
        self.assertIn('exceeds 8 lines', warnings.getvalue())
        self.assertIn('Crashes after intro', result)
        self.assertIn('Remaster by Example', result)
        self.assertEqual(result.splitlines()[-1].strip(), 'OCS·4×PAL')

    def test_demo_and_override_note(self):
        value = entry(category='Demo', subcategory='Intro 4K', country='Norway', publisher='Spaceballs', note='CSV note')
        result = make_note(value, 'List-specific note')
        self.assertIn('Norway · Intro 4K', result)
        self.assertIn('List-specific note', result)
        self.assertNotIn('CSV note', result)
        self.assertNotIn('Players', result)
        self.assertNotIn('English', result)
        self.assert_geometry(result)

    def test_modes_and_both_controllers_work_for_csv_strings_and_database_ints(self):
        for ntsc, mode in [(0, 'PAL'), (1, 'NTSC'), (2, 'PAL60')]:
            for convert in [str, int]:
                system = metadata_system(entry(ntsc=convert(ntsc), scale=convert(6), gamepad=convert(1), lightgun=convert(2)))
                self.assertEqual(system, 'OCS·6×' + mode + '·Light Gun·Game Pad (16:9)')
        self.assertEqual(metadata_system(entry(gamepad='0', lightgun='0')), 'OCS·4×PAL')

    def test_dates_preserve_sortable_source_and_display_uncertainty(self):
        for value, expected in [('198X', '1980s'), ('199X', '1990s'), ('19XX', ''), ('1993-12-30', '30 Dec 1993'), ('', '')]:
            self.assertEqual(metadata_date(value), expected)

    def test_authored_padding_and_both_literal_newline_forms_are_normalized(self):
        text = wrap_note('     About    \\n\\nCredits\\\\nLast line')
        self.assertEqual([line.strip() for line in text.splitlines()], ['About', '', 'Credits', 'Last line'])
        self.assert_geometry(text)
        with redirect_stdout(io.StringIO()):
            self.assert_geometry(wrap_note('word ' * 150))

    def test_entire_csv_fits_without_clipping(self):
        with (ROOT / 'data/db/titles.csv').open() as handle:
            for value in csv.DictReader(handle, delimiter=';'):
                with self.subTest(id=value['id']):
                    blocks = metadata_blocks(value, None, metadata_system(value))
                    self.assertLessEqual(sum(len(metadata_wrap(text)) for _, text in blocks), 8)
                    self.assert_geometry(make_note(value, None))

    def test_all_launcher_configs_and_static_text_match_geometry(self):
        for path in ['data/ags2/AGS2.conf', 'data/ags2/AGS2.conf.base', 'data/ags2-highres/AGS2.conf', 'data/ags2-ecs/AGS2.conf']:
            config = (ROOT / path).read_text()
            self.assertIn('text_width = 48', config)
            self.assertIn('text_height = 8', config)
        for path in list((ROOT / 'configs/Layers').rglob('*.txt')) + list((ROOT / 'data/ags2').glob('*.txt')):
            with self.subTest(path=path):
                self.assert_geometry(path.read_bytes().decode('latin-1'))


if __name__ == '__main__':
    unittest.main()
