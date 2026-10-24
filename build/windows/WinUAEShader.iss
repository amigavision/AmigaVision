; Elevated helper: only copies the AmigaVision shader into the selected WinUAE installation.
[Setup]
AppId=AmigaVisionWinUAEShader
AppName=AmigaVision WinUAE Shader Installer
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
OutputBaseFilename=WinUAEShaderSetup

[Files]
Source: "{param:SHADERSOURCE}"; DestDir: "{param:WINUAEDIR}\plugins\filtershaders\direct3d"; DestName: "CRT-Pi-SmartRes.fx"; Flags: external ignoreversion overwritereadonly

[Code]
function InitializeSetup: Boolean;
var
  Folder, Source: String;
begin
  Folder := ExpandConstant('{param:WINUAEDIR|}');
  Source := ExpandConstant('{param:SHADERSOURCE|}');
  Result := (Folder <> '') and FileExists(Source) and
    (CompareText(ExtractFileName(Source), 'CRT-Pi-SmartRes.fx') = 0) and
    (FileExists(AddBackslash(Folder) + 'winuae.exe') or
     FileExists(AddBackslash(Folder) + 'winuae64.exe'));
  if not Result then
    SuppressibleMsgBox('The WinUAE installation or AmigaVision shader could not be found.', mbError, MB_OK, IDOK);
end;
