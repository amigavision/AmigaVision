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
function Read-Shortcut($path) {
    $shell = $null
    $link = $null
    try {
        $shell = New-Object -ComObject WScript.Shell
        $link = $shell.CreateShortcut($path)
        # Return plain strings; never retain a live Shell COM object between installs.
        return [pscustomobject]@{
            TargetPath = [string]$link.TargetPath
            Arguments = [string]$link.Arguments
            IconLocation = [string]$link.IconLocation
        }
    } finally {
        if ($null -ne $link) { [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($link) }
        if ($null -ne $shell) { [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($shell) }
    }
}
function Rename-TestShortcut($path, $newName) {
    $destination = Join-Path (Split-Path $path) $newName
    for ($attempt = 0; $attempt -lt 10; $attempt++) {
        try {
            [IO.File]::Move($path, $destination)
            return
        } catch [IO.IOException] {
            # Shell indexing/antivirus may briefly retain the newly created shortcut.
            $code = $_.Exception.HResult -band 0xffff
            if ($code -notin @(32, 33) -or $attempt -eq 9) { throw }
            Start-Sleep -Milliseconds 200
        }
    }
}
function Find-EmulatorShortcut($folder, $emulator) {
    $plain = Join-Path $folder 'AmigaVision.lnk'
    if (Test-Path $plain) {
        $target = [IO.Path]::GetFileName((Read-Shortcut $plain).TargetPath)
        if (($emulator -eq 'Amiberry' -and $target -ieq 'amiberry.exe') -or
            ($emulator -eq 'WinUAE' -and $target -imatch '^winuae(64)?\.exe$') -or
            ($emulator -eq 'Copperline' -and $target -ieq 'copperline.exe')) { return $plain }
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
    Put "$payload/Amiberry/HardDrives/AmigaVision.hdf" 'new main'
    Put "$payload/Amiberry/HardDrives/AmigaVision-Saves.hdf" 'fresh saves'
    Put "$payload/Amiberry/HardDrives/Shared/user.txt" 'release shared'
    Put "$payload/Amiberry/HardDrives/Shared/new.txt" 'new shared'
    Put "$payload/Amiberry/HardDrives/listings/games.txt" 'listings'
    foreach ($emulator in @('Amiberry', 'WinUAE')) {
        Put "$payload/$emulator/ROMs/AmigaVision.rom" 'rom'
        $template = if ($emulator -eq 'WinUAE') { 'WinUAE/default.uae' } else { 'Amiberry/AmigaVision-Amiberry.uae' }
        $template = Join-Path $PSScriptRoot "../../content/distro_emulators/$template"
        Put "$payload/$emulator/Configurations/AmigaVision.uae" ([IO.File]::ReadAllText($template))
    }
    Put "$payload/Amiberry/Visuals/Shaders/example.glsl" 'shader'
    Copy-Item -Recurse -Force "$PSScriptRoot/../../content/distro_emulators/Amiberry/Visuals/*" "$payload/Amiberry/Visuals"
    Put "$payload/WinUAE/plugins/filtershaders/direct3d/CRT-Pi-SmartRes.fx" 'shader'
    # Exercise migration of the shader settings in already published releases.
    Put "$payload/Copperline/configs/AmigaVision.toml" ([IO.File]::ReadAllText("$PSScriptRoot/../../content/distro_emulators/Copperline/AmigaVision.toml"))
    $legacyConfig = "$payload/Amiberry/Configurations/AmigaVision.uae"
    $legacyText = [IO.File]::ReadAllText($legacyConfig).Replace('amiberry.shader=', 'shader=').Replace('gfx_lores=false', 'gfx_lores=true').Replace('gfx_resolution=hires', 'gfx_resolution=lores').Replace('gfx_linemode=double', 'gfx_linemode=none')
    Put $legacyConfig ($legacyText + "`nshaders_path=Visuals/Shaders`n")
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
        $shader = if ($emulator -eq 'WinUAE') { "$(Split-Path $exe)/plugins/filtershaders/direct3d/CRT-Pi-SmartRes.fx" }
                  else { "$data/Visuals/Shaders/example.glsl" }
        Assert-Content $shader 'shader'
        $installedIcon = Join-Path $data 'AmigaVision.ico'
        if ((Get-FileHash $installedIcon).Hash -ne (Get-FileHash "$PSScriptRoot/assets/AmigaVision.ico").Hash) {
            throw 'The installed AmigaVision icon does not match the bundled artwork'
        }
        $shortcut = Read-Shortcut (Find-EmulatorShortcut "${env:APPDATA}/Microsoft/Windows/Start Menu/Programs" $emulator)
        if ($shortcut.IconLocation -ne "$installedIcon,0") { throw 'Shortcut does not use the AmigaVision icon' }
        if ($emulator -eq 'Amiberry') {
            if (!$shortcut.Arguments.Contains('-o "shaders_path=' + $data + '\Visuals\Shaders"')) { throw 'Launcher does not set the application shader directory' }
            if (!$config.Contains('amiberry.shader=crt/crt-easymode-halation.glslp')) { throw 'Amiberry preset is not configured' }
            foreach ($setting in @('gfx_lores=false', 'gfx_resolution=hires', 'gfx_linemode=double')) {
                if (!$config.Contains($setting)) { throw "Amiberry display setting does not match the reference setup: $setting" }
            }
            $preset = Join-Path $data 'Visuals/Shaders/crt/crt-easymode-halation.glslp'
            $passes = [regex]::Matches((Get-Content -Raw $preset), '(?m)^shader\d+\s*=\s*"([^"]+)"')
            if ($passes.Count -ne 5) { throw 'Incomplete shader preset' }
            foreach ($pass in $passes) {
                if (!(Test-Path (Join-Path (Split-Path $preset) $pass.Groups[1].Value))) { throw 'Missing shader pass' }
            }
        }
        if ((Install $emulator $payload $data $exe 'defaultconfig') -ne 0) { throw 'Default configuration install failed' }
        Assert-Content "$data/Configurations/default.uae.backup-1" 'my default'
        Assert-Content "$data/Configurations/default.uae" $config
        if ((Install $emulator $payload $payload $exe) -eq 0) { throw 'Overlapping source was accepted' }
        if ((Install $emulator "$root/missing" $data $exe) -eq 0) { throw 'Missing media was accepted' }
        if ((Install $emulator $payload $data "$root/missing.exe") -eq 0) { throw 'Missing executable was accepted' }
    }
    # Permission failures must be detected before copying the main image.
    # Copperline uses the canonical Amiberry media and a separate TOML config.
    $copperExe = Join-Path $root 'Copperline bin/copperline.exe'
    $copperHome = Split-Path $copperExe
    $copperData = Join-Path $root 'Copperline data'
    Put $copperExe 'placeholder executable; not launched'
    Put "$copperHome/portable.txt" ''
    Put "$copperHome/configs/default.toml" 'my Copperline default'
    if ((Install 'Copperline' $payload $copperData $copperExe) -ne 0) { throw 'Copperline install failed' }
    Assert-Content "$copperHome/configs/default.toml" 'my Copperline default'
    Assert-Content "$copperHome/configs/AmigaVision.toml" (Get-Content -Raw "$copperData/configs/AmigaVision.toml")
    Assert-Content "$copperData/HardDrives/AmigaVision.hdf" 'new main'
    Assert-Content "$copperData/ROMs/AmigaVision.rom" 'rom'
    $copperConfig = Get-Content -Raw "$copperData/configs/AmigaVision.toml"
    $forwardData = $copperData.Replace('\', '/')
    foreach ($path in @('ROMs/AmigaVision.rom', 'HardDrives/AmigaVision.hdf', 'HardDrives/AmigaVision-Saves.hdf')) {
        if (!$copperConfig.Contains("$forwardData/$path")) { throw "Copperline media path incorrect: $path" }
    }
    if ($copperConfig.Contains('../Amiberry')) { throw 'Copperline media paths were not resolved' }
    $copperLink = Read-Shortcut (Find-EmulatorShortcut "${env:APPDATA}/Microsoft/Windows/Start Menu/Programs" 'Copperline')
    if ($copperLink.TargetPath -ne $copperExe -or !$copperLink.Arguments.Contains('--config "' + $copperData + '\configs\AmigaVision.toml"')) { throw 'Copperline shortcut is incorrect' }
    Put "$copperData/HardDrives/AmigaVision-Saves.hdf" 'my Copperline saves'
    Put "$copperData/configs/AmigaVision.toml" 'my Copperline config'
    if ((Install 'Copperline' $payload $copperData $copperExe 'defaultconfig') -ne 0) { throw 'Copperline startup configuration failed' }
    Assert-Content "$copperHome/configs/default.toml.backup-1" 'my Copperline default'
    Assert-Content "$copperHome/configs/default.toml" $copperConfig
    Assert-Content "$copperData/configs/AmigaVision.toml.backup-1" 'my Copperline config'
    Assert-Content "$copperData/HardDrives/AmigaVision-Saves.hdf" 'my Copperline saves'

    $protectedBin = Join-Path $root 'protected WinUAE'
    Put "$protectedBin/winuae64.exe" 'placeholder'
    $shaderDir = Join-Path $protectedBin 'plugins/filtershaders/direct3d'
    New-Item -ItemType Directory -Force $shaderDir | Out-Null
    $acl = Get-Acl $shaderDir
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent().User
    $deny = New-Object Security.AccessControl.FileSystemAccessRule($identity, 'Write', 'ContainerInherit,ObjectInherit', 'None', 'Deny')
    $restricted = Get-Acl $shaderDir
    $restricted.AddAccessRule($deny)
    try {
        Set-Acl $shaderDir $restricted
        if ((Install 'WinUAE' $payload "$root/protected install" "$protectedBin/winuae64.exe") -eq 0) { throw 'Protected shader installation should require elevation' }
        if (Test-Path "$root/protected install/HardDrives/AmigaVision.hdf") { throw 'Permission check happened after main-image copying' }
        if (!(Get-Content -Raw "$root/WinUAE.log").Contains('requires administrator access')) { throw 'Missing explanation of required administrator access' }
    } finally { Set-Acl $shaderDir $acl }
    # Exercise the helper directly on the elevated CI runner; no interactive UAC on CI.
    $helper = Join-Path $PSScriptRoot 'output/WinUAEShaderSetup.exe'
    $helperArgs = @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART',
        "`"/SHADERSOURCE=$payload/WinUAE/plugins/filtershaders/direct3d/CRT-Pi-SmartRes.fx`"",
        "`"/WINUAEDIR=$protectedBin`"", "`"/LOG=$root/shader-helper.log`"")
    $helperProcess = Start-Process $helper -ArgumentList $helperArgs -PassThru
    if (!$helperProcess.WaitForExit(120000)) {
        & taskkill.exe /PID $helperProcess.Id /T /F | Out-Null
        throw 'Shader helper timed out'
    }
    $helperProcess.Refresh()
    if ($helperProcess.ExitCode -ne 0) { throw 'Shader helper failed' }
    Assert-Content "$shaderDir/CRT-Pi-SmartRes.fx" 'shader'

    # Verify names and original targets survive a second emulator and subsequent upgrades.
    $programs = "${env:APPDATA}/Microsoft/Windows/Start Menu/Programs"
    $desktop = [Environment]::GetFolderPath('Desktop')
    foreach ($folder in @($programs, $desktop)) {
        foreach ($name in @('AmigaVision', 'AmigaVision (Amiberry)', 'AmigaVision (WinUAE)', 'AmigaVision (Copperline)')) {
            Remove-Item "$folder/$name.lnk" -ErrorAction SilentlyContinue
        }
    }
    $amiberryExe = Join-Path $root 'Amiberry bin/amiberry.exe'
    $winuaeExe = Join-Path $root 'WinUAE bin/winuae.exe'
    if ((Install 'Amiberry' $payload "$root/shortcut Amiberry" $amiberryExe 'desktopicon') -ne 0) { throw 'Single-emulator install failed' }
    foreach ($folder in @($programs, $desktop)) {
        if (!(Test-Path "$folder/AmigaVision.lnk")) { throw 'Single emulator should use the plain AmigaVision name' }
        if (Test-Path "$folder/AmigaVision (Amiberry).lnk") { throw 'Unnecessary emulator suffix' }
    }
    foreach ($folder in @($programs, $desktop)) {
        Rename-TestShortcut "$folder/AmigaVision.lnk" 'AmigaVision (Amiberry).lnk'
    }
    if ((Install 'Amiberry' $payload "$root/shortcut Amiberry" $amiberryExe 'desktopicon') -ne 0) { throw 'Legacy shortcut migration failed' }
    foreach ($folder in @($programs, $desktop)) {
        if (!(Test-Path "$folder/AmigaVision.lnk") -or (Test-Path "$folder/AmigaVision (Amiberry).lnk")) {
            throw 'Lone legacy shortcut did not migrate to the plain name'
        }
    }
    $oldArguments = (Read-Shortcut "$programs/AmigaVision.lnk").Arguments
    if ((Install 'WinUAE' $payload "$root/shortcut WinUAE" $winuaeExe 'desktopicon') -ne 0) { throw 'Second-emulator install failed' }
    foreach ($folder in @($programs, $desktop)) {
        if (Test-Path "$folder/AmigaVision.lnk") { throw 'Ambiguous plain shortcut remains' }
        $old = Read-Shortcut "$folder/AmigaVision (Amiberry).lnk"
        if ($old.TargetPath -ne $amiberryExe -or $old.Arguments -ne $oldArguments) { throw 'Renaming changed the original shortcut configuration' }
        if ((Read-Shortcut "$folder/AmigaVision (WinUAE).lnk").TargetPath -ne $winuaeExe) { throw 'New emulator shortcut is wrong' }
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

    # Setup ships inside the extracted package and finds its sibling folders itself.
    $originalSetup = $setup
    $setup = Join-Path $payload 'Install AmigaVision for Windows.exe'
    Copy-Item $originalSetup $setup
    $exe = Join-Path $root 'Amiberry bin/amiberry.exe'
    try {
        if ((Install 'Amiberry' '' "$root/packaged install" $exe) -ne 0) { throw 'Packaged installer did not use its sibling Amiberry folder' }
        Assert-Content "$root/packaged install/HardDrives/AmigaVision.hdf" 'new main'
        $winuae = Join-Path $root 'WinUAE bin/winuae.exe'
        if ((Install 'WinUAE' '' "$root/packaged WinUAE" $winuae) -ne 0) { throw 'WinUAE did not use the canonical Amiberry disk files' }
        Assert-Content "$root/packaged WinUAE/HardDrives/AmigaVision.hdf" 'new main'
        if ((Install 'Copperline' '' "$root/packaged Copperline" $copperExe) -ne 0) { throw 'Copperline did not use the packaged media' }
        Assert-Content "$root/packaged Copperline/HardDrives/AmigaVision.hdf" 'new main'
        $setup = Join-Path $root 'Install AmigaVision for Windows.exe'
        Copy-Item $originalSetup $setup
        if ((Install 'Amiberry' '' "$root/detached install" $exe) -eq 0) { throw 'Detached installer should reject missing sibling folders' }
        if (Test-Path "$root/detached install/HardDrives/AmigaVision.hdf") { throw 'Detached setup copied files' }
    } finally { $setup = $originalSetup }

    # Keep registry fixtures below a neutral parent so portable discovery cannot
    # find them while scanning the release's parent directory one level deep.
    # Remove each fixture before the next case, including the executable files.
    # Detect installed applications from both registry views without an executable argument.
    foreach ($view in @([Microsoft.Win32.RegistryView]::Registry32, [Microsoft.Win32.RegistryView]::Registry64)) {
        $registry = [Microsoft.Win32.RegistryKey]::OpenBaseKey([Microsoft.Win32.RegistryHive]::CurrentUser, $view)
        try {
            foreach ($emulator in @('Amiberry', 'WinUAE', 'Copperline')) {
                $bin = Join-Path $root "registry fixtures/$view/$emulator"
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
                    $shortcut = Read-Shortcut (Find-EmulatorShortcut "${env:APPDATA}/Microsoft/Windows/Start Menu/Programs" $emulator)
                    if ($shortcut.TargetPath -ne $expected) { throw "Wrong detected executable: $($shortcut.TargetPath); expected $expected" }
                } finally {
                    $registry.DeleteSubKeyTree($keyPath, $false)
                    Remove-Item -Recurse -Force $bin
                }
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
    foreach ($emulator in @('Amiberry', 'WinUAE', 'Copperline')) {
        Remove-Item "$([Environment]::GetFolderPath('Desktop'))/AmigaVision ($emulator).lnk" -ErrorAction SilentlyContinue
        Remove-Item "${env:APPDATA}/Microsoft/Windows/Start Menu/Programs/AmigaVision ($emulator).lnk" -ErrorAction SilentlyContinue
    }
    Remove-Item -Recurse -Force $root -ErrorAction SilentlyContinue
}
