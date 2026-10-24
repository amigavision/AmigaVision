# AmigaVision Windows setup

A small Inno Setup 6 installer for an **existing Windows Amiberry or WinUAE installation**.
The emulator list shows Amiberry, Copperline (a disabled coming-soon placeholder),
and WinUAE, each with a download link. Copperline installation is deferred until
its AmigaVision configuration is supplied.
The setup does not download or install emulators.

## Build and distribute

Run the **Windows installer** GitHub Actions workflow, or compile on Windows:

```powershell
& 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe' build/windows/WinUAEShader.iss
& 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe' build/windows/AmigaVision.iss
```

The workflow compiles the installer, exercises it using synthetic release files,
and uploads `Install AmigaVision for Windows.exe` as an artifact. It does not publish a release.
The optional compiler argument `/DReleaseVersion=2026.10.24` sets its version.

Place the resulting executable beside the downloaded emulator archive:

```
Install AmigaVision for Windows.exe
AmigaVision-Emulators-2026.10.24.7z
```

Setup detects a single `AmigaVision-Emulators*.7z` or `.zip` beside itself and
extracts it with progress shown. A complete extracted `AmigaVision-Emulators*`
folder, or the existing loose Amiberry/WinUAE/HardDrives folders beside setup,
also works. Multiple matches or no match lead to a separate release picker.
The picker accepts an archive or an extracted folder, including a parent folder
containing the extracted release. No disk images or ROMs are embedded in the
executable or uploaded by this workflow.

Archives are extracted to Windows temporary storage before copying to the
chosen destination. Allow space for the full extracted release on the temporary
volume as well as the installed files on the destination. Users with limited
temporary storage can extract the archive elsewhere and choose that folder.

## User flow

1. Install Amiberry or WinUAE separately and close the emulator.
2. Put the downloaded release beside setup and run setup.
3. Choose the emulator. Setup finds the selected emulator automatically.
   If it cannot find it, install it or choose its installation folder.
4. Choose the data folder. Setup checks the selected destination as it changes,
   showing the backup warning below the folder picker only if the main image
   already exists, before you click Next. Existing saves/Shared files are
   identified as being preserved when present.
5. Click Next. Setup detects the release beside itself; if needed, the next page
   asks for the release archive or extracted folder. Destination selection never
   validates the release location.
6. Choose whether to make AmigaVision the default configuration and add a desktop
   shortcut. Both options are selected by default and can be unchecked.
7. On “AmigaVision Install Completed”, leave “Launch AmigaVision” checked to
   launch it when you click Finish. Silent installations never launch an emulator.

Detection checks Windows App Paths and uninstall records for the current user
and all users, in both registry views; Program Files and per-user Programs;
PATH; and nearby portable folders (beside setup/the release, on the Desktop,
in Documents, Downloads and the user profile). Portable searches check one
level of emulator-named folders, not the entire drive. WinUAE prefers
`winuae64.exe` over `winuae.exe` across all detected locations. The executable
picker is removed; only a folder fallback is shown if detection fails.

WinUAE suggests Public Documents/Amiga Files/WinUAE for data; Amiberry suggests
the executable's folder. Both can be changed. Media paths in the installed
configuration are made absolute, and the shortcut sets the working directory.
WinUAE shaders go beside the executable, not into its data folder. Installing
into a protected WinUAE program folder is handled automatically: setup explains
why administrator permission is required on the destination page, then asks
Windows to elevate a small embedded shader helper before copying the main
installation. Only that helper runs with administrator access; user data and
shortcuts remain under the original Windows account. Cancelling the permission
request prevents installation from starting, and the shader cannot be silently
skipped. Writable WinUAE installations need no elevation. Silent installations
never display a permission prompt: run those as administrator if the shader
folder is protected. The helper is built first and embedded in the main setup
executable, so users still download just one installer.

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

If you have made any changes to the main System drive or the Data drive, back those up first. Do not run the
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
shader destinations, absolute paths, registered emulator discovery in both
registry views, 64-bit WinUAE preference, ZIP/7z extraction, nearby release
discovery and rejection of ambiguous releases and invalid inputs. Run it in
a disposable Windows account/runner: it creates and removes AmigaVision Start
menu shortcuts. A real release still needs boot, shader and input verification
in both emulators before distribution. Installation tests run on Windows through GitHub Actions; local compilation
alone does not verify the detection behavior on Windows.

For automation/testing the setup accepts `/EMULATOR=Amiberry` (or `WinUAE`),
`/PAYLOAD="C:\release"`, `/EMULATORFILE="C:\emulator\amiberry.exe"`,
`/DATA="C:\AmigaVision"`, and standard Inno Setup switches. The executable override is optional: omit it to use detection. Supply the payload
and data paths when using `/VERYSILENT`; interactive page defaults are not
applied in that mode.

References: [Inno Setup](https://jrsoftware.org/isinfo.php),
[external files](https://jrsoftware.org/ishelp/topic_filessection.htm).

Amiberry install locations are based on its [Windows packaging settings](https://github.com/BlitterStudio/amiberry/blob/master/packaging/CMakeLists.txt).

## Branding

`assets/AV-avatar.png` is the supplied source artwork. `assets/AmigaVision.ico`
contains 16, 20, 24, 32, 40, 48, 64, 96, 128 and 256 pixel versions for the
setup executable and installed shortcuts. The ICO is copied into the data
folder so shortcuts retain their icon independently of the setup executable.
The wizard keeps the avatar in its header and uses a full-width blue banner
on the welcome/completion pages, with the AmigaVision SVG wordmark centered
above the text. The background is #5180DD, matching the avatar. The SVG source
is saved as `assets/amigavision.svg`; `assets/banner.bmp` is embedded for the
Windows bitmap control, and `assets/banner.png` is a preview.

Shortcuts are named “AmigaVision” for a single emulator. If another emulator
already has an AmigaVision shortcut, setup renames the existing shortcut to
include its emulator, preserving its target and launch settings, and names the
new shortcut accordingly (for example, “AmigaVision (Amiberry)” and
“AmigaVision (WinUAE)”). This applies to Start menu and desktop shortcuts;
upgrades reuse the existing names.
