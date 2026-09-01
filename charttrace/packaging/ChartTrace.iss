#ifndef SourceRoot
  #define SourceRoot "..\.."
#endif

[Setup]
AppId={{71DE9AF2-A18C-4FCE-A8EA-DDBB99A41C11}
AppName=ChartTrace
AppVersion=1.1
AppVerName=ChartTrace 1.1 UNSIGNED_SYNTHETIC
AppPublisher=ChartTrace
DefaultDirName={localappdata}\Programs\ChartTrace
DefaultGroupName=ChartTrace
OutputBaseFilename=ChartTrace-1.1-UNSIGNED_SYNTHETIC-Setup
OutputDir={#SourceRoot}\dist\installer
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\ChartTrace.exe
SignedUninstaller=no

[Files]
Source: "{#SourceRoot}\dist\ChartTrace.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceRoot}\charttrace\packaging\build_manifest.json"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\ChartTrace"; Filename: "{app}\ChartTrace.exe"
Name: "{autodesktop}\ChartTrace"; Filename: "{app}\ChartTrace.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"

[Run]
Filename: "{app}\ChartTrace.exe"; Description: "Launch ChartTrace"; Flags: nowait postinstall skipifsilent
