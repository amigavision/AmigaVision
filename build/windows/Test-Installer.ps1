# Exercises the compiled installer with synthetic media, never the real release.
$ErrorActionPreference = 'Stop'
$setup = Join-Path $PSScriptRoot 'output/AmigaVision-Setup.exe'
$root = Join-Path ([IO.Path]::GetTempPath()) ('AmigaVision setup test ' + [guid]::NewGuid())
function Put($path, $value) {
    New-Item -ItemType Directory -Force (Split-Path $path) | Out-Null
    [IO.File]::WriteAllText($path, $value)
}
function Assert-Content($path, $expected) {
    if ([IO.File]::ReadAllText($path) -ne $expected) { throw "Unexpected contents: $path" }
}
function Install($emulator, $payload, $data, $exe, $tasks = '') {
    $arguments = @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART',
        "/EMULATOR=$emulator", "`"/PAYLOAD=$payload`"", "`"/DATA=$data`"",
        "`"/EMULATORFILE=$exe`"", "`"/TASKS=$tasks`"", "`"/LOG=$root\$emulator.log`"")
    $process = Start-Process $setup -ArgumentList $arguments -Wait -PassThru
    return $process.ExitCode
}
try {
    $payload = Join-Path $root 'release'
    Put "$payload/HardDrives/AmigaVision.hdf" 'new main'
    Put "$payload/HardDrives/AmigaVision-Saves.hdf" 'fresh saves'
    Put "$payload/HardDrives/Shared/user.txt" 'release shared'
    Put "$payload/HardDrives/Shared/new.txt" 'new shared'
    Put "$payload/HardDrives/listings/games.txt" 'listings'
    foreach ($emulator in @('Amiberry', 'WinUAE')) {
        Put "$payload/$emulator/ROMs/AmigaVision.rom" 'rom'
        $template = if ($emulator -eq 'WinUAE') { 'WinUAE/default.uae' } else { 'Amiberry/AmigaVision-Amiberry.uae' }
        $template = Join-Path $PSScriptRoot "../../content/distro_emulators/$template"
        Put "$payload/$emulator/Configurations/AmigaVision.uae" ([IO.File]::ReadAllText($template))
    }
    Put "$payload/Amiberry/Visuals/Shaders/example.glsl" 'shader'
    Put "$payload/WinUAE/plugins/filtershaders/direct3d/example.fx" 'shader'
    foreach ($emulator in @('Amiberry', 'WinUAE')) {
        $data = Join-Path $root "$emulator data"
        $exe = Join-Path $root "$emulator bin/$($emulator.ToLower()).exe"
        Put $exe 'placeholder executable; not launched'
        # Fresh install creates saves and shared files.
        if ((Install $emulator $payload $data $exe) -ne 0) { throw 'Fresh install failed' }
        Assert-Content "$data/HardDrives/AmigaVision-Saves.hdf" 'fresh saves'
        Assert-Content "$data/HardDrives/Shared/new.txt" 'new shared'
        if (Test-Path "$data/Configurations/default.uae") { throw 'Default was installed without consent' }
        # Upgrade replaces the main image and keeps user data and default settings.
        Put "$data/HardDrives/AmigaVision.hdf" 'old main'
        Put "$data/HardDrives/AmigaVision-Saves.hdf" 'my saves'
        Put "$data/HardDrives/Shared/user.txt" 'my shared'
        Put "$data/Configurations/default.uae" 'my default'
        Put "$data/Configurations/AmigaVision.uae" 'my config'
        if ((Install $emulator $payload $data $exe) -ne 0) { throw 'Upgrade failed' }
        Assert-Content "$data/HardDrives/AmigaVision.hdf" 'new main'
        Assert-Content "$data/HardDrives/AmigaVision-Saves.hdf" 'my saves'
        Assert-Content "$data/HardDrives/Shared/user.txt" 'my shared'
        Assert-Content "$data/Configurations/default.uae" 'my default'
        Assert-Content "$data/Configurations/AmigaVision.uae.backup-1" 'my config'
        $config = Get-Content -Raw "$data/Configurations/AmigaVision.uae"
        if (!$config.Contains("$data\HardDrives\AmigaVision.hdf") -or ($config.Contains('./ROMs/') -or $config.Contains('.\ROMs\'))) {
            throw 'Media paths were not resolved'
        }
        $shader = if ($emulator -eq 'WinUAE') { "$(Split-Path $exe)/plugins/filtershaders/direct3d/example.fx" }
                  else { "$data/Visuals/Shaders/example.glsl" }
        Assert-Content $shader 'shader'
        if ((Install $emulator $payload $data $exe 'defaultconfig') -ne 0) { throw 'Default configuration install failed' }
        Assert-Content "$data/Configurations/default.uae.backup-1" 'my default'
        Assert-Content "$data/Configurations/default.uae" $config
        if ((Install $emulator $payload $payload $exe) -eq 0) { throw 'Overlapping source was accepted' }
        if ((Install $emulator "$root/missing" $data $exe) -eq 0) { throw 'Missing media was accepted' }
        if ((Install $emulator $payload $data "$root/missing.exe") -eq 0) { throw 'Missing executable was accepted' }
    }
    Write-Host 'Fresh installation, upgrades, preservation, backups, paths and invalid input passed.'
} finally {
    # The installer has no uninstaller: remove test shortcuts explicitly.
    foreach ($emulator in @('Amiberry', 'WinUAE')) {
        Remove-Item "${env:APPDATA}/Microsoft/Windows/Start Menu/Programs/AmigaVision ($emulator).lnk" -ErrorAction SilentlyContinue
    }
    Remove-Item -Recurse -Force $root -ErrorAction SilentlyContinue
}
