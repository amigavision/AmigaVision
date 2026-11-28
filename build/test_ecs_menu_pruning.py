"""ECS-only exclusions and recursive empty-category cleanup."""
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from avs_ecs import prepare_menu

class PruningTests(unittest.TestCase):
    def test_notes_art_and_labels_do_not_keep_empty_categories(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            empty=root/'Curated.avs'/'Empty.avs';empty.mkdir(parents=True)
            for name in ('Empty.txt','Empty.iff','Empty-3.iff','Empty-QR.iff','Empty.avs.label'):
                (empty.parent/name).touch()
            (root/'Curated.txt').touch()
            about=root/'About.run';about.write_text('; Information only\n')
            options=root/'Options.avs';options.mkdir();(options/'Enable Music.run').touch()
            removed=prepare_menu(root)
            self.assertEqual({row['category'] for row in removed},{'Curated.avs/Empty.avs','Curated.avs'})
            self.assertTrue(about.is_file());self.assertTrue(options.is_dir())
            self.assertFalse((root/'Curated.txt').exists())

    def test_requested_exclusions_cannot_be_recreated_by_artwork_installation(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp);image_entries={}
            for parent,name in [('Curated Games',"GouldFish's AGA Games to Play"),('Demo Scene','060 Demos')]:
                folder=root/(parent+'.avs')/(name+'.avs');folder.mkdir(parents=True)
                (folder/'Fallback.run').touch()
                image_entries[str(folder.relative_to(root)/'Fallback')]='game--fallback--fallback'
            live=root/'Other.avs';live.mkdir();(live/'Game.run').touch()
            image_entries['Other.avs/Game']='game--game--game'
            collection=SimpleNamespace(image_entries=image_entries)
            removed=prepare_menu(root,collection)
            excluded={Path(row['category']).stem for row in removed if row['reason']=='excluded'}
            self.assertEqual(excluded,{"GouldFish's AGA Games to Play",'060 Demos'})
            self.assertEqual(collection.image_entries,{'Other.avs/Game':'game--game--game'})
            self.assertTrue(live.is_dir())

    def test_virtual_menu_actions_are_selectable(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp);folder=root/'Special.avs';folder.mkdir()
            (folder/'Favorites.menuitem').write_text('V')
            self.assertEqual(prepare_menu(root),[])

if __name__=='__main__':unittest.main()
