#ifndef ArtifactRoot
  #define ArtifactRoot "..\..\dist\charttrace-unsigned\release"
#endif
#ifndef InstallerOutputDir
  #define InstallerOutputDir "..\..\dist\installer"
#endif

[Setup]
AppId={{71DE9AF2-A18C-4FCE-A8EA-DDBB99A41C11}
AppName=ChartTrace
AppVersion=1.1
AppVerName=ChartTrace 1.1 UNSIGNED / NON-PRODUCTION
AppPublisher=ChartTrace
DefaultDirName={localappdata}\Programs\ChartTrace
DefaultGroupName=ChartTrace
OutputBaseFilename=ChartTrace-1.1-UNSIGNED_SYNTHETIC-Setup
OutputDir={#InstallerOutputDir}
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\ChartTrace.exe
SignedUninstaller=no
InfoBeforeFile={#ArtifactRoot}\UNSIGNED_NOTICE.txt

[Files]
Source: "{#ArtifactRoot}\ChartTrace-1.1-UNSIGNED_SYNTHETIC.exe"; DestDir: "{app}"; DestName: "ChartTrace.exe"; Flags: ignoreversion
Source: "{#ArtifactRoot}\UNSIGNED_NOTICE.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#ArtifactRoot}\ChartTrace-1.1.cdx.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#ArtifactRoot}\frozen-startup-receipt.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#ArtifactRoot}\ChartTrace-1.1-UNSIGNED_SYNTHETIC.exe.sha256"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\ChartTrace"; Filename: "{app}\ChartTrace.exe"
Name: "{autodesktop}\ChartTrace"; Filename: "{app}\ChartTrace.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"

[Run]
Filename: "{app}\ChartTrace.exe"; Description: "Launch ChartTrace"; Flags: nowait postinstall skipifsilent

