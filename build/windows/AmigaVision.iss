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
PrivilegesRequiredOverridesAllowed=commandline
DisableDirPage=yes
DisableProgramGroupPage=yes
UsePreviousTasks=no
WizardStyle=modern dynamic
WizardSizePercent=120,150
SetupIconFile=assets\AmigaVision.ico
WizardImageFile=
WizardSmallImageFile=assets\AV-avatar.png
DisableWelcomePage=no
DisableFinishedPage=no
OutputDir=output
OutputBaseFilename=Install on Windows
Compression=lzma2

[Messages]
WelcomeLabel2=AmigaVision is the ultimate Amiga games & demo scene collection for%nMiSTer & Pocket FPGAs, Raspberry Pi + Windows/Mac/Linux — and%nAmiga 1200, 4000 & CD32.%n%nLet’s get AmigaVision installed on your Windows computer!
ClickNext=
FinishedHeadingLabel=AmigaVision Install Completed
FinishedLabel=
FinishedLabelNoIcons=
ClickFinish=
WizardSelectTasks=Startup Options
SelectTasksDesc=Choose how to launch AmigaVision.
SelectTasksLabel2=
ErrorCreatingDir=Setup was unable to create the directory “%1”
ErrorTooManyFilesInDir=Unable to create a file in the directory “%1” because it contains too many files
SelectStartMenuFolderDesc=Where should Setup place the program’s shortcuts?
SelectStartMenuFolderLabel3=Setup will create the program’s shortcuts in the following Start Menu folder.
NoProgramGroupCheck2=&Don’t create a Start Menu folder
FileNotInDir2=The file “%1” could not be located in “%2”. Please insert the correct disk or select another folder.
ErrorIniEntry=Error creating INI entry in file “%1”.
SourceDoesntExist=The source file “%1” does not exist
VerificationSignatureDoesntExist=The signature file “%1” does not exist
VerificationSignatureInvalid=The signature file “%1” is invalid
VerificationKeyNotFound=The signature file “%1” uses an unknown key
UninstallNotFound=File “%1” does not exist. Cannot uninstall.
UninstallOpenError=File “%1” could not be opened. Cannot uninstall
UninstallUnsupportedVer=The uninstall log file “%1” is in a format not recognized by this version of the uninstaller. Cannot uninstall
UninstallDataCorrupted=“%1” file is corrupted. Cannot uninstall

[Tasks]
Name: defaultconfig; Description: "Set AmigaVision as the default configuraton"
Name: desktopicon; Description: "Create a desktop shortcut"

[Files]
Source: "assets\banner.bmp"; Flags: dontcopy
Source: "assets\amiberry.bmp"; Flags: dontcopy
Source: "assets\copperline.bmp"; Flags: dontcopy
Source: "assets\winuae.bmp"; Flags: dontcopy
Source: "assets\amiberry-dark.png"; Flags: dontcopy
Source: "assets\copperline-dark.png"; Flags: dontcopy
Source: "assets\winuae-dark.png"; Flags: dontcopy
Source: "output\WinUAEShaderSetup.exe"; Flags: dontcopy
Source: "assets\AmigaVision.ico"; DestDir: "{code:DataRoot}"; Flags: ignoreversion
Source: "{code:Payload}\Amiberry\HardDrives\AmigaVision.hdf"; DestDir: "{code:DataRoot}\HardDrives"; Flags: external ignoreversion
Source: "{code:Payload}\Amiberry\HardDrives\AmigaVision-Saves.hdf"; DestDir: "{code:DataRoot}\HardDrives"; Flags: external onlyifdoesntexist
Source: "{code:Payload}\Amiberry\HardDrives\Shared\*"; DestDir: "{code:DataRoot}\HardDrives\Shared"; Flags: external recursesubdirs createallsubdirs onlyifdoesntexist
Source: "{code:Payload}\Amiberry\HardDrives\listings\*"; DestDir: "{code:DataRoot}\HardDrives\listings"; Flags: external recursesubdirs createallsubdirs ignoreversion
Source: "{code:Payload}\Amiberry\ROMs\AmigaVision.rom"; DestDir: "{code:DataRoot}\ROMs"; Flags: external ignoreversion
Source: "{code:Payload}\Amiberry\Visuals\*"; DestDir: "{code:DataRoot}\Visuals"; Flags: external recursesubdirs createallsubdirs ignoreversion; Check: IsAmiberry
Source: "{code:Payload}\WinUAE\plugins\filtershaders\direct3d\CRT-Pi-SmartRes.fx"; DestDir: "{code:ExeRoot}\plugins\filtershaders\direct3d"; Flags: external ignoreversion overwritereadonly; Check: InstallShaderDirectly

[Run]
Filename: "{code:ExePath}"; Parameters: "{code:LaunchArgs}"; WorkingDir: "{code:DataRoot}"; Description: "Launch AmigaVision"; Flags: postinstall nowait skipifsilent runasoriginaluser

[Code]
var
  TargetPage: TWizardPage;
  EmulatorChoiceTop: Integer;
  EmulatorChoices: array[0..2] of TNewStaticText;
  EmulatorFrames: array[0..2] of TPanel;
  EmulatorCards: array[0..2] of TPanel;
  EmulatorSelectionLabels: array[0..2] of TNewStaticText;
  SelectedEmulatorIndex: Integer;
  EmulatorDataFolders: array[0..2] of String;
  DataPage: TInputDirWizardPage;
  ProgramPage: TInputDirWizardPage;
  DestinationNotice: TNewStaticText;
  EmulatorExitHint: TNewStaticText;
  SelectedExe: String;
  ConfigText: AnsiString;
  ShaderInstalledWithAdmin: Boolean;

