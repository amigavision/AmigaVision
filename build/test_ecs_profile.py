"""ECS selection and static palette regression tests."""
import sqlite3
import tempfile
import unittest
import struct
from unittest.mock import patch
from pathlib import Path

from PIL import Image
from ags_ecs import ECSSelector, ECSDatabase, candidate_rank, make_sanitizer, prepare_menu, patch_menu_text_pen
import ags_query
from ecs_artwork import quantize_ecs, encode_ecs, convert
from repair_hires_palettes import decode, read_chunks


def entry(name, **values):
    return dict(id=name, title=name, preferred_version=values.pop('preferred_version', ''),
                hardware=values.pop('hardware', 'OCS'), aga=values.pop('aga', ''),
                archive_path=values.pop('archive_path', name+'.lha'),
                language=values.pop('language', 'English'), issues=values.pop('issues', ''), **values)


class ECSProfileTest(unittest.TestCase):
    def test_perceptual_palette_keeps_representable_colors_without_dithering(self):
        colors = [(0,0,0),(255,255,255)] + [
            (17*i,17*((5*i)%16),17*((7*i)%16)) for i in range(1,14)]
        source = Image.new('RGB',(len(colors),2)); source.putdata(colors*2)
        first = quantize_ecs(source)
        second = quantize_ecs(source)
        self.assertEqual(first.convert('RGB').tobytes(), source.tobytes())
        self.assertEqual(first.tobytes(), second.tobytes())
        self.assertEqual(first.getpalette(), second.getpalette())
        self.assertLessEqual(max(first.tobytes()),15)
        self.assertTrue(all(value%17==0 for value in first.getpalette()[:48]))

    def test_perceptual_palette_preserves_purple_owl_and_red_mouth(self):
        masters = Path(__file__).resolve().parents[1]/'data/img_highres'
        cases = [
            ('game--agony--agony-3.iff',lambda r,g,b: b>r+20 and r>g+15 and b>100,.6),
            ('game--alienbreed2--alienbreed2-2.iff',lambda r,g,b: r>g+40 and r>b+20 and r>100,.9),
        ]
        for name,is_accent,minimum in cases:
            source,_ = decode(read_chunks(masters/name))
            result = quantize_ecs(source).convert('RGB')
            pairs = [(old,new) for old,new in zip(source.convert('RGB').getdata(),result.getdata())
                     if is_accent(*old)]
            self.assertGreater(len(pairs),100)
            retained = sum(is_accent(*new) for _,new in pairs)/len(pairs)
            self.assertGreater(retained,minimum,name)

    def test_perceptual_palette_keeps_agony_sea_green(self):
        path = Path(__file__).resolve().parents[1]/'data/img_highres/game--agony--agony-5.iff'
        source,_ = decode(read_chunks(path))
        result = quantize_ecs(source).convert('RGB')
        water = (100,170,source.width,source.height)
        def green(rgb):
            r,g,b = rgb
            return g>r+12 and g>b+12
        pairs = [(old,new) for old,new in zip(source.convert('RGB').crop(water).getdata(),
                                             result.crop(water).getdata()) if green(old)]
        self.assertGreater(len(pairs),100)
        self.assertGreater(sum(green(new) for _,new in pairs)/len(pairs),.8)

    def test_launcher_text_pen_patch_changes_only_dynamic_pen_to_locked_white(self):
        source = Path(__file__).resolve().parents[1]/'data/ags2/AGS2Menu'
        original = source.read_bytes()
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder)/'AGS2Menu'
            patch_menu_text_pen(source, target)
            patched = target.read_bytes()
            self.assertEqual(len(original), len(patched))
            self.assertEqual([(a,b) for a,b in zip(original,patched) if a!=b],[(253,255)])
            self.assertEqual(source.read_bytes(), original)
            unknown = Path(folder)/'unknown'; unknown.write_bytes(b'unknown launcher')
            with self.assertRaises(ValueError):
                patch_menu_text_pen(unknown, target)

    def test_menu_cleanup_preserves_note_only_about_and_artwork(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root/'About.ags').mkdir()
            (root/'About.txt').write_text('About AmigaVision')
            (root/'About.iff').write_bytes(b'artwork')
            (root/'Empty.ags').mkdir()
            (root/'Empty.iff').write_bytes(b'empty artwork')
            prepare_menu(root)
            self.assertTrue((root/'About.ags').is_dir())
            self.assertTrue((root/'About.txt').is_file())
            self.assertTrue((root/'About.iff').is_file())
            self.assertFalse((root/'Empty.ags').exists())
            self.assertFalse((root/'Empty.iff').exists())

    def test_low_memory_never_beats_standard_even_if_canonical(self):
        low = entry('low', archive_path='Example_v1.0_LowMem.lha')
        full = entry('full', preferred_version='low', issues='minor issue')
        selector = ECSSelector([low, full], dict)
        self.assertEqual(selector.resolve('low')['id'], 'full')
        with self.assertRaises(ValueError):
            ECSSelector([low, full], dict, {'low':'low'})

    def test_aga_root_has_one_shared_fallback_for_all_siblings(self):
        rows = [entry('aga', aga='1'), entry('full', preferred_version='aga'),
                entry('low', archive_path='Example_v1.0_512k.lha', preferred_version='aga')]
        selector = ECSSelector(rows, dict)
        self.assertEqual({selector.resolve(r['id'])['id'] for r in rows}, {'full'})

    def test_ocs_ecs_tie_requires_curated_choice(self):
        rows = [entry('aga', hardware='AGA'), entry('ocs', preferred_version='aga'),
                entry('ecs', hardware='ECS', preferred_version='aga')]
        self.assertIsNone(ECSSelector(rows, dict).resolve('aga'))
        self.assertEqual(ECSSelector(rows, dict, {'aga':'ocs'}).resolve('ecs')['id'], 'ocs')

    def test_missing_archive_is_not_a_candidate(self):
        rows = [entry('aga', aga='1'), entry('missing', preferred_version='aga')]
        selector = ECSSelector(rows, lambda r: None if r['id']=='missing' else dict(r))
        self.assertIsNone(selector.resolve('aga'))

    def test_broken_link_is_reported_without_selecting_random_sibling(self):
        selector = ECSSelector([entry('broken', preferred_version='missing')], dict)
        self.assertIsNone(selector.resolve('broken'))
        self.assertEqual(selector.report[0]['status'], 'invalid-link')

    def test_exact_and_fuzzy_menu_requests_resolve_same_family(self):
        raw = sqlite3.connect(':memory:'); raw.row_factory=sqlite3.Row
        raw.execute('CREATE TABLE titles (id TEXT, title TEXT, preferred_version TEXT, hardware TEXT, aga TEXT, archive_path TEXT, language TEXT, issues TEXT)')
        rows=[entry('game--exampleaga--exampleaga', aga='1'),
              entry('game--example--example', preferred_version='game--exampleaga--exampleaga')]
        for row in rows:
            raw.execute('INSERT INTO titles VALUES (:id,:title,:preferred_version,:hardware,:aga,:archive_path,:language,:issues)', row)
        db=ECSDatabase(raw,ECSSelector(rows,dict))
        for name in ['example', 'game--exampleaga--exampleaga', 'game--example--example']:
            self.assertEqual(ags_query.get_entry(db,name)[0]['id'], 'game--example--example')
        raw.close()

    def test_small_palette_roundtrip_and_padding_keep_locked_colors(self):
        for rgb in ['red', 'black', 'white']:
            original=Image.new('RGB',(19,7),rgb)
            image=quantize_ecs(original)
            with tempfile.TemporaryDirectory() as folder:
                path=Path(folder)/'test.iff';path.write_bytes(encode_ecs(image,0x19004))
                chunks=read_chunks(path);decoded,_=decode(chunks)
                self.assertEqual(chunks[b'BMHD'][8],4)
                self.assertEqual(decoded.getpalette()[42:48],[0,0,0,255,255,255])
                self.assertEqual(decoded.tobytes(),image.tobytes())
                self.assertEqual(decoded.getpalette()[:3],[0,0,0])
                stride=4  # 19 visible pixels padded to 32 bits in each plane.
                for offset in range(0,len(chunks[b'BODY']),stride):
                    self.assertEqual(int.from_bytes(chunks[b'BODY'][offset:offset+stride],'big') & ((1<<13)-1),0)

    def test_qr_pixels_only_use_locked_black_white(self):
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'qr'/'example-qr.iff';source.parent.mkdir()
            image=Image.new('RGB',(50,50),'white');image.paste('black',(5,5,40,40))
            source.write_bytes(encode_ecs(quantize_ecs(image),0))
            target=Path(folder)/'output.iff'
            convert((str(source),str(target),False))
            result,_=decode(read_chunks(target))
            self.assertEqual(set(result.tobytes()),{14,15})

    def test_slave_verification_ignores_case_and_rejects_aga_flag(self):
        row=entry('example',slave_path='Example/Example.slave')
        with patch('lhafile.LhaFile') as archive, patch('ags_paths.titles',return_value='/tmp'):
            archive.return_value.namelist.return_value=['Example/Example.Slave']
            archive.return_value.read.return_value=b'\x70\xff\x4e\x75WHDLOADS'+struct.pack('>HH',17,32)
            sanitizer=make_sanitizer(dict)
            self.assertIsNone(sanitizer(row))
            self.assertIn('requires AGA',sanitizer.excluded[0]['reason'])
            archive.return_value.read.return_value=b'\x70\xff\x4e\x75WHDLOADS'+struct.pack('>HH',17,0)
            self.assertEqual(make_sanitizer(dict)(row)['id'],'example')

    def test_skin_maps_blue_to_white_and_almost_black_to_black(self):
        original=Image.new('RGB',(3,1));original.putdata([(0,0,0),(1,1,1),(16,135,165)])
        image=quantize_ecs(original,skin=True)
        self.assertEqual(image.tobytes(),bytes([14,14,15]))


if __name__=='__main__':
    unittest.main()
