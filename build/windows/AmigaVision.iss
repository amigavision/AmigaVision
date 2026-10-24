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
SetupIconFile=assets\AmigaVision.ico
WizardImageFile=
WizardSmallImageFile=assets\AV-avatar.png
DisableWelcomePage=no
DisableFinishedPage=no
OutputDir=output
OutputBaseFilename=Install AmigaVision for Windows
Compression=lzma2
ArchiveExtraction=full

[Messages]
WelcomeLabel2=AmigaVision is the ultimate Amiga games & demo scene collection for MiSTer & Pocket FPGAs, Raspberry Pi + emulators — and Amiga 1200, 4000 & CD32.%n%nLet’s get AmigaVision installed on your Windows computer.
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
Name: defaultconfig; Description: "Start AmigaVision when the emulator opens"
Name: desktopicon; Description: "Create a desktop shortcut"

[Files]
Source: "assets\banner.bmp"; Flags: dontcopy
Source: "assets\AmigaVision.ico"; DestDir: "{code:DataRoot}"; Flags: ignoreversion
Source: "{code:Payload}\HardDrives\AmigaVision.hdf"; DestDir: "{code:DataRoot}\HardDrives"; Flags: external ignoreversion
Source: "{code:Payload}\HardDrives\AmigaVision-Saves.hdf"; DestDir: "{code:DataRoot}\HardDrives"; Flags: external onlyifdoesntexist
Source: "{code:Payload}\HardDrives\Shared\*"; DestDir: "{code:DataRoot}\HardDrives\Shared"; Flags: external recursesubdirs createallsubdirs onlyifdoesntexist
Source: "{code:Payload}\HardDrives\listings\*"; DestDir: "{code:DataRoot}\HardDrives\listings"; Flags: external recursesubdirs createallsubdirs ignoreversion
Source: "{code:Payload}\{code:Emulator}\ROMs\AmigaVision.rom"; DestDir: "{code:DataRoot}\ROMs"; Flags: external ignoreversion
Source: "{code:Payload}\Amiberry\Visuals\*"; DestDir: "{code:DataRoot}\Visuals"; Flags: external recursesubdirs createallsubdirs ignoreversion; Check: IsAmiberry
Source: "{code:Payload}\WinUAE\plugins\*"; DestDir: "{code:ExeRoot}\plugins"; Flags: external recursesubdirs createallsubdirs ignoreversion; Check: IsWinUAE

[Run]
Filename: "{code:ExePath}"; Parameters: "{code:LaunchArgs}"; WorkingDir: "{code:DataRoot}"; Description: "Launch AmigaVision"; Flags: postinstall nowait skipifsilent runasoriginaluser

[Code]
var
  TargetPage: TWizardPage;
  EmulatorChoices: array[0..2] of TNewRadioButton;
  SourcePage: TInputFileWizardPage;
  DataPage: TInputDirWizardPage;
  ExtractedFolderButton: TNewButton;
  ResolvedPayload, ResolvedSource: String;
  ExtractionCount: Integer;
  ExtractionProgress: TOutputProgressWizardPage;
  ProgramPage: TInputDirWizardPage;
  DestinationNotice: TNewStaticText;
  SelectedExe: String;
  ConfigText: AnsiString;

function IsAmiberry: Boolean;
begin
  if EmulatorChoices[0] = nil then
    Result := CompareText(ExpandConstant('{param:EMULATOR|Amiberry}'), 'WinUAE') <> 0
  else
    Result := EmulatorChoices[0].Checked;
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
  Result := ResolvedPayload;
  if Result = '' then Result := ExpandConstant('{param:PAYLOAD|{src}}');
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
  Folder := GetEnv('USERPROFILE');
  if Folder <> '' then begin
    ScanNamedFolders(AddBackslash(Folder) + 'Downloads');
    ScanNamedFolders(Folder);
  end;
  if SelectedExe <> '' then Log('Detected ' + Emulator('') + ': ' + SelectedExe)
  else Log('No ' + Emulator('') + ' installation found.');
end;

function CompleteRelease(Root: String): Boolean;
var
  Platform: String;
begin
  Platform := AddBackslash(Root) + Emulator('') + '\';
  Result := (Root <> '') and
    FileExists(AddBackslash(Root) + 'HardDrives\AmigaVision.hdf') and
    FileExists(AddBackslash(Root) + 'HardDrives\AmigaVision-Saves.hdf') and
    DirExists(AddBackslash(Root) + 'HardDrives\Shared') and
    DirExists(AddBackslash(Root) + 'HardDrives\listings') and
    FileExists(Platform + 'ROMs\AmigaVision.rom') and
    FileExists(Platform + 'Configurations\AmigaVision.uae');
  if Result then begin
    if IsAmiberry then Result := DirExists(Platform + 'Visuals\Shaders')
    else Result := DirExists(Platform + 'plugins\filtershaders\direct3d');
  end;
end;

function FindReleaseFolder(Root: String): String;
var
  Find: TFindRec;
  Candidate: String;
