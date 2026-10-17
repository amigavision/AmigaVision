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

All paths are relative to the emulator working directory. Launch the emulator from that directory; placing a configuration in a Configurations subfolder does not by itself establish its path base. In WinUAE, verify the resolved ROM and disk paths in the GUI on first load, then save the configuration with relative paths enabled. Existing images and ROMs must be supplied separately.

The source configuration is unchanged. Both copies preserve its PAL AGA/A1200 chipset, 68030 and 68881, cycle exact settings, disabled JIT, RAM sizes, audio, mouse and keyboard joystick layout 2, borderless fullscreen, and three writable mounts (including their boot priorities).

WinUAE uses Direct3D 11 and auto scaling with TV aspect correction as an approximation of Amiberry auto-cropping and aspect preservation. Amiberry's GLSL preset does not transfer directly; select an appropriate WinUAE CRT effect in its Filter settings if desired. Scaling, crop and keyboard joystick behavior need visual/input verification on Windows. WinUAE normally uses F12 for its GUI; the Amiberry-specific open_gui option was omitted.

Duplicate Amiberry search paths were collapsed. Host audio device selection was removed so each platform can use its default device. Empty flash/RTC filenames replace source entries that pointed to a directory rather than a persistence file. The WinUAE copy omits the legacy cpu_type alias in favor of explicit cpu_model and fpu_model, and omits Amiberry-specific settings and unused WHDLoad booter options.

WinUAE option names were checked against https://github.com/tonioni/WinUAE/blob/master/cfgfile.cpp. Static checks verified relative paths, preserved core hardware values, and mount counts. Neither configuration has been boot tested here.