function IsAmiberry: Boolean;
begin
  if EmulatorChoices[0] = nil then
    Result := CompareText(ExpandConstant('{param:EMULATOR|Amiberry}'), 'Amiberry') = 0
  else Result := SelectedEmulatorIndex = 0;
end;

function IsCopperline: Boolean;
begin
  if EmulatorChoices[1] = nil then
    Result := CompareText(ExpandConstant('{param:EMULATOR|Amiberry}'), 'Copperline') = 0
  else Result := SelectedEmulatorIndex = 1;
end;

function IsWinUAE: Boolean;
begin
  Result := not IsAmiberry and not IsCopperline;
end;

function Emulator(Param: String): String;
begin
  if IsAmiberry then Result := 'Amiberry'
  else if IsCopperline then Result := 'Copperline'
  else Result := 'WinUAE';
end;

function Payload(Param: String): String;
begin
  Result := ExpandConstant('{param:PAYLOAD|{src}}');
  Result := RemoveBackslashUnlessRoot(Result);
end;

function CopperlineHome: String;
var
  Folder: String;
begin
  Folder := ExtractFileDir(SelectedExe);
  if Folder = '' then Folder := ExtractFileDir(ExpandConstant('{param:EMULATORFILE|}'));
  if (Folder <> '') and FileExists(Folder + '\portable.txt') then Result := Folder
  else Result := GetEnv('USERPROFILE') + '\Documents\Copperline';
end;

function DataRoot(Param: String): String;
begin
  if IsCopperline then Result := CopperlineHome
  else if DataPage = nil then Result := ExpandConstant('{param:DATA|{userdocs}\AmigaVision}')
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

function DefaultDataFolder: String;
var
  ConfigFile, Value: String;
  Lines: TArrayOfString;
  I, Separator: Integer;