begin
  Result := '';
  if CompleteRelease(Root) then begin Result := Root; exit; end;
  if FindFirst(AddBackslash(Root) + 'AmigaVision-Emulators*', Find) then begin
    try
      repeat
        Candidate := AddBackslash(Root) + Find.Name;
        if ((Find.Attributes and FILE_ATTRIBUTE_DIRECTORY) <> 0) and CompleteRelease(Candidate) then begin
          Result := Candidate;
          exit;
        end;
      until not FindNext(Find);
    finally
      FindClose(Find);
    end;
  end;
end;

function NearbyRelease: String;
var
  Find: TFindRec;
  Root, Candidate, Extension: String;
  Count: Integer;
begin
  Root := ExpandConstant('{src}');
  Result := '';
  if CompleteRelease(Root) then begin Result := Root; exit; end;
  Count := 0;
  if FindFirst(AddBackslash(Root) + 'AmigaVision-Emulators*', Find) then begin
    try
      repeat
        Candidate := AddBackslash(Root) + Find.Name;
        Extension := Lowercase(ExtractFileExt(Find.Name));
        if (((Find.Attributes and FILE_ATTRIBUTE_DIRECTORY) <> 0) and CompleteRelease(Candidate)) or
           (((Find.Attributes and FILE_ATTRIBUTE_DIRECTORY) = 0) and
            ((Extension = '.7z') or (Extension = '.zip'))) then begin
          Count := Count + 1;
          Result := Candidate;
        end;
      until not FindNext(Find);
    finally
      FindClose(Find);
    end;
  end;
  // Let the user choose rather than silently selecting among multiple releases.
  if Count <> 1 then Result := '';
end;

function ReleaseExtractionProgress(const ArchiveName, FileName: String; const Progress, ProgressMax: Int64): Boolean;
begin
  Result := True;
  if ExtractionProgress <> nil then begin
    ExtractionProgress.SetText(ExtractFileName(ArchiveName), FileName);
    if ProgressMax > 0 then ExtractionProgress.SetProgress(Progress * 1000 div ProgressMax, 1000);
  end;
end;

function ResolveRelease: String;
var
  Source, Extracted, Extension: String;
begin
  Result := '';
  Source := Trim(SourcePage.Values[0]);
  if (Source = ResolvedSource) and CompleteRelease(ResolvedPayload) then exit;
  ResolvedPayload := '';
  if DirExists(Source) then
    ResolvedPayload := FindReleaseFolder(Source)
  else if FileExists(Source) then begin
    Extension := Lowercase(ExtractFileExt(Source));
    if (Extension <> '.7z') and (Extension <> '.zip') then begin
      Result := 'Choose an AmigaVision-Emulators .7z or .zip archive, or its extracted folder.';
      exit;
    end;
    ExtractionCount := ExtractionCount + 1;
    Extracted := ExpandConstant('{tmp}') + '\release-' + IntToStr(ExtractionCount);
    if ExtractionProgress = nil then ExtractionProgress := CreateOutputProgressPage('Extracting AmigaVision',
      'Preparing the release files. Large disk images can take several minutes.');
    try
      ExtractionProgress.SetText(ExtractFileName(Source), '');
      ExtractionProgress.Show;
      try
        ExtractArchive(Source, Extracted, '', True, @ReleaseExtractionProgress);
      finally
        ExtractionProgress.Hide;
      end;
      ResolvedPayload := FindReleaseFolder(Extracted);
    except
      Result := 'Could not extract the release: ' + GetExceptionMessage;
      exit;
    end;
  end;
  if ResolvedPayload = '' then
    Result := 'Choose the AmigaVision-Emulators release archive or a complete extracted release folder.'
  else begin
    ResolvedSource := Source;
    Log('Release files: ' + ResolvedPayload);
  end;
end;

procedure ChooseExtractedRelease(Sender: TObject);
var
  Folder: String;
begin
  Folder := '';
  if BrowseForFolder('Choose the extracted AmigaVision emulator release', Folder, False) then
    SourcePage.Values[0] := Folder;
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
  if SourcePage <> nil then
    if PageID = SourcePage.ID then begin
      Result := CompleteRelease(ResolvedPayload);
      exit;
    end;
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

procedure AddEmulatorChoice(Index: Integer; Caption: String; Available: Boolean);
var
  Link: TNewLinkLabel;
  URL: String;
begin
  case Index of
    0: URL := 'https://github.com/BlitterStudio/amiberry/releases';
    1: URL := 'https://copperline.dev/';
    2: URL := 'https://www.winuae.net/download/';
  end;
  EmulatorChoices[Index] := TNewRadioButton.Create(WizardForm);
  with EmulatorChoices[Index] do begin
    Parent := TargetPage.Surface;
    SetBounds(0, ScaleY(16 + Index * 40), ScaleX(240), ScaleY(24));
    Enabled := Available;
    TabOrder := Index * 2;
  end;
  EmulatorChoices[Index].Caption := Caption;
  Link := TNewLinkLabel.Create(WizardForm);
  Link.Parent := TargetPage.Surface;
  Link.SetBounds(ScaleX(260), ScaleY(20 + Index * 40), ScaleX(120), ScaleY(20));
  Link.Caption := '<a href="' + URL + '">Download</a>';
  Link.UseVisualStyle := True;
  Link.TabStop := True;
  Link.TabOrder := Index * 2 + 1;
  Link.Tag := Index;
  Link.OnLinkClick := @DownloadEmulator;
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
  DestinationNotice.Caption := Notice;
  DestinationNotice.AdjustHeight;
