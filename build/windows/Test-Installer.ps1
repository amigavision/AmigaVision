# Exercises the compiled installer with synthetic media, never the real release.
$ErrorActionPreference = 'Stop'
$setup = Join-Path $PSScriptRoot 'output/Install AmigaVision for Windows.exe'
$registryTestName = 'AmigaVision-emulator-discovery-' + [guid]::NewGuid()
$root = Join-Path ([IO.Path]::GetTempPath()) ('AmigaVision setup test ' + [guid]::NewGuid())
function Put($path, $value) {
    New-Item -ItemType Directory -Force (Split-Path $path) | Out-Null
    [IO.File]::WriteAllText($path, $value)
}
function Assert-Content($path, $expected) {
    if ([IO.File]::ReadAllText($path) -ne $expected) { throw "Unexpected contents: $path" }
}
function Find-EmulatorShortcut($folder, $emulator) {
    $plain = Join-Path $folder 'AmigaVision.lnk'
    if (Test-Path $plain) {
        $shell = New-Object -ComObject WScript.Shell
        $target = [IO.Path]::GetFileName($shell.CreateShortcut($plain).TargetPath)
        if (($emulator -eq 'Amiberry' -and $target -ieq 'amiberry.exe') -or
            ($emulator -eq 'WinUAE' -and $target -imatch '^winuae(64)?\.exe$')) { return $plain }
    }
    return Join-Path $folder "AmigaVision ($emulator).lnk"
}
function Install($emulator, $payload, $data, $exe, $tasks = '') {
    $arguments = @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/CURRENTUSER',
        "/EMULATOR=$emulator", "`"/PAYLOAD=$payload`"", "`"/DATA=$data`"",
        "`"/EMULATORFILE=$exe`"", "`"/TASKS=$tasks`"", "`"/LOG=$root\$emulator.log`"")
    if ($tasks -eq '__defaults__') {
        $arguments = $arguments | Where-Object { $_ -notlike '*TASKS=*' }
    }
    if ($payload -eq '') {
        $arguments = $arguments | Where-Object { $_ -notlike '*PAYLOAD=*' }
    }
    if ($exe -eq '') {
        $arguments = $arguments | Where-Object { $_ -notlike '*EMULATORFILE=*' }
    }
    Write-Host "Testing $emulator, tasks='$tasks', payload='$payload', data='$data'"
    $process = Start-Process $setup -ArgumentList $arguments -PassThru
    if (!$process.WaitForExit(120000)) {
        & taskkill.exe /PID $process.Id /T /F | Out-Null
        throw "Installer timed out for $emulator. See the saved setup log."
    }
    $process.Refresh()
    Write-Host "Installer exit code: $($process.ExitCode)"
    if ($process.ExitCode -ne 0 -and (Test-Path "$root/$emulator.log")) {
        Get-Content "$root/$emulator.log" | Select-Object -Last 30 | Write-Host
    }
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
        $installedIcon = Join-Path $data 'AmigaVision.ico'
        if ((Get-FileHash $installedIcon).Hash -ne (Get-FileHash "$PSScriptRoot/assets/AmigaVision.ico").Hash) {
            throw 'The installed AmigaVision icon does not match the bundled artwork'
        }
        $shell = New-Object -ComObject WScript.Shell
        $shortcut = $shell.CreateShortcut((Find-EmulatorShortcut "${env:APPDATA}/Microsoft/Windows/Start Menu/Programs" $emulator))
        if ($shortcut.IconLocation -ne "$installedIcon,0") { throw 'Shortcut does not use the AmigaVision icon' }
        if ((Install $emulator $payload $data $exe 'defaultconfig') -ne 0) { throw 'Default configuration install failed' }
        Assert-Content "$data/Configurations/default.uae.backup-1" 'my default'
        Assert-Content "$data/Configurations/default.uae" $config
        if ((Install $emulator $payload $payload $exe) -eq 0) { throw 'Overlapping source was accepted' }
        if ((Install $emulator "$root/missing" $data $exe) -eq 0) { throw 'Missing media was accepted' }
        if ((Install $emulator $payload $data "$root/missing.exe") -eq 0) { throw 'Missing executable was accepted' }
    }
    # Verify names and original targets survive a second emulator and subsequent upgrades.
    $programs = "${env:APPDATA}/Microsoft/Windows/Start Menu/Programs"
    $desktop = [Environment]::GetFolderPath('Desktop')
    foreach ($folder in @($programs, $desktop)) {
        foreach ($name in @('AmigaVision', 'AmigaVision (Amiberry)', 'AmigaVision (WinUAE)')) {
            Remove-Item "$folder/$name.lnk" -ErrorAction SilentlyContinue
        }
    }
    $amiberryExe = Join-Path $root 'Amiberry bin/amiberry.exe'
    $winuaeExe = Join-Path $root 'WinUAE bin/winuae.exe'
    if ((Install 'Amiberry' $payload "$root/shortcut Amiberry" $amiberryExe 'desktopicon') -ne 0) { throw 'Single-emulator install failed' }
    $shell = New-Object -ComObject WScript.Shell
    foreach ($folder in @($programs, $desktop)) {
        if (!(Test-Path "$folder/AmigaVision.lnk")) { throw 'Single emulator should use the plain AmigaVision name' }
        if (Test-Path "$folder/AmigaVision (Amiberry).lnk") { throw 'Unnecessary emulator suffix' }
    }
    foreach ($folder in @($programs, $desktop)) {
        Rename-Item "$folder/AmigaVision.lnk" 'AmigaVision (Amiberry).lnk'
    }
    if ((Install 'Amiberry' $payload "$root/shortcut Amiberry" $amiberryExe 'desktopicon') -ne 0) { throw 'Legacy shortcut migration failed' }
    foreach ($folder in @($programs, $desktop)) {
        if (!(Test-Path "$folder/AmigaVision.lnk") -or (Test-Path "$folder/AmigaVision (Amiberry).lnk")) {
            throw 'Lone legacy shortcut did not migrate to the plain name'
        }
    }
    $oldArguments = $shell.CreateShortcut("$programs/AmigaVision.lnk").Arguments
    if ((Install 'WinUAE' $payload "$root/shortcut WinUAE" $winuaeExe 'desktopicon') -ne 0) { throw 'Second-emulator install failed' }
    foreach ($folder in @($programs, $desktop)) {
        if (Test-Path "$folder/AmigaVision.lnk") { throw 'Ambiguous plain shortcut remains' }
        $old = $shell.CreateShortcut("$folder/AmigaVision (Amiberry).lnk")
        if ($old.TargetPath -ne $amiberryExe -or $old.Arguments -ne $oldArguments) { throw 'Renaming changed the original shortcut configuration' }
        if ($shell.CreateShortcut("$folder/AmigaVision (WinUAE).lnk").TargetPath -ne $winuaeExe) { throw 'New emulator shortcut is wrong' }
    }
    if ((Install 'WinUAE' $payload "$root/shortcut WinUAE" $winuaeExe 'desktopicon') -ne 0) { throw 'Second-emulator upgrade failed' }
    foreach ($folder in @($programs, $desktop)) {
        if (@(Get-ChildItem $folder -Filter 'AmigaVision*.lnk').Count -ne 2) { throw 'Upgrade created duplicate shortcuts' }
    }

    # A normal interactive install selects the default configuration and desktop shortcut.
    $exe = Join-Path $root 'Amiberry bin/amiberry.exe'
    $defaultData = Join-Path $root 'default choices'
    if ((Install 'Amiberry' $payload $defaultData $exe '__defaults__') -ne 0) { throw 'Default choices installation failed' }
    Assert-Content "$defaultData/Configurations/default.uae" (Get-Content -Raw "$defaultData/Configurations/AmigaVision.uae")
    $desktop = [Environment]::GetFolderPath('Desktop')
    if (!(Test-Path (Find-EmulatorShortcut $desktop 'Amiberry'))) { throw 'Desktop shortcut was not enabled by default' }

    # Accept downloaded archives directly and discover one beside the installer.
    $archive = Join-Path $root 'AmigaVision-Emulators-test.zip'
    Compress-Archive -Path "$payload/*" -DestinationPath $archive
    $exe = Join-Path $root 'Amiberry bin/amiberry.exe'
    if ((Install 'Amiberry' $archive "$root/from zip" $exe) -ne 0) { throw 'ZIP release installation failed' }
    Assert-Content "$root/from zip/HardDrives/AmigaVision.hdf" 'new main'
    $sevenZip = "$env:ProgramFiles/7-Zip/7z.exe"
    $archive7z = Join-Path $root 'AmigaVision-Emulators-test.7z'
    Push-Location $payload
    try {
        & $sevenZip a '-t7z' $archive7z '.\*' | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'Could not build test 7z release' }
    } finally { Pop-Location }
    if ((Install 'Amiberry' $archive7z "$root/from 7z" $exe) -ne 0) { throw '7z release installation failed' }
    Assert-Content "$root/from 7z/HardDrives/AmigaVision.hdf" 'new main'
    $originalSetup = $setup
    $setup = Join-Path $root 'Install AmigaVision for Windows.exe'
    Copy-Item $originalSetup $setup
    try {
        if ((Install 'Amiberry' '' "$root/ambiguous release" $exe) -eq 0) { throw 'Silently chose among multiple releases' }
        Remove-Item $archive7z
        if ((Install 'Amiberry' '' "$root/nearby archive" $exe) -ne 0) { throw 'Nearby archive was not discovered' }
        Assert-Content "$root/nearby archive/HardDrives/AmigaVision.hdf" 'new main'
        Remove-Item $archive
        $nearbyFolder = Join-Path $root 'AmigaVision-Emulators-test'
        Copy-Item -Recurse $payload $nearbyFolder
        if ((Install 'Amiberry' '' "$root/nearby extracted" $exe) -ne 0) { throw 'Nearby extracted release was not discovered' }
        Assert-Content "$root/nearby extracted/HardDrives/AmigaVision.hdf" 'new main'
    } finally { $setup = $originalSetup }

    # Detect installed applications from both registry views without an executable argument.
    foreach ($view in @([Microsoft.Win32.RegistryView]::Registry32, [Microsoft.Win32.RegistryView]::Registry64)) {
        $registry = [Microsoft.Win32.RegistryKey]::OpenBaseKey([Microsoft.Win32.RegistryHive]::CurrentUser, $view)
        try {
            foreach ($emulator in @('Amiberry', 'WinUAE')) {
                $bin = Join-Path $root "$emulator registered $view"
                $expected = Join-Path $bin "$($emulator.ToLower()).exe"
                Put $expected 'placeholder'
                if ($emulator -eq 'WinUAE') {
                    $expected = Join-Path $bin 'winuae64.exe'
                    Put $expected '64-bit placeholder; must be preferred over winuae.exe'
                }
                $keyPath = "Software\Microsoft\Windows\CurrentVersion\Uninstall\$registryTestName"
                $key = $registry.CreateSubKey($keyPath)
                try {
                    $key.SetValue('DisplayName', "$emulator (AmigaVision discovery test)")
                    $key.SetValue('InstallLocation', $bin)
                } finally { $key.Dispose() }
                try {
                    $data = Join-Path $root "$emulator detected $view"
                    if ((Install $emulator $payload $data '') -ne 0) { throw "Discovery failed for $emulator in $view" }
                    $shell = New-Object -ComObject WScript.Shell
                    $shortcut = $shell.CreateShortcut((Find-EmulatorShortcut "${env:APPDATA}/Microsoft/Windows/Start Menu/Programs" $emulator))
                    if ($shortcut.TargetPath -ne $expected) { throw "Wrong detected executable: $($shortcut.TargetPath); expected $expected" }
                } finally { $registry.DeleteSubKeyTree($keyPath, $false) }
            }
        } finally { $registry.Dispose() }
    }
    Write-Host 'Installation, upgrades, preservation, backups, paths, discovery in both registry views and WinUAE 64-bit preference passed.'
} finally {
    $logs = Join-Path $PSScriptRoot 'output/test-logs'
    New-Item -ItemType Directory -Force $logs | Out-Null
    Get-ChildItem $root -Filter '*.log' -ErrorAction SilentlyContinue |
        Copy-Item -Destination $logs
    # The installer has no uninstaller: remove test shortcuts explicitly.
    Remove-Item "$([Environment]::GetFolderPath('Desktop'))/AmigaVision.lnk" -ErrorAction SilentlyContinue
    Remove-Item "${env:APPDATA}/Microsoft/Windows/Start Menu/Programs/AmigaVision.lnk" -ErrorAction SilentlyContinue
    foreach ($emulator in @('Amiberry', 'WinUAE')) {
        Remove-Item "$([Environment]::GetFolderPath('Desktop'))/AmigaVision ($emulator).lnk" -ErrorAction SilentlyContinue
        Remove-Item "${env:APPDATA}/Microsoft/Windows/Start Menu/Programs/AmigaVision ($emulator).lnk" -ErrorAction SilentlyContinue
    }
    Remove-Item -Recurse -Force $root -ErrorAction SilentlyContinue
}
