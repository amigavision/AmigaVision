; Elevated data-only worker. The parent handles shortcuts and launching as the original user.
[Setup]
AppId=AmigaVisionProtectedData
AppName=AmigaVision Data Installer
AppVersion=0.1.0
AppPublisher=AmigaVision
SetupIconFile=assets\AmigaVision.ico
DefaultDirName={tmp}\AmigaVision
CreateAppDir=no
Uninstallable=no
PrivilegesRequired=admin
DisableWelcomePage=yes
DisableDirPage=yes
DisableProgramGroupPage=yes
DisableReadyPage=yes
DisableFinishedPage=yes
OutputDir=output
OutputBaseFilename=ProtectedDataSetup

[Files]
Source: "assets\AmigaVision.ico"; DestDir: "{param:DATA}"; Flags: ignoreversion
Source: "{param:PAYLOAD}\Amiberry\HardDrives\AmigaVision.hdf"; DestDir: "{param:DATA}\HardDrives"; Flags: external ignoreversion
Source: "{param:PAYLOAD}\Amiberry\HardDrives\AmigaVision-Saves.hdf"; DestDir: "{param:DATA}\HardDrives"; Flags: external onlyifdoesntexist
Source: "{param:PAYLOAD}\Amiberry\HardDrives\Shared\*"; DestDir: "{param:DATA}\HardDrives\Shared"; Flags: external recursesubdirs createallsubdirs onlyifdoesntexist
Source: "{param:PAYLOAD}\Amiberry\HardDrives\listings\*"; DestDir: "{param:DATA}\HardDrives\listings"; Flags: external recursesubdirs createallsubdirs ignoreversion
Source: "{param:PAYLOAD}\Amiberry\ROMs\AmigaVision.rom"; DestDir: "{param:DATA}\ROMs"; Flags: external ignoreversion
Source: "{param:PAYLOAD}\Amiberry\Visuals\*"; DestDir: "{param:DATA}\Visuals"; Flags: external recursesubdirs createallsubdirs ignoreversion; Check: IsAmiberry

[Code]
var
  ConfigText: AnsiString;

function IsAmiberry: Boolean;
begin
  Result := CompareText(ExpandConstant('{param:EMULATOR|}'), 'Amiberry') = 0;
end;

function InitializeSetup: Boolean;
var
  Root, Source, Kind: String;
begin
  Root := ExpandConstant('{param:DATA|}');
  Source := ExpandConstant('{param:PAYLOAD|}');
  Kind := ExpandConstant('{param:EMULATOR|}');
  Result := (ExpandConstant('{param:DATAUSER|}') <> '') and
    ((Copy(Root, 1, 2) = '\\') or
    ((Length(Root) >= 3) and (Copy(Root, 2, 2) = ':\'))) and
    ((Kind = 'Amiberry') or (Kind = 'Copperline') or (Kind = 'WinUAE')) and
    FileExists(Source + '\Amiberry\HardDrives\AmigaVision.hdf') and
    FileExists(Source + '\Amiberry\HardDrives\AmigaVision-Saves.hdf') and
    FileExists(Source + '\Amiberry\ROMs\AmigaVision.rom') and
    LoadStringFromFile(ExpandConstant('{param:CONFIG|}'), ConfigText);
  // Never overwrite files in the source package itself.
  if Result then
    Result := (Pos(Lowercase(AddBackslash(ExpandFileName(Source))),
      Lowercase(AddBackslash(ExpandFileName(Root)))) <> 1) and
      (Pos(Lowercase(AddBackslash(ExpandFileName(Root))),
      Lowercase(AddBackslash(ExpandFileName(Source)))) <> 1);
end;

procedure WriteConfig(Name: String);
var
  Backup: String;
  Index: Integer;
begin
  if FileExists(Name) then begin
    Index := 1;
    repeat
      Backup := Name + '.backup-' + IntToStr(Index);
      Index := Index + 1;
    until not FileExists(Backup);
    if not CopyFile(Name, Backup, True) then
      RaiseException('Could not back up ' + Name);
  end;
  if not SaveStringToFile(Name, ConfigText, False) then
    RaiseException('Could not write ' + Name);
end;


procedure AllowOriginalUserWrites(const Folder: String);
var
  ExitCode: Integer;
  User: String;
begin
  User := ExpandConstant('{param:DATAUSER|}');
  if User = '' then RaiseException('The original Windows account was not supplied.');
  // Grant access only to AmigaVision data, never to the emulator executable folder.
  if not Exec(ExpandConstant('{sys}\icacls.exe'),
    '"' + Folder + '" /grant "' + User + ':(OI)(CI)M" /T /Q',
    '', SW_HIDE, ewWaitUntilTerminated, ExitCode) then
    RaiseException('Could not set data permissions for the original Windows account.');
  if ExitCode <> 0 then
    RaiseException('Could not make AmigaVision data writable for the original Windows account.');
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  Folder, Extension: String;
begin
  if CurStep <> ssPostInstall then exit;
  if ExpandConstant('{param:EMULATOR|}') = 'Copperline' then begin
    Folder := ExpandConstant('{param:DATA}') + '\configs';
    Extension := '.toml';
  end else begin
    Folder := ExpandConstant('{param:DATA}') + '\Configurations';
    Extension := '.uae';
  end;
  if not ForceDirectories(Folder) then RaiseException('Could not create the configuration folder.');
  WriteConfig(Folder + '\AmigaVision' + Extension);
  if ExpandConstant('{param:DEFAULTCONFIG|0}') = '1' then
    WriteConfig(Folder + '\default' + Extension);
  AllowOriginalUserWrites(ExpandConstant('{param:DATA}') + '\HardDrives');
  AllowOriginalUserWrites(Folder);
end;