end;

function AddBrandBanner(Page: TWinControl): Integer;
var
  Banner: TBitmapImage;
begin
  Banner := TBitmapImage.Create(WizardForm);
  Banner.Parent := Page;
  Banner.Bitmap.LoadFromFile(ExpandConstant('{tmp}\banner.bmp'));
  Banner.Stretch := True;
  Banner.SetBounds(0, 0, Page.ClientWidth, Page.ClientWidth * 300 div 1491);
  Result := Banner.Height + ScaleY(20);
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
    Top := WizardForm.WelcomeLabel1.Top + WizardForm.WelcomeLabel1.Height + ScaleY(16);
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

procedure LayoutCompletionOptions;
var
  Top: Integer;
begin
  WizardForm.FinishedLabel.Visible := False;
  Top := WizardForm.FinishedHeadingLabel.Top + WizardForm.FinishedHeadingLabel.Height + ScaleY(16);
  WizardForm.RunList.SetBounds(ScaleX(24), Top,
    WizardForm.FinishedPage.ClientWidth - ScaleX(48),
    WizardForm.FinishedPage.ClientHeight - Top - ScaleY(16));
end;

procedure InitializeWizard;
begin
  Log('Creating AmigaVision setup pages');
  TargetPage := CreateCustomPage(wpWelcome, 'Choose your emulator',
    'Select an installed emulator. Use its download link if you need to install it first.');
  AddEmulatorChoice(0, 'Amiberry', True);
  AddEmulatorChoice(1, 'Copperline (coming soon)', False);
  AddEmulatorChoice(2, 'WinUAE', True);
  EmulatorChoices[0].Checked := True;
  if CompareText(ExpandConstant('{param:EMULATOR|Amiberry}'), 'WinUAE') = 0 then
    EmulatorChoices[2].Checked := True;
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
  SourcePage := CreateInputFilePage(DataPage.ID, 'Locate your AmigaVision release',
    'Where is your downloaded release?',
    'Setup could not automatically select a release beside the installer. Choose an AmigaVision-Emulators archive, or use the button below to choose an extracted release folder.');
  SourcePage.Add('Release archive or extracted folder:', 'AmigaVision emulator release|AmigaVision-Emulators*.7z;AmigaVision-Emulators*.zip|Archives|*.7z;*.zip', '.7z');
  SourcePage.Values[0] := ExpandConstant('{param:PAYLOAD|}');
  ExtractedFolderButton := TNewButton.Create(WizardForm);
  ExtractedFolderButton.Parent := SourcePage.Surface;
  ExtractedFolderButton.SetBounds(0, SourcePage.Edits[0].Top + SourcePage.Edits[0].Height + ScaleY(16), ScaleX(220), ScaleY(25));
  ExtractedFolderButton.Caption := 'Choose extracted folder...';
  ExtractedFolderButton.OnClick := @ChooseExtractedRelease;
  BrandWelcomeAndFinish;
  Log('AmigaVision setup pages ready');
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  if CurPageID = wpFinished then LayoutCompletionOptions;
  if DataPage = nil then exit;
  if (CurPageID = DataPage.ID) and (DataPage.Values[0] = '') then begin
    if IsWinUAE then
      DataPage.Values[0] := ExpandConstant('{commondocs}\Amiga Files\WinUAE')
    else
      DataPage.Values[0] := ExeRoot('');
  end;
  if CurPageID = DataPage.ID then UpdateDestinationNotice(nil);
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
  Error := '';
  if CurPageID = DataPage.ID then begin
    Error := ValidateDestination;
    if Error = '' then begin
      if SourcePage.Values[0] = '' then SourcePage.Values[0] := NearbyRelease;
      if SourcePage.Values[0] <> '' then begin
        // Source errors belong on the following release page, not this destination page.
        SourcePage.Description := ResolveRelease;
        if SourcePage.Description = '' then SourcePage.Description := 'Where is your downloaded release?';
      end;
    end;
  end;
  if CurPageID = SourcePage.ID then begin
    Error := ResolveRelease;
    if Error = '' then Error := ValidateInputs;
  end;
  if Error <> '' then begin
    Log(Error);
    if not WizardSilent then MsgBox(Error, mbError, MB_OK);
    Result := False;
  end;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  if SelectedExe = '' then DetectEmulator;
  if SourcePage.Values[0] = '' then SourcePage.Values[0] := NearbyRelease;
  Result := ResolveRelease;
  if Result = '' then Result := ValidateInputs;
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
    if not ForceDirectories(DataRoot('') + '\Configurations') then
      RaiseException('Could not create the configuration folder.');
    WriteConfig(DataRoot('') + '\Configurations\AmigaVision.uae');
    if WizardIsTaskSelected('defaultconfig') then
      WriteConfig(DataRoot('') + '\Configurations\default.uae');
    InstallAmigaVisionShortcuts;
  end;
end;
