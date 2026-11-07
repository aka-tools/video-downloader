; Copyright (c) 2026 AKA. All rights reserved.
; Inno Setup script: packs the whole app into ONE installer file.
; Built automatically by Setup.bat (in the main folder). Paths below are relative to build_tools\.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#ifndef AppLabel
  #define AppLabel "V1"
#endif
#define AppName      "Video Downloader"
#define AppPublisher "AKA"
#define AppExe       "VideoDownloader.exe"

[Setup]
AppId={{B9561365-3B62-4E39-ABF1-5F8D1B8ABB29}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppLabel}
AppPublisher={#AppPublisher}
AppCopyright=Copyright (c) 2026 {#AppPublisher}. All rights reserved.
VersionInfoVersion={#AppVersion}
VersionInfoCompany={#AppPublisher}
VersionInfoDescription={#AppName} {#AppLabel} Setup
VersionInfoCopyright=Copyright (c) 2026 {#AppPublisher}
; per-user install: no administrator rights, nothing outside the user's own profile
PrivilegesRequired=lowest
DefaultDirName={localappdata}\Programs\VideoDownloader
DisableDirPage=yes
DisableProgramGroupPage=yes
DisableReadyPage=yes
LicenseFile=..\app\LICENSE.txt
SetupIconFile=..\app\icon.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
WizardStyle=modern
Compression=lzma2/max
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
CloseApplications=yes
RestartApplications=no
OutputDir=..
OutputBaseFilename=VideoDownloader-Setup-{#AppLabel}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &Desktop shortcut"; Flags: checkedonce

[InstallDelete]
; remove files from an older version before installing the new one
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "..\_build\dist\VideoDownloader\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\app\LICENSE.txt";             DestDir: "{app}"; Flags: ignoreversion
Source: "..\docs\README.txt";              DestDir: "{app}"; Flags: ignoreversion
Source: "..\docs\THIRD_PARTY_NOTICES.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\docs\SECURITY.md";             DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}";  Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "Start {#AppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; saved login (encrypted), private browser profile, settings and logs - downloaded videos are NOT touched
Type: filesandordirs; Name: "{localappdata}\VideoDownloader"
