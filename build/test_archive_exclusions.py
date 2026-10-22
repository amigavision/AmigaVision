import contextlib
import io
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from archive_exclusions import is_excluded_archive
import pull_archives
from fetch_archives_from_csv import load_csv_archive_paths
from avs_index import is_ignored_archive_path
from import_notwhdl_demos import list_manual_archives


class ExclusionTests(unittest.TestCase):
    def test_all_languages_and_new_versions_are_excluded(self):
        for name in ['DayOfTheTentacle.lha', 'DayOfTheTentacleDe.lha', 'dayofthetentacle_v2.0_Fr_DaRaSCo.LHA']:
            self.assertTrue(is_excluded_archive('/remote/games/' + name))
        self.assertFalse(is_excluded_archive('Karateka.lha'))

    def test_initial_download_and_manifest_filters(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            csv = root/'titles.csv'
            csv.write_text('id;archive_path\na;game/DayOfTheTentacle.lha\nb;game/Keep.lha\n')
            self.assertEqual([r['id'] for r in load_csv_archive_paths(csv)], ['b'])
            self.assertTrue(is_ignored_archive_path(root, root/'game/DayOfTheTentacle.lha'))
            self.assertFalse(is_ignored_archive_path(root, root/'game/Keep.lha'))

    def test_pull_does_not_download_excluded_remote_archives(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            env = {'ARCHIVE_FETCH_REMOTE': 'test', 'ARCHIVE_FETCH_SYNC_CMD': '',
                   'ARCHIVE_FETCH_LIST_CMD': 'true', 'ARCHIVE_FETCH_GET_CMD': 'true {path}',
                   'ARCHIVE_FETCH_LOGIN_CMD': '', 'ARCHIVE_FETCH_LOGOUT_CMD': '',
                   'ARCHIVE_FETCH_CUTOFF_DAYS': '0'}
            argv = ['pull_archives', '--titles-dir', str(root/'titles'), '--dest', str(root/'staging'), '--state-path', str(root/'state.json')]
            def run(cmd, capture_output=False):
                return SimpleNamespace(stdout='/Games/DayOfTheTentacle_v2.0_De.lha\n/Games/Keep.lha\n')
            with patch.dict('os.environ', env), patch('sys.argv', argv), \
                 patch.object(pull_archives, 'load_state', return_value={'remote_paths': ['/old.lha']}), \
                 patch.object(pull_archives, 'run', side_effect=run) as calls, \
                 contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(pull_archives.main(), 0)
            commands = [str(c.args[0]) for c in calls.call_args_list]
            self.assertFalse(any('Tentacle' in cmd for cmd in commands))
            self.assertTrue(any('Keep.lha' in cmd for cmd in commands))


if __name__ == '__main__':
    unittest.main()