begin
  if IsCopperline then begin Result := CopperlineHome; exit; end;
  if IsWinUAE then begin
    Result := ExpandConstant('{commondocs}\Amiga Files\WinUAE');
    exit;
  end;
  // Amiberry's content root is distinct from both its executable and its
  // bootstrap amiberry.conf. Respect a configured base content folder.
  Value := Trim(GetEnv('AMIBERRY_HOME_DIR'));
  if Value <> '' then begin Result := RemoveQuotes(Value); exit; end;
  if FileExists(ExeRoot('') + '\amiberry.portable') then
    ConfigFile := ExeRoot('') + '\Settings\amiberry.conf'
  else ConfigFile := ExpandConstant('{localappdata}\Amiberry\amiberry.conf');
  if LoadStringsFromFile(ConfigFile, Lines) then
    for I := 0 to GetArrayLength(Lines) - 1 do begin
      Separator := Pos('=', Lines[I]);
      if (Separator > 0) and
         (CompareText(Trim(Copy(Lines[I], 1, Separator - 1)), 'base_content_path') = 0) then begin
        Value := RemoveQuotes(Trim(Copy(Lines[I], Separator + 1, Length(Lines[I]))));
        StringChangeEx(Value, '/', '\', True);
        if (Copy(Value, 1, 2) = '\\') or
           ((Length(Value) >= 3) and (Copy(Value, 2, 2) = ':\')) then begin
          Result := RemoveBackslashUnlessRoot(Value);
          exit;
        end;
      end;
    end;
  if FileExists(ExeRoot('') + '\amiberry.portable') then Result := ExeRoot('')
  else Result := GetEnv('USERPROFILE') + '\Amiberry';
end;

procedure FillDefaultDataFolder;
begin
  if (DataPage <> nil) and (DataPage.Values[0] = '') then begin
    DataPage.Values[0] := DefaultDataFolder;
    Log('Default ' + Emulator('') + ' data folder: ' + DataPage.Values[0]);
  end;
end;

function OpenPathForAccess(const Path: String; Access, ShareMode: LongWord;
  Security: LongWord; Creation, Attributes: LongWord; Template: THandle): THandle;
  external 'CreateFileW@kernel32.dll stdcall';
function CloseAccessHandle(Handle: THandle): Boolean;
  external 'CloseHandle@kernel32.dll stdcall';

function CanWriteWinUAEShader: Boolean;
var
  Folder, Parent, Shader: String;
  Handle: THandle;
begin
  Result := True;
  if not IsWinUAE or (ExeRoot('') = '') then exit;
  Folder := ExeRoot('') + '\plugins\filtershaders\direct3d';
  Shader := Folder + '\CRT-Pi-SmartRes.fx';
  if FileExists(Shader) then begin
    Handle := OpenPathForAccess(Shader, $40000000, 7, 0, 3, $80, 0);
    Result := Handle <> THandle(-1);
    if not Result then exit;
    CloseAccessHandle(Handle);
  end;
  // A missing plugin directory will inherit access from its nearest existing parent.
  while not DirExists(Folder) do begin
    Parent := ExtractFileDir(Folder);
    if (Parent = '') or (Parent = Folder) then begin Result := False; exit; end;
    Folder := Parent;
  end;
  Handle := OpenPathForAccess(Folder, $00000006, 7, 0, 3, $02000000, 0);
  Result := Handle <> THandle(-1);
  if Result then CloseAccessHandle(Handle);
end;

function InstallShaderDirectly: Boolean;
begin
  Result := IsWinUAE and not ShaderInstalledWithAdmin;
end;

function LaunchArgs(Param: String): String;
begin
  if IsCopperline then begin
    Result := '--config "' + DataRoot('') + '\configs\AmigaVision.toml"';
    exit;
  end;
  if IsAmiberry then
    Result := '-o "shaders_path=' + DataRoot('') + '\Visuals\Shaders" -f '
  else Result := '-config=';
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
  else if IsCopperline then Candidate := Folder + 'copperline.exe'
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
  if IsAmiberry then Name := 'Amiberry.exe'
  else if IsCopperline then Name := 'copperline.exe'
  else Name := 'winuae64.exe';
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
  Folder := GetEnv('USERPROFILE');
  if Folder <> '' then begin
    ScanNamedFolders(AddBackslash(Folder) + 'Downloads');
    ScanNamedFolders(Folder);
  end;
  if SelectedExe <> '' then Log('Detected ' + Emulator('') + ': ' + SelectedExe)
  else Log('No ' + Emulator('') + ' installation found.');
end;

function InitializeSetup: Boolean;
var
  Root: String;
begin
  Root := Payload('');
  Result := DirExists(Root + '\Amiberry') and DirExists(Root + '\WinUAE') and
    FileExists(Root + '\Amiberry\HardDrives\AmigaVision.hdf') and
    FileExists(Root + '\Amiberry\HardDrives\AmigaVision-Saves.hdf');
  if not Result then
    SuppressibleMsgBox('Run this installer from inside the extracted AmigaVision-Emulators folder, with the Amiberry and WinUAE folders beside it. Extract the complete package before starting setup.', mbError, MB_OK, IDOK);
end;

function ValidateDestination: String;
begin
  Result := '';
  if (DataRoot('') = '') or
     ((Copy(DataRoot(''), 1, 2) <> '\\') and
      ((Length(DataRoot('')) < 3) or (Copy(DataRoot(''), 2, 2) <> ':\'))) then
    Result := 'Choose an absolute data folder path.';
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

procedure DownloadEmulator(Sender: TObject; const Link: String; LinkType: TSysLinkType);
var
  ErrorCode: Integer;
begin
  if LinkType <> sltURL then exit;
  if not ShellExecAsOriginalUser('open', Link, '', '', SW_SHOWNORMAL, ewNoWait, ErrorCode) then
    MsgBox('Could not open the download page. Please visit ' + Link, mbError, MB_OK);
end;

procedure SelectEmulator(Index: Integer);
var
  I: Integer;
begin
  if SelectedEmulatorIndex <> Index then begin
    if DataPage <> nil then
      EmulatorDataFolders[SelectedEmulatorIndex] := DataPage.Values[0];
    SelectedExe := '';
    SelectedEmulatorIndex := Index;
    if DataPage <> nil then DataPage.Values[0] := EmulatorDataFolders[Index];
  end;
  for I := 0 to 2 do begin
    if EmulatorFrames[I] <> nil then begin
      if I = Index then begin
        if HighContrastActive then EmulatorFrames[I].Color := clHighlight
        else EmulatorFrames[I].Color := $DD8051;
        EmulatorSelectionLabels[I].Caption := 'Selected';
      end else begin
        if HighContrastActive then EmulatorFrames[I].Color := clWindowText
        else if IsDarkInstallMode then EmulatorFrames[I].Color := $555555
        else EmulatorFrames[I].Color := $D8D8D8;
        EmulatorSelectionLabels[I].Caption := '';
      end;
    end;
  end;
end;

procedure EmulatorRowClick(Sender: TObject);
var
  Index: Integer;
begin
  Index := TComponent(Sender).Tag;
  SelectEmulator(Index);
  WizardForm.ActiveControl := EmulatorFrames[Index];
end;

function FocusedEmulatorRow: Integer;
var
  I: Integer;
begin
  Result := -1;
  for I := 0 to 2 do
    if WizardForm.ActiveControl = EmulatorFrames[I] then begin
      Result := I;
      exit;
    end;
end;

procedure EmulatorSelectionKeyDown(Sender: TObject; var Key: Word; Shift: TShiftState);
var
  Index: Integer;
begin
  if (TargetPage = nil) or (WizardForm.CurPageID <> TargetPage.ID) then exit;
  Index := FocusedEmulatorRow;
  if (Key >= 49) and (Key <= 51) then Index := Key - 49
  else if Index >= 0 then begin
    case Key of
      37, 38: Index := (Index + 2) mod 3;
      39, 40: Index := (Index + 1) mod 3;
      36: Index := 0;
      35: Index := 2;
      32: ;
    else exit;
    end;
  end else exit;
  SelectEmulator(Index);
  WizardForm.ActiveControl := EmulatorFrames[Index];
  Key := 0;
end;

procedure EmulatorSelectionKeyUp(Sender: TObject; var Key: Word; Shift: TShiftState);
var
  Index: Integer;
begin
  if (TargetPage = nil) or (WizardForm.CurPageID <> TargetPage.ID) then exit;
  // Selection follows keyboard focus, keeping the row outline visible on Tab.
  if Key = 9 then begin
    Index := FocusedEmulatorRow;
    if Index >= 0 then SelectEmulator(Index);
  end;
end;

procedure AddEmulatorChoice(Index: Integer; Caption: String; Available: Boolean);
var
  Link: TNewLinkLabel;
  Icon: TBitmapImage;
  Details, Separator: TNewStaticText;
  TextMeasure: TBitmap;
  NameWidth, SeparatorWidth, RowHeight: Integer;
  URL, Description, IconFile: String;
begin
  case Index of
    0: begin
      URL := 'https://github.com/BlitterStudio/amiberry/releases';
      Description := 'The recommended setup. Great integer scaling and autocrop make the most of your Amiga experience without stretched or uneven pixels. Handles NTSC scaling correctly, too. Runs the latest WinUAE code on the back-end, but has better screen rendering.';
    end;
    1: begin
      URL := 'https://copperline.dev/';
      Description := 'The “new kid on the block” — a recent emulator with best-in-class developer tools and great scaling. Choose this if you do Amiga development work.';
    end;
    2: begin
      URL := 'https://www.winuae.net/download/';
      Description := 'The “standard” Amiga emulator for Windows. More complex to configure, with scaling issues between PAL and NTSC. Choose this only if you need it and are already familiar with it. AmigaVision running under WinUAE has uneven pixels and other scaling issues that may bother you, this is an emulator limitation.';
    end;
  end;
  EmulatorFrames[Index] := TPanel.Create(WizardForm);
  with EmulatorFrames[Index] do begin
    Parent := TargetPage.Surface;
    StyleElements := [];
    ParentBackground := False;
    BevelOuter := bvNone;
    Caption := '';
    Tag := Index;
    TabOrder := Index;
    TabStop := True;
    OnClick := @EmulatorRowClick;
    SetBounds(0, EmulatorChoiceTop, TargetPage.SurfaceWidth, ScaleY(100));
  end;
  EmulatorFrames[Index].Caption := Caption;
  EmulatorCards[Index] := TPanel.Create(WizardForm);
  with EmulatorCards[Index] do begin
    Parent := EmulatorFrames[Index];
    StyleElements := [];
    ParentBackground := False;
    BevelOuter := bvNone;
    Caption := '';
    if HighContrastActive then Color := clWindow
    else if IsDarkInstallMode then Color := $202020 else Color := clWhite;
    Tag := Index;
    OnClick := @EmulatorRowClick;
    SetBounds(ScaleX(2), ScaleY(2), EmulatorFrames[Index].Width - ScaleX(4), ScaleY(96));
  end;
  if IsDarkInstallMode then IconFile := Lowercase(Caption) + '-dark.png'
  else IconFile := Lowercase(Caption) + '.bmp';
  ExtractTemporaryFile(IconFile);
  Icon := TBitmapImage.Create(WizardForm);
  Icon.Parent := EmulatorCards[Index];
  Icon.Tag := Index;
  Icon.OnClick := @EmulatorRowClick;
  if IsDarkInstallMode then begin
    Icon.BackColor := clNone;
    Icon.PngImage.LoadFromFile(ExpandConstant('{tmp}\') + IconFile);
  end else Icon.Bitmap.LoadFromFile(ExpandConstant('{tmp}\') + IconFile);
  Icon.Stretch := True;
  Icon.SetBounds(ScaleX(8), ScaleY(8), ScaleX(48), ScaleY(48));
  TextMeasure := TBitmap.Create;
  TextMeasure.Canvas.Font.Name := WizardForm.Font.Name;
  TextMeasure.Canvas.Font.Size := WizardForm.Font.Size;
  TextMeasure.Canvas.Font.Style := [fsBold];
  NameWidth := TextMeasure.Canvas.TextWidth(Caption);
  TextMeasure.Canvas.Font.Style := [];
  SeparatorWidth := TextMeasure.Canvas.TextWidth(' — ');
  TextMeasure.Free;
  EmulatorChoices[Index] := TNewStaticText.Create(WizardForm);
  with EmulatorChoices[Index] do begin
    Parent := EmulatorCards[Index];
    AutoSize := False;
    SetBounds(ScaleX(68), ScaleY(10), NameWidth, ScaleY(20));
    Font.Style := [fsBold];
    Enabled := Available;
    TabStop := False;
    Tag := Index;
    OnClick := @EmulatorRowClick;
  end;
  EmulatorChoices[Index].Caption := Caption;
  Separator := TNewStaticText.Create(WizardForm);
  Separator.Parent := EmulatorCards[Index];
  Separator.Tag := Index;
  Separator.OnClick := @EmulatorRowClick;
  Separator.AutoSize := False;
  Separator.Font.Color := clWindowText;
  Separator.SetBounds(EmulatorChoices[Index].Left + EmulatorChoices[Index].Width, ScaleY(10),
    SeparatorWidth, ScaleY(20));
  Separator.Caption := ' — ';
  Link := TNewLinkLabel.Create(WizardForm);
  Link.Parent := EmulatorCards[Index];
  Link.SetBounds(Separator.Left + Separator.Width,
    ScaleY(10), ScaleX(120), ScaleY(20));
  Link.Caption := '<a href="' + URL + '">Download</a>';
  Link.UseVisualStyle := True;
  Link.TabStop := True;
  Link.TabOrder := 1;
  Link.Tag := Index;
  Link.OnLinkClick := @DownloadEmulator;
  Details := TNewStaticText.Create(WizardForm);
  Details.Parent := EmulatorCards[Index];
  Details.Tag := Index;
  Details.OnClick := @EmulatorRowClick;
  Details.AutoSize := False;
  Details.WordWrap := True;
  Details.SetBounds(ScaleX(68), ScaleY(34),
    EmulatorCards[Index].Width - ScaleX(80), ScaleY(20));
  Details.Caption := Description;
  Details.AdjustHeight;
  RowHeight := Details.Top + Details.Height + ScaleY(8);
  if RowHeight < ScaleY(64) then RowHeight := ScaleY(64);
  EmulatorCards[Index].Height := RowHeight;
  EmulatorFrames[Index].Height := RowHeight + ScaleY(4);
  Icon.Top := (RowHeight - Icon.Height) div 2;
  EmulatorSelectionLabels[Index] := TNewStaticText.Create(WizardForm);
  with EmulatorSelectionLabels[Index] do begin
    Parent := EmulatorCards[Index];
    AutoSize := False;
    Alignment := taRightJustify;
    Font.Style := [fsBold];
    Tag := Index;
    OnClick := @EmulatorRowClick;
    SetBounds(EmulatorCards[Index].Width - ScaleX(86), ScaleY(10), ScaleX(74), ScaleY(20));
  end;
  EmulatorChoiceTop := EmulatorFrames[Index].Top + EmulatorFrames[Index].Height + ScaleY(6);
end;


procedure UpdateDestinationNotice(Sender: TObject);
var
  Root, Notice: String;
begin
  if DestinationNotice = nil then exit;
  Root := Trim(DataRoot(''));
  Notice := '';
  if Root <> '' then begin
    if FileExists(Root + '\HardDrives\AmigaVision.hdf') then
      Notice := 'An existing AmigaVision installation was found here. The main disk image will be replaced.' + #13#10#13#10 +
        'If you have made any changes to the main System drive or the Data drive, back those up first.';
    if FileExists(Root + '\HardDrives\AmigaVision-Saves.hdf') or
       DirExists(Root + '\HardDrives\Shared') then begin
      if Notice <> '' then Notice := Notice + #13#10#13#10;
      Notice := Notice + 'Existing saves and Shared files will be kept.';
    end;
  end;
  if IsWinUAE and not CanWriteWinUAEShader then begin
    if Notice <> '' then Notice := Notice + #13#10#13#10;
    Notice := Notice + 'WinUAE is installed in a folder that requires administrator access. Windows will ask for permission to install the AmigaVision shader.';
  end;
  DestinationNotice.Caption := Notice;
  DestinationNotice.AdjustHeight;
end;

function BrandBannerHeight: Integer;
begin
  // The logo is unchanged; half the original top/bottom padding was cropped.
  Result := WizardForm.WelcomePage.ClientWidth * 212 div 1491;
end;

function AddBrandBanner(Page: TWinControl): Integer;
var
  Banner: TBitmapImage;
begin
  Banner := TBitmapImage.Create(WizardForm);
  Banner.Parent := Page;
  Banner.Bitmap.LoadFromFile(ExpandConstant('{tmp}\banner.bmp'));
  Banner.Stretch := True;
  Banner.SetBounds(0, 0, Page.ClientWidth, BrandBannerHeight);
  Result := Banner.Height + ScaleY(10);
end;

procedure BrandWelcomeAndFinish;
var
  TextTop, Margin, TextWidth: Integer;
begin
  ExtractTemporaryFile('banner.bmp');
  Margin := ScaleX(24);
  WizardForm.WizardBitmapImage.Visible := False;
  WizardForm.WizardBitmapImage2.Visible := False;
  TextTop := AddBrandBanner(WizardForm.WelcomePage);
  TextWidth := WizardForm.WelcomePage.ClientWidth - 2 * Margin;
  with WizardForm.WelcomeLabel1 do begin
    Left := Margin;
    Top := TextTop;
    Width := TextWidth;
    AutoSize := False;
    WordWrap := True;
    AdjustHeight;
  end;
  with WizardForm.WelcomeLabel2 do begin
    Left := Margin;
    Top := WizardForm.WelcomeLabel1.Top + WizardForm.WelcomeLabel1.Height + ScaleY(8);
    Width := TextWidth;
    Height := WizardForm.WelcomePage.ClientHeight - Top - ScaleY(16);
  end;
  TextTop := AddBrandBanner(WizardForm.FinishedPage);
  TextWidth := WizardForm.FinishedPage.ClientWidth - 2 * Margin;
  with WizardForm.FinishedHeadingLabel do begin
    Left := Margin;
    Top := TextTop;
    Width := TextWidth;
    AutoSize := False;
    WordWrap := True;
    AdjustHeight;
  end;
  WizardForm.FinishedLabel.Visible := False;
end;

procedure BrandIntermediatePages;
var
  Banner: TBitmapImage;
  BannerHeight, ExtraHeight: Integer;
begin
  // MainPanel is shared by all intermediate built-in and custom pages.
  // Reserve header space without resizing the live wizard: Inno Setup
  // also adjusts its layout when the form dimensions change.
  BannerHeight := BrandBannerHeight;
  ExtraHeight := BannerHeight + ScaleY(16);
  WizardForm.MainPanel.Height := WizardForm.MainPanel.Height + ExtraHeight;
  WizardForm.Bevel1.Top := WizardForm.Bevel1.Top + ExtraHeight;
  WizardForm.InnerNotebook.Top := WizardForm.InnerNotebook.Top + ExtraHeight;
  WizardForm.InnerNotebook.Height := WizardForm.InnerNotebook.Height - ExtraHeight;
  WizardForm.WizardSmallBitmapImage.Visible := False;
  WizardForm.PageNameLabel.Top := WizardForm.PageNameLabel.Top + BannerHeight;
  WizardForm.PageNameLabel.Width := WizardForm.MainPanel.ClientWidth -
    WizardForm.PageNameLabel.Left - ScaleX(24);
  WizardForm.PageDescriptionLabel.Top := WizardForm.PageDescriptionLabel.Top + BannerHeight;
  WizardForm.PageDescriptionLabel.Width := WizardForm.MainPanel.ClientWidth -
    WizardForm.PageDescriptionLabel.Left - ScaleX(24);
  WizardForm.PageDescriptionLabel.Height := WizardForm.PageDescriptionLabel.Height + ScaleY(16);
  Banner := TBitmapImage.Create(WizardForm);
  Banner.Parent := WizardForm.MainPanel;
  Banner.Bitmap.LoadFromFile(ExpandConstant('{tmp}\banner.bmp'));
  Banner.Stretch := True;
  Banner.SetBounds(0, 0, WizardForm.MainPanel.ClientWidth, BannerHeight);
end;

procedure LayoutCompletionOptions;
var
  Top: Integer;
begin
  WizardForm.FinishedLabel.Visible := False;
  Top := WizardForm.FinishedHeadingLabel.Top + WizardForm.FinishedHeadingLabel.Height + ScaleY(16);
  WizardForm.RunList.SetBounds(ScaleX(24), Top,
    WizardForm.FinishedPage.ClientWidth - ScaleX(48),
    ScaleY(28));
  if EmulatorExitHint = nil then begin
    EmulatorExitHint := TNewStaticText.Create(WizardForm);
    EmulatorExitHint.Parent := WizardForm.FinishedPage;
    EmulatorExitHint.AutoSize := False;
    EmulatorExitHint.WordWrap := True;
  end;
  if IsCopperline then EmulatorExitHint.Caption := 'Press Alt+Q to exit the emulator.'
  else EmulatorExitHint.Caption := 'Press F12 to exit the emulator.';
  EmulatorExitHint.SetBounds(ScaleX(24), Top + ScaleY(40),
    WizardForm.FinishedPage.ClientWidth - ScaleX(48), ScaleY(32));
  EmulatorExitHint.AdjustHeight;
end;

procedure InitializeWizard;
begin
  ExtractTemporaryFile('banner.bmp');
  BrandIntermediatePages;
  WizardForm.KeyPreview := True;
  WizardForm.OnKeyDown := @EmulatorSelectionKeyDown;
  WizardForm.OnKeyUp := @EmulatorSelectionKeyUp;
  Log('Creating AmigaVision setup pages');
  TargetPage := CreateCustomPage(wpWelcome, 'Choose your emulator',
    'Select which emulator to use. Use its download link if you need to install it first, and then come back here to complete the process.');
  AddEmulatorChoice(0, 'Amiberry', True);
  AddEmulatorChoice(1, 'Copperline', True);
  AddEmulatorChoice(2, 'WinUAE', True);
  Log(Format('Emulator selection layout: rows=%d, available=%d', [EmulatorChoiceTop, TargetPage.SurfaceHeight]));
  SelectEmulator(0);
  if CompareText(ExpandConstant('{param:EMULATOR|Amiberry}'), 'Copperline') = 0 then
    SelectEmulator(1);
  if CompareText(ExpandConstant('{param:EMULATOR|Amiberry}'), 'WinUAE') = 0 then
    SelectEmulator(2);
  ProgramPage := CreateInputDirPage(TargetPage.ID, 'Emulator not found',
    'Install the selected emulator before continuing, or select its installation folder.',
    'Setup checked installed applications and common system, per-user and portable locations. If you have already installed the emulator elsewhere, choose its folder. Setup will select the correct program automatically.', False, '');
  ProgramPage.Add('Emulator installation folder:');
  DataPage := CreateInputDirPage(ProgramPage.ID, 'Choose the AmigaVision data folder',
    'Where should AmigaVision be installed?',
    'Choose the folder where you want to install AmigaVision. Setup will check it for an existing installation.', False, '');
  DataPage.Add('Data folder:');
  DestinationNotice := TNewStaticText.Create(WizardForm);
  DestinationNotice.Parent := DataPage.Surface;
  DestinationNotice.Left := 0;
  DestinationNotice.Top := DataPage.Edits[0].Top + DataPage.Edits[0].Height + ScaleY(20);
  DestinationNotice.Width := DataPage.SurfaceWidth;
  DestinationNotice.AutoSize := False;
  DestinationNotice.WordWrap := True;
  DataPage.Edits[0].OnChange := @UpdateDestinationNotice;
  DataPage.Values[0] := ExpandConstant('{param:DATA|}');
  UpdateDestinationNotice(nil);
  BrandWelcomeAndFinish;
  Log('AmigaVision setup pages ready');
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  if CurPageID = wpFinished then LayoutCompletionOptions;
  if DataPage = nil then exit;
  if CurPageID = DataPage.ID then begin
    DataPage.Edits[0].ReadOnly := IsCopperline;
    DataPage.Buttons[0].Enabled := not IsCopperline;
    if IsCopperline then begin
      DataPage.Caption := 'AmigaVision data folder';
      DataPage.Description := 'Copperline uses this folder for its configurations, ROMs and disk images.';
      DataPage.SubCaptionLabel.Caption := 'Setup uses Copperline’s standard data folder so the same configuration works without path changes. Existing saves and configuration files will be kept or backed up.';
      DataPage.Values[0] := CopperlineHome;
    end else begin
      DataPage.Caption := 'Choose the AmigaVision data folder';
      DataPage.Description := 'Where should AmigaVision be installed?';
      DataPage.SubCaptionLabel.Caption := 'Choose the folder where you want to install AmigaVision. Setup will check it for an existing installation.';
      FillDefaultDataFolder;
    end;
    UpdateDestinationNotice(nil);
  end;
end;

function ValidateInputs: String;
var
  Root, Name, Text: String;
  Loaded: AnsiString;
begin
  Result := '';
  Root := Payload('');
  if not FileExists(Root + '\Amiberry\HardDrives\AmigaVision.hdf') or
     not FileExists(Root + '\Amiberry\HardDrives\AmigaVision-Saves.hdf') or
     not DirExists(Root + '\Amiberry\HardDrives\Shared') or
     not DirExists(Root + '\Amiberry\HardDrives\listings') or
     not FileExists(Root + '\Amiberry\ROMs\AmigaVision.rom') then begin
    Result := 'The emulator package is incomplete. Extract the complete AmigaVision-Emulators package and run its installer from that folder.';
    exit;
  end;
  if IsAmiberry then Name := 'Amiberry\Visuals\Shaders'
    else Name := 'WinUAE\plugins\filtershaders\direct3d';
  if not IsCopperline and not DirExists(Root + '\' + Name) then begin
    Result := 'The release is missing its shader folder.';
    exit;
  end;
  if IsCopperline then Name := 'Copperline\configs\AmigaVision.toml'
  else Name := Emulator('') + '\Configurations\AmigaVision.uae';
  if not LoadStringFromFile(Root + '\' + Name, Loaded) then begin
    Result := 'The release is missing ' + Name + '.';
    exit;
  end;
  Name := Lowercase(ExtractFileName(ExePath('')));
  if not FileExists(ExePath('')) or
     (IsAmiberry and (Name <> 'amiberry.exe')) or
     (IsCopperline and (Name <> 'copperline.exe')) or
     (IsWinUAE and (Name <> 'winuae.exe') and (Name <> 'winuae64.exe')) then begin
    Result := Emulator('') + ' was not found. Install it first, or choose its installation folder.';
    exit;
  end;
  Result := ValidateDestination;
  if Result <> '' then exit;
  // Reject overlapping release and destination trees: external file copying must not copy onto itself.
  Text := Lowercase(AddBackslash(ExpandFileName(DataRoot(''))));
  Root := Lowercase(AddBackslash(ExpandFileName(Payload(''))));
  if (Pos(Root, Text) = 1) or (Pos(Text, Root) = 1) then begin
    Result := 'Choose a data folder outside the extracted release folder.';
    exit;
  end;
  Text := UTF8Decode(Loaded);
  if IsCopperline then begin
    // Use the exact shared TOML. Copperline resolves bare media filenames
    // from its own roms and harddrives directories, independent of launch cwd.
    ConfigText := Loaded;
    exit;
  end;
  StringChangeEx(Text, './HardDrives/', AddBackslash(DataRoot('')) + 'HardDrives\', True);
  StringChangeEx(Text, './ROMs/', AddBackslash(DataRoot('')) + 'ROMs\', True);
  if IsAmiberry then begin
    StringChangeEx(Text, #10 + 'shader=', #10 + 'amiberry.shader=', True);
    StringChangeEx(Text, #10 + 'gfx_lores=true', #10 + 'gfx_lores=false', True);
    StringChangeEx(Text, #10 + 'gfx_resolution=lores', #10 + 'gfx_resolution=hires', True);
    StringChangeEx(Text, #10 + 'gfx_linemode=none', #10 + 'gfx_linemode=double', True);
    StringChangeEx(Text, 'shaders_path=Visuals/Shaders', '; Shader directory is set by the AmigaVision launcher.', True);
  end;
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
  Error := '';
  if CurPageID = DataPage.ID then Error := ValidateDestination;
  if Error <> '' then begin
    Log(Error);
    if not WizardSilent then MsgBox(Error, mbError, MB_OK);
    Result := False;
  end;
end;

function InstallProtectedShader: String;
var
  Parameters, Source, Destination: String;
  ExitCode: Integer;
begin
  Result := '';
  if not IsWinUAE or ShaderInstalledWithAdmin or CanWriteWinUAEShader then exit;
  if WizardSilent then begin
    Result := 'WinUAE is installed in a folder that requires administrator access. Run setup as administrator to install its AmigaVision shader.';
    exit;
  end;
  ExtractTemporaryFile('WinUAEShaderSetup.exe');
  Source := Payload('') + '\WinUAE\plugins\filtershaders\direct3d\CRT-Pi-SmartRes.fx';
  Destination := ExeRoot('') + '\plugins\filtershaders\direct3d\CRT-Pi-SmartRes.fx';
  Parameters := '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART ' +
    '/SHADERSOURCE="' + Source + '" /WINUAEDIR="' + ExeRoot('') + '" ' +
    '/LOG="' + ExpandConstant('{tmp}\WinUAE-shader.log') + '"';
  Log('Requesting administrator access because the WinUAE shader folder requires it: ' + ExeRoot(''));
  if not ShellExec('runas', ExpandConstant('{tmp}\WinUAEShaderSetup.exe'), Parameters,
    '', SW_SHOWNORMAL, ewWaitUntilTerminated, ExitCode) then begin
    Result := 'Administrator access is needed because WinUAE is installed in a protected folder. Allow the Windows permission request to install its AmigaVision shader.';
    exit;
  end;
  if ExitCode <> 0 then begin
    Result := 'The AmigaVision shader could not be installed in the protected WinUAE folder. See the setup log at ' + ExpandConstant('{tmp}\WinUAE-shader.log');
    exit;
  end;
  if not FileExists(Destination) then begin
    Result := 'The AmigaVision shader was not installed in the WinUAE folder.';
    exit;
  end;
  if GetSHA256OfFile(Source) <> GetSHA256OfFile(Destination) then begin
    Result := 'The installed WinUAE shader does not match the AmigaVision release.';
    exit;
  end;
  ShaderInstalledWithAdmin := True;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  if SelectedExe = '' then DetectEmulator;
  FillDefaultDataFolder;
  Result := ValidateInputs;
  if Result = '' then Result := InstallProtectedShader;
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

function ShortcutEmulator(Path: String): String;
var
  Shell, Link: Variant;
  Name: String;
begin
  Result := '';
  if not FileExists(Path) then exit;
  try
    Shell := CreateOleObject('WScript.Shell');
    Link := Shell.CreateShortcut(Path);
    Name := Lowercase(ExtractFileName(String(Link.TargetPath)));
    if Name = 'amiberry.exe' then Result := 'Amiberry'
    else if (Name = 'winuae.exe') or (Name = 'winuae64.exe') then Result := 'WinUAE'
    else if Name = 'copperline.exe' then Result := 'Copperline';
  except
    Log('Could not identify the emulator used by shortcut: ' + Path);
  end;
end;

function HasOtherShortcut(Folder: String): Boolean;
var
  Current: String;
begin
  Current := Emulator('');
  Result := (FileExists(Folder + '\AmigaVision.lnk') and
    (ShortcutEmulator(Folder + '\AmigaVision.lnk') <> Current)) or
    ((Current <> 'Amiberry') and FileExists(Folder + '\AmigaVision (Amiberry).lnk')) or
    ((Current <> 'WinUAE') and FileExists(Folder + '\AmigaVision (WinUAE).lnk')) or
    ((Current <> 'Copperline') and FileExists(Folder + '\AmigaVision (Copperline).lnk'));
end;

procedure QualifyExistingShortcut(Folder: String);
var
  Plain, Qualified, Name: String;
  Index: Integer;
begin
  Plain := Folder + '\AmigaVision.lnk';
  Name := ShortcutEmulator(Plain);
  if Name = '' then exit; // Preserve unrecognized shortcuts instead of guessing.
  Qualified := Folder + '\AmigaVision (' + Name + ').lnk';
  Index := 2;
  while FileExists(Qualified) do begin
    Qualified := Folder + '\AmigaVision (' + Name + ') (' + IntToStr(Index) + ').lnk';
    Index := Index + 1;
  end;
  if not RenameFile(Plain, Qualified) then
    RaiseException('Could not rename the existing AmigaVision shortcut: ' + Plain);
end;

procedure WriteAmigaVisionShortcut(Folder: String; Qualified: Boolean);
var
  Name, Legacy: String;
begin
  Name := Folder + '\AmigaVision';
  if Qualified then Name := Name + ' (' + Emulator('') + ')';
  Name := Name + '.lnk';
  // Migrate a lone shortcut created by earlier setup versions to the plain name.
  Legacy := Folder + '\AmigaVision (' + Emulator('') + ').lnk';
  if not Qualified and not FileExists(Name) and FileExists(Legacy) and
     (ShortcutEmulator(Legacy) = Emulator('')) then
    if not RenameFile(Legacy, Name) then
      RaiseException('Could not rename the existing AmigaVision shortcut: ' + Legacy);
  if not ForceDirectories(Folder) then
    RaiseException('Could not create the shortcut folder: ' + Folder);
  CreateShellLink(Name, 'AmigaVision', ExePath(''), LaunchArgs(''), DataRoot(''),
    DataRoot('') + '\AmigaVision.ico', 0, SW_SHOWNORMAL);
end;

procedure InstallAmigaVisionShortcuts;
var
  Programs, Desktop: String;
  Qualified: Boolean;
begin
  Programs := ExpandConstant('{userprograms}');
  Desktop := ExpandConstant('{userdesktop}');
  Qualified := HasOtherShortcut(Programs) or HasOtherShortcut(Desktop);
  if Qualified then begin
    QualifyExistingShortcut(Programs);
    QualifyExistingShortcut(Desktop);
  end;
  WriteAmigaVisionShortcut(Programs, Qualified);
  if WizardIsTaskSelected('desktopicon') then WriteAmigaVisionShortcut(Desktop, Qualified);
end;


procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then begin
    if IsCopperline then begin
      if not ForceDirectories(DataRoot('') + '\configs') then
        RaiseException('Could not create the configuration folder.');
      WriteConfig(DataRoot('') + '\configs\AmigaVision.toml');
      if not ForceDirectories(CopperlineHome + '\configs') then
        RaiseException('Could not create the Copperline configuration folder.');
      if WizardIsTaskSelected('defaultconfig') then begin
        WriteConfig(CopperlineHome + '\configs\default.toml');
      end;
    end else begin
    if not ForceDirectories(DataRoot('') + '\Configurations') then
      RaiseException('Could not create the configuration folder.');
    WriteConfig(DataRoot('') + '\Configurations\AmigaVision.uae');
    if WizardIsTaskSelected('defaultconfig') then
      WriteConfig(DataRoot('') + '\Configurations\default.uae');
    end;
    InstallAmigaVisionShortcuts;
  end;
end;
