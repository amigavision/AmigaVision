# AmigaVision Windows setup

A small Inno Setup 6 installer for an **existing Windows Amiberry or WinUAE installation**.
Copperline is intentionally deferred until its AmigaVision configuration is supplied.
The setup does not download or install emulators.

## Build and distribute

Run the **Windows installer** GitHub Actions workflow, or compile on Windows:

```powershell
& 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe' build/windows/AmigaVision.iss
```

The workflow compiles the installer, exercises it using synthetic release files,
and uploads `AmigaVision-Setup.exe` as an artifact. It does not publish a release.
The optional compiler argument `/DReleaseVersion=2026.10.24` sets its version.

Place the resulting executable beside the extracted emulator package:

```
AmigaVision-Setup.exe
Amiberry/
WinUAE/
HardDrives/
```

These are the existing `package-emulators` output folders. No disk images or ROMs
are embedded in the executable or uploaded by this workflow. Alternatively,
users can browse to a separately extracted package during setup.

## User flow

1. Install Amiberry or WinUAE separately and close the emulator.
2. Extract the complete AmigaVision emulator archive and run setup.
3. Choose the emulator, release folder, emulator executable and data folder.
4. Optionally make AmigaVision the default configuration or add a desktop shortcut.
5. Launch using the new Start menu shortcut.

WinUAE suggests Public Documents/Amiga Files/WinUAE for data; Amiberry suggests
the executable's folder. Both can be changed. Media paths in the installed
configuration are made absolute, and the shortcut sets the working directory.
WinUAE shaders go beside the executable, not into its data folder. Installing
into Program Files may require selecting **all users** at setup's initial mode
prompt to elevate; otherwise choose writable emulator/data locations.

## Upgrade behavior

- Replaces the main `AmigaVision.hdf`, ROM, shaders and generated listings.
- Keeps existing `AmigaVision-Saves.hdf` and every existing file in `Shared`.
  Missing Shared files are added. To update an existing Shared support file,
  back it up and remove it before rerunning setup.
- Backs up an existing `Configurations/AmigaVision.uae` to the first available
  `.backup-N` filename, then writes the release configuration with resolved paths.
- Leaves `default.uae` alone unless requested, backing it up before replacement.
- Does not create an uninstaller: these are writable emulator data and saved
  games, not files safe for automatic removal. Remove the data and shortcuts
  manually if no longer wanted.

Back up custom changes **inside the main HDF** before upgrading. Do not run the
emulator during setup. Do not move the installed files without rerunning setup,
because the generated configuration uses absolute media paths. The release
folder and installed data folder must be separate, nonoverlapping directories.

The installer uses Inno Setup's external-file copy engine for file progress,
space accounting and copy errors. The release is expected to be trusted and
fully extracted; this is not a release checksum verification tool.

## Validation

On Windows, after compilation:

```powershell
./build/windows/Test-Installer.ps1
```

The test uses tiny placeholder images and never starts an emulator. It verifies
fresh installation, upgrading, preserving user data, backing up configurations,
shader destinations, absolute paths and rejection of invalid inputs. Run it in
a disposable Windows account/runner: it creates and removes AmigaVision Start
menu shortcuts. A real release still needs boot, shader and input verification
in both emulators before distribution. The current source has not yet been
compiled or executed on Windows from this Mac session.

For automation/testing the setup accepts `/EMULATOR=Amiberry` (or `WinUAE`),
`/PAYLOAD="C:\release"`, `/EMULATORFILE="C:\emulator\amiberry.exe"`,
`/DATA="C:\AmigaVision"`, and standard Inno Setup switches. Supply all paths
when using `/VERYSILENT`; interactive page defaults are not applied in that mode.

References: [Inno Setup](https://jrsoftware.org/isinfo.php),
[external files](https://jrsoftware.org/ishelp/topic_filessection.htm).
