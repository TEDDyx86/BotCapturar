#define AppName "BotCapturar"
#define AppVersion "0.1.0"
#define AppExeName "BotCapturar.exe"

[Setup]
AppId={{7E6C90B4-00A1-49E3-9B52-B7CEEB9D7FD9}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=BotCapturar
SetupIconFile=..\assets\BotCapturar.ico
DefaultDirName={localappdata}\Programs\BotCapturar
DefaultGroupName=BotCapturar
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#AppExeName}
OutputDir=..\dist\installer
OutputBaseFilename=BotCapturar-Setup
WizardStyle=modern
Uninstallable=yes

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na área de trabalho"; Flags: unchecked

[Files]
Source: "..\dist\{#AppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\BotCapturar"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\BotCapturar"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Iniciar o BotCapturar"; Flags: postinstall nowait skipifsilent
