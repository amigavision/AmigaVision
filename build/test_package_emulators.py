import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import package_distros


class EmulatorPackageTests(unittest.TestCase):
    def test_stages_both_emulators_with_portable_paths_and_versioned_assets(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            payloads = {}
            for name in ("main.hdf", "saves.hdf", "kick.rom", "shared/support.txt",
                         "listings/games.txt", "visuals/Shaders/crt/crt-easymode-halation.glslp"):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(name)
                payloads[name] = path
            installer = root / package_distros.INSTALLER_NAME
            installer.write_bytes(b"MZ test installer")
            args = SimpleNamespace(
                windows_installer=installer,
                main_hdf=payloads["main.hdf"], saves_hdf=payloads["saves.hdf"],
                rom_file=payloads["kick.rom"], shared_dir=root / "shared",
                listings_dir=root / "listings", visuals_dir=root / "visuals",
                date_stamp="2026.10.20", dry_run=False, skip_emulator_archive=False,
            )

            def check_archive(output_path, stage, archive_tool, dry_run):
                self.assertEqual({p.name for p in stage.iterdir()}, {"Amiberry", "WinUAE", "Copperline", package_distros.INSTALLER_NAME})
                self.assertEqual((stage / package_distros.INSTALLER_NAME).read_bytes(), installer.read_bytes())
                assets = Path("content/distro_emulators")
                import tomllib
                copper = tomllib.loads((stage / "Copperline/configs/AmigaVision.toml").read_text())
                for media in (copper["rom"], copper["copperhf"]["unit0"], copper["copperhf"]["unit1"]["path"]):
                    self.assertTrue((stage / "Copperline" / media).is_file())
                self.assertEqual(copper["copperhf"]["unit1"]["bootpri"], -35)
                self.assertFalse((stage / "Copperline/HardDrives").exists())
                for dest, source in (
                    ("AmigaVision.hdf", "main.hdf"),
                    ("AmigaVision-Saves.hdf", "saves.hdf"),
                    ("Shared/support.txt", "shared/support.txt"),
                    ("listings/games.txt", "listings/games.txt"),
                ):
                    self.assertEqual((stage / "Amiberry/HardDrives" / dest).read_bytes(), payloads[source].read_bytes())
                self.assertEqual(len(list(stage.rglob("*.hdf"))), 2)
                for emulator in ("Amiberry", "WinUAE"):
                    base = stage / emulator
                    self.assertEqual((base / "HardDrives").exists(), emulator == "Amiberry")
                    self.assertEqual((base / "ROMs/AmigaVision.rom").read_bytes(), payloads["kick.rom"].read_bytes())
                    config_name = "AmigaVision-Amiberry.uae" if emulator == "Amiberry" else "default.uae"
                    dest_name = "default.uae" if emulator == "Amiberry" else config_name
                    config = base / "Configurations" / dest_name
                    self.assertEqual(config.read_bytes(), (assets / emulator / config_name).read_bytes())
                    self.assertEqual((base / "Configurations/AmigaVision.uae").read_bytes(), config.read_bytes())
                    self.assertEqual((base / "INSTALL.txt").read_bytes(), (assets / emulator / "INSTALL.txt").read_bytes())
                    self.assertNotIn("C:\\Users\\", config.read_text())
                    self.assertNotIn("/Users/", config.read_text())
                shader_path = Path("Visuals/Shaders/crt/shaders/crt-easymode-halation/crt-easymode-halation.glsl")
                self.assertEqual((stage / "Amiberry" / shader_path).read_bytes(),
                                 (assets / "Amiberry" / shader_path).read_bytes())
                self.assertTrue((stage / "Amiberry/Visuals/Shaders/crt/crt-easymode-halation.glslp").is_file())
                self.assertEqual((stage / "WinUAE/plugins/filtershaders/direct3d/CRT-Pi-SmartRes.fx").read_bytes(),
                                 (assets / "WinUAE/CRT-Pi-SmartRes.fx").read_bytes())
                self.assertEqual((stage / "WinUAE/INSTALL.txt").read_bytes(),
                                 (assets / "WinUAE/INSTALL.txt").read_bytes())
                self.assertEqual(output_path.name, "AmigaVision-Emulators-2026.10.20.7z")

            with patch.object(package_distros, "archive_7z", side_effect=check_archive) as archive:
                package_distros.package_emulators(args, root, "7zz")
                archive.assert_called_once()
            self.assertFalse(list(root.glob("amigavision-emulators-*")))
            args.skip_emulator_archive = True
            with patch.object(package_distros, "archive_7z") as archive:
                output = package_distros.package_emulators(args, root, None)
                archive.assert_not_called()
            self.assertTrue((output / "WinUAE/INSTALL.txt").is_file())
            self.assertEqual((output / package_distros.INSTALLER_NAME).read_bytes(), installer.read_bytes())
            self.assertTrue((output / "Amiberry/HardDrives/AmigaVision.hdf").is_file())
            self.assertEqual(len(list(output.rglob("*.hdf"))), 2)
            for emulator in ("Amiberry", "WinUAE"):
                self.assertEqual((output / emulator / "HardDrives").exists(), emulator == "Amiberry")
                configs = output / emulator / "Configurations"
                self.assertEqual((configs / "AmigaVision.uae").read_bytes(), (configs / "default.uae").read_bytes())
            self.assertEqual(output.name, "AmigaVision-Emulators-2026.10.20")
            with self.assertRaises(FileExistsError):
                package_distros.package_emulators(args, root, None)
            self.assertTrue((output / "WinUAE/INSTALL.txt").is_file())
            args.date_stamp = "2026.10.21"
            args.package = "emulators"
            args.output_dir = str(root)
            args.archive_tool = None
            with patch.object(package_distros, "parse_args", return_value=args), \
                 patch.object(package_distros, "find_archive_tool", side_effect=AssertionError("7z lookup")), \
                 patch.object(package_distros, "write_checksums", side_effect=AssertionError("Directory checksums")), \
                 patch.object(package_distros, "list_archive_contents", side_effect=AssertionError("Archive listing")):
                self.assertEqual(package_distros.main(), 0)
            self.assertTrue((root / "AmigaVision-Emulators-2026.10.21/WinUAE/INSTALL.txt").is_file())



if __name__ == "__main__":
    unittest.main()
