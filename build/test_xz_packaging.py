import lzma
from pathlib import Path
import shutil
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import package_distros as packaging
import pistorm_image
import xz_reuse
from test_exfat_extent import image_fixture


class PackagingTests(unittest.TestCase):
    def test_selected_run_only_adds_required_seed(self):
        args=SimpleNamespace(package='all', only='pi,pistorm-aga', no_xz_reuse=False)
        self.assertEqual(packaging.selected_packages(args), ['amiga', 'pi', 'pistorm-aga'])
        args.no_xz_reuse=True
        self.assertEqual(packaging.selected_packages(args), ['pi', 'pistorm-aga'])
        args.only='pistorm-ecs'; args.no_xz_reuse=False
        self.assertEqual(packaging.selected_packages(args), ['amiga-ecs', 'pistorm-ecs'])
        args.only='typo'
        with self.assertRaises(ValueError): packaging.selected_packages(args)

    def args(self, root):
        source = root / 'main.hdf'; source.write_bytes(b'RDSK' + b'HDF data' * 800000)
        script = root / 'pi_image.sh'; script.touch()
        return SimpleNamespace(package='all', main_hdf=source, ecs_hdf=source, date_stamp='test',
                               dry_run=False, pi_script=script, _xz_manifest_dir=root / 'manifests', _xz_seeds={})

    def test_selected_run_skips_dependents_when_seed_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); args=self.args(root)
            del args._xz_manifest_dir
            args.output_dir=root; args.archive_tool=None; args.no_xz_reuse=False
            args.only='pi,pistorm-aga'; args.saves_hdf=root/'saves.hdf'; args.skip_emulator_archive=False
            with patch.object(packaging, 'parse_args', return_value=args), \
                    patch.object(packaging, 'find_xz_tool', return_value='xz'), \
                    patch.object(packaging, 'package_amiga', side_effect=ValueError('Source changed')), \
                    patch.object(packaging, 'package_rpi') as pi, \
                    patch.object(packaging, 'package_pistorm') as pistorm:
                self.assertEqual(packaging.main(), 1)
                pi.assert_not_called(); pistorm.assert_not_called()
            self.assertFalse((root/'.build').exists())

    def test_amiga_seed_then_rpi_reuses_embedded_file_and_cleans_raw_image(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); args = self.args(root)
            packaging.package_amiga(args, root, 'xz', ecs=False)
            image, _ = image_fixture(args.main_hdf.read_bytes())
            pi = root / 'pi'; pi.mkdir()

            def build(command, **kwargs):
                Path(command[command.index('--output-img')+1]).write_bytes(image)

            with patch.object(packaging, 'run_command', side_effect=build), \
                    patch.object(xz_reuse.lzma, 'decompress', side_effect=AssertionError('Seed decoded')):
                output = packaging.package_rpi(args, pi, 'xz')
            self.assertEqual(lzma.decompress(output.read_bytes()), image)
            self.assertFalse(output.with_suffix('').exists())
            self.assertTrue(args._xz_seeds[False][1].is_file())

    def test_fragmented_rpi_falls_back_and_preserves_image_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); args = self.args(root)
            packaging.package_amiga(args, root, 'xz', ecs=False)
            image, _ = image_fixture(args.main_hdf.read_bytes(), fragmented=True)
            pi = root / 'pi'; pi.mkdir()

            def build(command, **kwargs):
                Path(command[command.index('--output-img')+1]).write_bytes(image)

            with patch.object(packaging, 'run_command', side_effect=build), \
                    patch.object(xz_reuse, 'reuse', side_effect=AssertionError('Fragmented file reused')):
                output = packaging.package_rpi(args, pi, 'xz')
            self.assertEqual(lzma.decompress(output.read_bytes()), image)
            self.assertFalse(output.with_suffix('').exists())

    def test_ordinary_compression_failure_preserves_previous_release(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); source = root / 'source'; source.write_bytes(b'payload')
            output = root / 'release.xz'; output.write_bytes(b'old release')
            with patch.object(packaging.subprocess, 'run', side_effect=subprocess.CalledProcessError(1, 'xz')):
                with self.assertRaises(subprocess.CalledProcessError):
                    packaging.compress_xz(source, output, 'xz')
            self.assertEqual(output.read_bytes(), b'old release')
            self.assertFalse(list(root.glob('*.partial.*')))

    def test_pistorm_variants_receive_the_correct_seed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); args = self.args(root)
            args.dry_run=True; args.pistorm_rom='rom'; args.amiberry='amiberry'; args.rom_file='rom'
            args._xz_seeds={False: (root/'main.xz', root/'main.json'), True: (root/'ecs.xz', root/'ecs.json')}
            for ecs in (False, True):
                with patch.object(packaging, 'run_command') as run:
                    packaging.package_pistorm(args, root, ecs)
                command=run.call_args.args[0]
                self.assertEqual(command[command.index('--reuse-seed')+1], str(args._xz_seeds[ecs][0]))

    def test_all_packages_create_seeds_before_consumers_and_remove_workspace(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); args = self.args(root)
            del args._xz_manifest_dir
            args.output_dir=root; args.archive_tool=None; args.no_xz_reuse=False
            args.saves_hdf=root/'saves.hdf'; args.skip_emulator_archive=False
            order=[]

            def simple(name):
                def package(*unused, **kwargs):
                    order.append(name); return root/(name+'.xz')
                return package

            def amiga(args, *unused, ecs=False):
                order.append('ecs' if ecs else 'amiga')
                args._xz_seeds[ecs]=(root/'seed', root/'manifest')
                return root/'amiga.xz'

            def pi(args, *unused):
                self.assertIn(False, args._xz_seeds)
                order.append('pi'); return root/'pi.xz'

            def pistorm(args, *unused, ecs=False):
                self.assertIn(ecs, args._xz_seeds)
                name='pistorm-ecs' if ecs else 'pistorm-aga'
                order.append(name); return root/(name+'.xz')

            with patch.object(packaging, 'parse_args', return_value=args), \
                    patch.object(packaging, 'find_archive_tool', return_value='7zz'), \
                    patch.object(packaging, 'find_xz_tool', return_value='xz'), \
                    patch.object(packaging, 'package_mister', side_effect=simple('mister')), \
                    patch.object(packaging, 'build_cd32_release', return_value=root/'cd32.zip'), \
                    patch.object(packaging, 'package_cd32_mister', side_effect=simple('cd32')), \
                    patch.object(packaging, 'package_emulators', side_effect=simple('emulators')), \
                    patch.object(packaging, 'package_amiga', side_effect=amiga), \
                    patch.object(packaging, 'package_rpi', side_effect=pi), \
                    patch.object(packaging, 'package_pistorm', side_effect=pistorm), \
                    patch.object(packaging, 'list_archive_contents'), \
                    patch.object(packaging, 'write_checksums'):
                self.assertEqual(packaging.main(), 0)
            self.assertEqual(order, ['amiga', 'pi', 'pistorm-aga', 'ecs', 'pistorm-ecs',
                                     'mister', 'emulators', 'cd32'])
            self.assertFalse((root/'.build').exists())


