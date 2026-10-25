"""Directory cache sorting must compare titles without filesystem extensions."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from avs_make import directory_cache_entries

class MenuSortingTests(unittest.TestCase):
    def test_base_titles_before_sequels_and_trailing_roman_numerals(self):
        with TemporaryDirectory() as tmp:
            titles=['Turrican 3','Cannon Fodder 2','Castle Master II','Turrican II (AGA)',
                    'Another World Lost Level','Cannon Fodder','Turrican','Castle Master','Another World']
            rows=directory_cache_entries(tmp,[],[name+'.run' for name in titles],{})
            self.assertEqual(rows,['FAnother World','FAnother World Lost Level','FCannon Fodder',
                                   'FCannon Fodder 2','FCastle Master','FCastle Master II',
                                   'FTurrican','FTurrican II (AGA)','FTurrican 3'])

    def test_directory_titles_use_the_same_sort(self):
        with TemporaryDirectory() as tmp:
            rows=directory_cache_entries(tmp,['Turrican 3.avs','Turrican II.avs','Turrican.avs'],[],{})
            self.assertEqual(rows,['DTurrican','DTurrican II','DTurrican 3'])

    def test_explicit_order_dividers_and_favorites_are_preserved(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'Favorites.menuitem').write_text('V')
            (root/'Space.divider').write_text('')
            ranks={str(root/'Turrican 3.run'):0,str(root/'Space.divider'):1,
                   str(root/'Favorites.menuitem'):2}
            rows=directory_cache_entries(tmp,[],['Turrican.run','Turrican II.run','Turrican 3.run',
                                              'Space.divider','Favorites.menuitem'],ranks)
            self.assertEqual(rows,['FTurrican 3','S ','VFavorites','FTurrican','FTurrican II'])

    def test_unranked_menu_items_sort_on_stem_without_duplicating_script(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name in ['Cannon Fodder 2','Cannon Fodder']:
                (root/(name+'.menuitem')).write_text('F')
            rows=directory_cache_entries(tmp,[],['Cannon Fodder 2.menuitem','Cannon Fodder.menuitem',
                                              'Cannon Fodder 2.run','Cannon Fodder.run'],{})
            self.assertEqual(rows,['FCannon Fodder','FCannon Fodder 2'])

if __name__=='__main__':
    unittest.main()
