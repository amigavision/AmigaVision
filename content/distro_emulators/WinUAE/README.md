# Portable AmigaVision configurations

Use the Amiberry or WinUAE `.uae` file with this folder layout:

```
<emulator working directory>/
  ROMs/AmigaVision.rom
  HardDrives/AmigaVision.hdf
  HardDrives/AmigaVision-Saves.hdf
  HardDrives/Shared/
  Visuals/Shaders/  (Amiberry CRT shader and its dependencies)
```

All paths are relative to the emulator working directory. WinUAE sets that directory itself to its selected data root during startup, so a shortcut's Start in field does not reliably select it. For a standard installation using Public Documents, use this layout:

```
C:\Users\Public\Documents\Amiga Files\WinUAE\
  Configurations\AmigaVision.uae
  Configurations\default.uae (optional)
  ROMs\AmigaVision.rom
  HardDrives\AmigaVision.hdf
  HardDrives\AmigaVision-Saves.hdf
  HardDrives\Shared\
```

Keep the executable in its existing installation directory. Load the configuration through WinUAE's Configurations panel and verify the resolved ROM and disk paths. Enable relative paths in the Paths panel before saving if you want WinUAE to preserve relative paths. Custom or portable installations may select a different data root; the configuration directory alone does not determine that root. For Amiberry, launch from the folder containing ROMs, HardDrives, and Visuals. Existing images and ROMs must be supplied separately.

Windows path handling was checked against https://github.com/tonioni/WinUAE/blob/master/od-win32/win32.cpp (startup data-root selection and SetCurrentDirectory).

The source configuration is unchanged. Both copies preserve its PAL AGA/A1200 chipset, 68030 and 68881, cycle exact settings, disabled JIT, RAM sizes, audio, mouse and keyboard joystick layout 2, borderless fullscreen, and three writable mounts (including their boot priorities).

WinUAE uses Direct3D 11 with CRT-Pi-SmartRes.fx, hires output, doubled lines, and 2x horizontal / 4x vertical filter sizing for normal and interlaced output, transposed from the supplied WinUAE 6.0.3 default.uae. TV aspect correction is retained. The saved file omits gfx_filter_autoscale because auto is the WinUAE 6.0.3 default; the portable config keeps that value explicit. These settings do not enforce integer scaling. Install CRT-Pi-SmartRes.fx under plugins\filtershaders\direct3d in WinUAE's plugin directory. Amiberry's GLSL preset does not transfer directly. Scaling, crop and keyboard joystick behavior need visual/input verification on Windows. WinUAE normally uses F12 for its GUI; the Amiberry-specific open_gui option was omitted.

Duplicate Amiberry search paths were collapsed. Host audio device selection was removed so each platform can use its default device. Empty flash/RTC filenames replace source entries that pointed to a directory rather than a persistence file. The WinUAE copy omits the legacy cpu_type alias in favor of explicit cpu_model and fpu_model, and omits Amiberry-specific settings and unused WHDLoad booter options.

WinUAE option names were checked against https://github.com/tonioni/WinUAE/blob/master/cfgfile.cpp. Static checks verified relative paths, preserved core hardware values, and mount counts. Neither configuration has been boot tested here.

The emulator package includes identical `AmigaVision.uae` and `default.uae` configurations for each emulator. Install `AmigaVision.uae` and skip `default.uae` to preserve your existing emulator default; load AmigaVision explicitly when needed. See each packaged `INSTALL.txt` for details.

The emulator archive has three top-level folders: `Amiberry`, `WinUAE`, and `HardDrives`. The HDF images, Shared directory, and listings are shipped only in that shared `HardDrives` folder. Copy its contents into `HardDrives` under your chosen emulator data folder, in addition to installing the emulator-specific files. The configuration paths remain unchanged.