@unittest.skipUnless((pistorm_image.ROOT/'data/cache/pistorm/hdf2emu68-source.zip').is_file() and shutil.which('cc'),
                     'cached converter source and cc required')
class PiStormIntegrationTests(unittest.TestCase):
    def test_real_converter_prefix_with_hash_reuse_and_missing_seed_fallback(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); cache=root/'cache'; cache.mkdir()
            shutil.copyfile(pistorm_image.ROOT/'data/cache/pistorm/hdf2emu68-source.zip', cache/'hdf2emu68-source.zip')
            converter=pistorm_image.get_converter(cache)
            source=root/'source.hdf'; source.write_bytes(b'RDSK'+b'contents'*800000)
            seed, manifest=root/'seed.xz', root/'seed.json'
            xz_reuse.compress_seed(source, seed, manifest)
            raw=bytearray(source.read_bytes()); raw[100]^=1
            patched=root/'patched.hdf'; patched.write_bytes(raw)
            boot=root/'boot'; boot.mkdir(); (boot/'kick.rom').write_bytes(b'ROM'*100)
            prefix=root/'prefix.img'
            subprocess.run([str(converter), str(patched), '-fatsize', '64', '-fatdir', str(boot),
                            '-output', str(prefix), '-prefix-only'], check=True, stdout=subprocess.DEVNULL)
            total=pistorm_image.validate(prefix, patched, boot, prefix_only=True)
            expected=prefix.read_bytes()+raw+bytes(total-prefix.stat().st_size-len(raw))
            for metadata in (manifest, root/'missing.json'):
                output=root/'release.xz'
                pistorm_image.compress_streamed_image(prefix, patched, boot, output,
                                                      reuse_seed=seed, reuse_manifest=metadata)
                self.assertEqual(lzma.decompress(output.read_bytes()), expected)


if __name__ == '__main__': unittest.main()
