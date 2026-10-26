"""ECS conversion metadata is optional local cache, not a launcher build input."""
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase,main,mock
import json
import ecs_artwork
from avs_ecs import install_launcher

class ECSArtworkCacheTests(TestCase):
    def test_installs_checked_in_artwork_without_manifest_or_aga_source(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp);output=root/'menu';static=root/'art';launcher=root/'launcher'
            for p in (output,static,launcher):p.mkdir()
            (output/'Custom Menu.iff').write_bytes(b'medium placeholder')
            (static/'Custom Menu.iff').write_bytes(b'custom pre-rendered ECS artwork')
            for name in ('AVSMenu','AVS.conf','skin-bg-highres.iff','AmigaVisionEmpty.iff','About-qr.iff'):
                (launcher/name).write_bytes(name.encode())
            install_launcher(output,SimpleNamespace(image_entries={},by_id={}),static,launcher)
            self.assertEqual((output/'Custom Menu.iff').read_bytes(),b'custom pre-rendered ECS artwork')
            self.assertFalse((static/'manifest.json').exists())
            self.assertEqual(json.loads((output/'ecs-artwork-report.json').read_text())['missing'],[])

    def test_conversion_reuses_local_cache_without_repo_manifest(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp);output=root/'images';launcher=root/'launcher';local=root/'cache'
            source=Path('data/img_highres/By Year.avs/1985.iff')
            argv=['ecs-artwork','--output',str(output),'--launcher-output',str(launcher),'--jobs','1']
            with mock.patch.dict('os.environ',{'AVSCACHE_ROOT':str(local)}), \
                 mock.patch('sys.argv',argv), \
                 mock.patch.object(Path,'rglob',autospec=True,side_effect=lambda *a:iter([source])), \
                 mock.patch.object(Path,'glob',autospec=True,side_effect=lambda *a:iter([])), \
                 mock.patch.object(ecs_artwork,'ProcessPoolExecutor') as pool, \
                 mock.patch.object(ecs_artwork,'convert',wraps=ecs_artwork.convert) as convert:
                pool.return_value.__enter__.return_value.map.side_effect=lambda fn,jobs,chunksize:list(map(fn,jobs))
                ecs_artwork.main()
                self.assertEqual(convert.call_count,1)
                cache=ecs_artwork.cache_manifest_path(output,launcher)
                self.assertTrue(cache.is_relative_to(local))
                self.assertTrue(cache.is_file())
                self.assertFalse((output/'manifest.json').exists())
                ecs_artwork.main()
                self.assertEqual(convert.call_count,1)
                self.assertNotEqual(cache,ecs_artwork.cache_manifest_path(root/'other',launcher))

if __name__=='__main__':main()
