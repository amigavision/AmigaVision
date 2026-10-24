; Compile with Inno Setup 6. The release payload remains external to this EXE.
#ifndef ReleaseVersion
  #define ReleaseVersion "0.1.0"
#endif
[Setup]
AppId=AmigaVisionSetup
AppName=AmigaVision
AppVersion={#ReleaseVersion}
AppPublisher=AmigaVision
AppPublisherURL=https://amiga.vision
DefaultDirName={userdocs}\AmigaVision
CreateAppDir=no
Uninstallable=no
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
DisableDirPage=yes
DisableProgramGroupPage=yes
UsePreviousTasks=no
WizardStyle=modern
OutputDir=output
OutputBaseFilename=AmigaVision-Setup
Compression=lzma2

[Tasks]
Name: defaultconfig; Description: "Make AmigaVision the emulator's default configuration (backs up the existing file)"; Flags: unchecked
Name: desktopicon; Description: "Create a desktop shortcut"; Flags: unchecked

[Files]
Source: "{code:Payload}\HardDrives\AmigaVision.hdf"; DestDir: "{code:DataRoot}\HardDrives"; Flags: external ignoreversion
Source: "{code:Payload}\HardDrives\AmigaVision-Saves.hdf"; DestDir: "{code:DataRoot}\HardDrives"; Flags: external onlyifdoesntexist
Source: "{code:Payload}\HardDrives\Shared\*"; DestDir: "{code:DataRoot}\HardDrives\Shared"; Flags: external recursesubdirs createallsubdirs onlyifdoesntexist
Source: "{code:Payload}\HardDrives\listings\*"; DestDir: "{code:DataRoot}\HardDrives\listings"; Flags: external recursesubdirs createallsubdirs ignoreversion
Source: "{code:Payload}\{code:Emulator}\ROMs\AmigaVision.rom"; DestDir: "{code:DataRoot}\ROMs"; Flags: external ignoreversion
Source: "{code:Payload}\Amiberry\Visuals\*"; DestDir: "{code:DataRoot}\Visuals"; Flags: external recursesubdirs createallsubdirs ignoreversion; Check: IsAmiberry
Source: "{code:Payload}\WinUAE\plugins\*"; DestDir: "{code:ExeRoot}\plugins"; Flags: external recursesubdirs createallsubdirs ignoreversion; Check: IsWinUAE

[Icons]
Name: "{userprograms}\AmigaVision ({code:Emulator})"; Filename: "{code:ExePath}"; Parameters: "{code:LaunchArgs}"; WorkingDir: "{code:DataRoot}"
Name: "{userdesktop}\AmigaVision ({code:Emulator})"; Filename: "{code:ExePath}"; Parameters: "{code:LaunchArgs}"; WorkingDir: "{code:DataRoot}"; Tasks: desktopicon

[Code]
var
  TargetPage: TInputOptionWizardPage;
  SourcePage, DataPage: TInputDirWizardPage;
  ProgramPage: TInputDirWizardPage;
  SelectedExe: String;
  ConfigText: AnsiString;

function IsAmiberry: Boolean;
begin
  if TargetPage = nil then
    Result := CompareText(ExpandConstant('{param:EMULATOR|Amiberry}'), 'WinUAE') <> 0
  else
    Result := TargetPage.SelectedValueIndex = 0;
end;

function IsWinUAE: Boolean;
begin
  Result := not IsAmiberry;
end;

function Emulator(Param: String): String;
begin
  if IsAmiberry then Result := 'Amiberry' else Result := 'WinUAE';
end;

function Payload(Param: String): String;
begin
  if SourcePage = nil then Result := ExpandConstant('{param:PAYLOAD|{src}}')
  else Result := SourcePage.Values[0];
  Result := RemoveBackslashUnlessRoot(Result);
end;

function DataRoot(Param: String): String;
begin
  if DataPage = nil then Result := ExpandConstant('{param:DATA|{userdocs}\AmigaVision}')
  else Result := DataPage.Values[0];
  Result := RemoveBackslashUnlessRoot(Result);
end;

function ExePath(Param: String): String;
begin
  Result := SelectedExe;
  if Result = '' then Result := ExpandConstant('{param:EMULATORFILE|}');
end;

function ExeRoot(Param: String): String;
begin
  Result := ExtractFileDir(ExePath(''));
end;

function LaunchArgs(Param: String): String;
begin
  if IsAmiberry then Result := '-f ' else Result := '-config=';
  Result := Result + '"' + DataRoot('') + '\Configurations\AmigaVision.uae"';
end;

// Keep the executable choice internal; users only choose a folder as a fallback.
procedure ConsiderFolder(Folder: String);
var
  Candidate: String;
begin
  Folder := RemoveQuotes(Trim(Folder));
  if Folder = '' then exit;
  Folder := AddBackslash(Folder);
  if IsAmiberry then Candidate := Folder + 'Amiberry.exe'
  else begin
    Candidate := Folder + 'winuae64.exe';
    if not FileExists(Candidate) then Candidate := Folder + 'winuae.exe';
  end;
  if not FileExists(Candidate) then exit;
  if (SelectedExe = '') or
     (IsWinUAE and (CompareText(ExtractFileName(Candidate), 'winuae64.exe') = 0) and
      (CompareText(ExtractFileName(SelectedExe), 'winuae64.exe') <> 0)) then
    SelectedExe := Candidate;
end;

procedure ScanNamedFolders(Root: String);
var
  Find: TFindRec;
begin
  ConsiderFolder(Root);
  ConsiderFolder(AddBackslash(Root) + Emulator(''));
  // One level only: catches versioned portable folders without crawling a drive.
  if FindFirst(AddBackslash(Root) + '*', Find) then begin
    try
      repeat
        if ((Find.Attributes and FILE_ATTRIBUTE_DIRECTORY) <> 0) and
           (Pos(Lowercase(Emulator('')), Lowercase(Find.Name)) > 0) then
          ConsiderFolder(AddBackslash(Root) + Find.Name);
      until not FindNext(Find);
    finally
      FindClose(Find);
    end;
  end;
end;

procedure ScanRegistry(RootKey: Integer);
var
  Keys: TArrayOfString;
  I, Comma: Integer;
  Key, Name, Value: String;
begin
  Key := 'Software\Microsoft\Windows\CurrentVersion\App Paths\';
  if IsAmiberry then Name := 'Amiberry.exe' else Name := 'winuae64.exe';
  if RegQueryStringValue(RootKey, Key + Name, '', Value) then
    ConsiderFolder(ExtractFileDir(RemoveQuotes(Value)));
  if IsWinUAE and RegQueryStringValue(RootKey, Key + 'winuae.exe', '', Value) then
    ConsiderFolder(ExtractFileDir(RemoveQuotes(Value)));
  Key := 'Software\Microsoft\Windows\CurrentVersion\Uninstall';
  if RegGetSubkeyNames(RootKey, Key, Keys) then
    for I := 0 to GetArrayLength(Keys) - 1 do begin
      if RegQueryStringValue(RootKey, Key + '\' + Keys[I], 'DisplayName', Name) and
         (Pos(Lowercase(Emulator('')), Lowercase(Name)) = 1) then begin
        if RegQueryStringValue(RootKey, Key + '\' + Keys[I], 'InstallLocation', Value) then
          ConsiderFolder(Value);
        if RegQueryStringValue(RootKey, Key + '\' + Keys[I], 'DisplayIcon', Value) then begin
          Comma := Pos(',', Value);
          if Comma > 0 then Value := Copy(Value, 1, Comma - 1);
          ConsiderFolder(ExtractFileDir(RemoveQuotes(Value)));
        end;
      end;
    end;
end;

procedure DetectEmulator;
var
  Paths, Folder: String;
  Split: Integer;
begin
  SelectedExe := '';
  // Retain the command-line override for unattended installations and tests.
  SelectedExe := ExpandConstant('{param:EMULATORFILE|}');
  if SelectedExe <> '' then exit;
  ScanRegistry(HKCU32);
  if IsWin64 then ScanRegistry(HKCU64);
  ScanRegistry(HKLM32);
  if IsWin64 then ScanRegistry(HKLM64);
  ScanNamedFolders(ExpandConstant('{localappdata}\Programs'));
  ScanNamedFolders(ExpandConstant('{localappdata}'));
  ScanNamedFolders(ExpandConstant('{pf32}'));
  if IsWin64 then ScanNamedFolders(ExpandConstant('{pf64}'));
  Paths := GetEnv('PATH');
  while Paths <> '' do begin
    Split := Pos(';', Paths);
    if Split = 0 then Split := Length(Paths) + 1;
    Folder := Copy(Paths, 1, Split - 1);
    Delete(Paths, 1, Split);
    ConsiderFolder(Folder);
  end;
  ScanNamedFolders(ExpandConstant('{src}'));
  ScanNamedFolders(ExtractFileDir(Payload('')));
  ScanNamedFolders(Payload(''));
  ScanNamedFolders(ExpandConstant('{userdesktop}'));
  ScanNamedFolders(ExpandConstant('{userdocs}'));
  ScanNamedFolders(ExpandConstant('{userprofile}\Downloads'));
  ScanNamedFolders(ExpandConstant('{userprofile}'));
  if SelectedExe <> '' then Log('Detected ' + Emulator('') + ': ' + SelectedExe)
  else Log('No ' + Emulator('') + ' installation found.');
end;

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := False;
  if ProgramPage = nil then exit;
  if PageID = ProgramPage.ID then begin
    DetectEmulator;
    Result := SelectedExe <> '';
    if not Result then begin
      ProgramPage.Caption := Emulator('') + ' was not found';
      ProgramPage.Description := 'Install ' + Emulator('') + ' before continuing, or select its installation folder below.';
      ProgramPage.Values[0] := '';
    end;
  end;
end;

procedure InitializeWizard;
begin
  Log('Creating AmigaVision setup pages');
  TargetPage := CreateInputOptionPage(wpWelcome, 'Choose your emulator',
    'Which emulator should AmigaVision use?',
    'Install the emulator first. Close it before continuing. Copperline support will follow separately.', True, False);
  TargetPage.Add('Amiberry');
  TargetPage.Add('WinUAE');
  Log('Created emulator choice');
  TargetPage.SelectedValueIndex := 0;
  if CompareText(ExpandConstant('{param:EMULATOR|Amiberry}'), 'WinUAE') = 0 then
    TargetPage.SelectedValueIndex := 1;
  SourcePage := CreateInputDirPage(TargetPage.ID, 'Locate your AmigaVision release',
    'Select the extracted emulator package.',
    'Choose the folder containing Amiberry, WinUAE and HardDrives. Extract the complete archive before continuing.', False, '');
  SourcePage.Add('Release folder:');
  Log('Created release folder page');
  SourcePage.Values[0] := ExpandConstant('{param:PAYLOAD|{src}}');
  ProgramPage := CreateInputDirPage(SourcePage.ID, 'Emulator not found',
    'Install the selected emulator before continuing, or select its installation folder.',
    'Setup checked installed applications and common system, per-user and portable locations. If you have already installed the emulator elsewhere, choose its folder. Setup will select the correct program automatically.', False, '');
  ProgramPage.Add('Emulator installation folder:');
  DataPage := CreateInputDirPage(ProgramPage.ID, 'Choose the AmigaVision data folder',
    'Where should AmigaVision be installed?',
    'Existing saves and Shared files are kept. The main disk image is replaced on upgrade. Back up custom changes inside that image first.', False, '');
  DataPage.Add('Data folder:');
  DataPage.Values[0] := ExpandConstant('{param:DATA|}');
  Log('AmigaVision setup pages ready');
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  if DataPage = nil then exit;
  if (CurPageID = DataPage.ID) and (DataPage.Values[0] = '') then begin
    if IsWinUAE then
      DataPage.Values[0] := ExpandConstant('{commondocs}\Amiga Files\WinUAE')
    else
      DataPage.Values[0] := ExeRoot('');
  end;
end;

function ValidateInputs: String;
var
  Root, Name, Text: String;
  Loaded: AnsiString;
begin
  Result := '';
  Root := Payload('');
  if not FileExists(Root + '\HardDrives\AmigaVision.hdf') or
     not FileExists(Root + '\HardDrives\AmigaVision-Saves.hdf') or
     not DirExists(Root + '\HardDrives\Shared') or
     not DirExists(Root + '\HardDrives\listings') or
     not FileExists(Root + '\' + Emulator('') + '\ROMs\AmigaVision.rom') then begin
    Result := 'Select a complete, extracted AmigaVision emulator release.';
    exit;
  end;
  if IsAmiberry then Name := 'Amiberry\Visuals\Shaders'
    else Name := 'WinUAE\plugins\filtershaders\direct3d';
  if not DirExists(Root + '\' + Name) then begin
    Result := 'The release is missing its shader folder.';
    exit;
  end;
  if not LoadStringFromFile(Root + '\' + Emulator('') + '\Configurations\AmigaVision.uae', Loaded) then begin
    Result := 'The release is missing Configurations\AmigaVision.uae.';
    exit;
  end;
  Name := Lowercase(ExtractFileName(ExePath('')));
  if not FileExists(ExePath('')) or
     (IsAmiberry and (Name <> 'amiberry.exe')) or
     (IsWinUAE and (Name <> 'winuae.exe') and (Name <> 'winuae64.exe')) then begin
    Result := Emulator('') + ' was not found. Install it first, or choose its installation folder.';
    exit;
  end;
  if (DataRoot('') = '') or
     ((Copy(DataRoot(''), 1, 2) <> '\\') and
      ((Length(DataRoot('')) < 3) or (Copy(DataRoot(''), 2, 2) <> ':\'))) then begin
    Result := 'Choose an absolute data folder path.';
    exit;
  end;
  // Reject overlapping release and destination trees: external file copying must not copy onto itself.
  Text := Lowercase(AddBackslash(ExpandFileName(DataRoot(''))));
  Root := Lowercase(AddBackslash(ExpandFileName(Payload(''))));
  if (Pos(Root, Text) = 1) or (Pos(Text, Root) = 1) then begin
    Result := 'Choose a data folder outside the extracted release folder.';
    exit;
  end;
  Text := UTF8Decode(Loaded);
  StringChangeEx(Text, './HardDrives/', AddBackslash(DataRoot('')) + 'HardDrives\', True);
  StringChangeEx(Text, './ROMs/', AddBackslash(DataRoot('')) + 'ROMs\', True);
  StringChangeEx(Text, 'shaders_path=Visuals/Shaders', 'shaders_path=' + AddBackslash(DataRoot('')) + 'Visuals\Shaders', True);
  StringChangeEx(Text, '.\HardDrives\', AddBackslash(DataRoot('')) + 'HardDrives\', True);
  StringChangeEx(Text, '.\ROMs\', AddBackslash(DataRoot('')) + 'ROMs\', True);
  ConfigText := UTF8Encode(Text);
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  Error: String;
begin
  Result := True;
  if DataPage = nil then exit;
  if CurPageID = TargetPage.ID then SelectedExe := '';
  if CurPageID = ProgramPage.ID then begin
    SelectedExe := '';
    ConsiderFolder(ProgramPage.Values[0]);
    if SelectedExe = '' then begin
      Log('The selected folder does not contain ' + Emulator(''));
      if not WizardSilent then MsgBox('This folder does not contain ' + Emulator('') + '. Install it first, or choose its installation folder.', mbError, MB_OK);
      Result := False;
      exit;
    end;
  end;
  if CurPageID = DataPage.ID then begin
    Error := ValidateInputs;
    if Error <> '' then begin
      Log(Error);
      if not WizardSilent then MsgBox(Error, mbError, MB_OK);
      Result := False;
    end;
  end;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  if SelectedExe = '' then DetectEmulator;
  Result := ValidateInputs;
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

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then begin
    if not ForceDirectories(DataRoot('') + '\Configurations') then
      RaiseException('Could not create the configuration folder.');
    WriteConfig(DataRoot('') + '\Configurations\AmigaVision.uae');
    if WizardIsTaskSelected('defaultconfig') then
      WriteConfig(DataRoot('') + '\Configurations\default.uae');
  end;
end;
