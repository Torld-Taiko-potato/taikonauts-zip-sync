#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif

[Setup]
AppId={{30AC8183-13D8-4B3E-91E4-E4136C2E22AD}}
AppName=TJA譜面同期
AppVersion={#AppVersion}
AppPublisher=Torld-Taiko-potato
SetupIconFile=assets\taikonauts_sync.ico
DefaultDirName={localappdata}\Programs\TaikoNauts ZIP Sync
DefaultGroupName=TJA譜面同期
PrivilegesRequired=lowest
CloseApplications=yes
RestartApplications=no
OutputDir=dist-installer
OutputBaseFilename=TJA-Chart-Sync-Setup
UninstallDisplayIcon={app}\TaikoNautsZipSync.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "japanese"; MessagesFile: "compiler:Languages\Japanese.isl"

[Tasks]
Name: "desktopicon"; Description: "デスクトップにショートカットを作成する"; GroupDescription: "追加タスク:"; Flags: unchecked

[InstallDelete]
Type: files; Name: "{userprograms}\TaikoNauts ZIP Sync.lnk"
Type: files; Name: "{userdesktop}\TaikoNauts ZIP Sync.lnk"

[Files]
Source: "dist\TaikoNautsZipSync.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\TJA譜面同期"; Filename: "{app}\TaikoNautsZipSync.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\TJA譜面同期"; Filename: "{app}\TaikoNautsZipSync.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\TaikoNautsZipSync.exe"; Description: "TJA譜面同期を起動"; Flags: postinstall nowait skipifsilent
