; Compile com Inno Setup 6 depois de gerar o EXE.
[Setup]
AppId={{273B67B1-4C77-4B7D-8954-5C82AB33D1F5}
AppName=Calendário de Férias STMU
AppVersion=1.1.0
AppPublisher=STMU
DefaultDirName={localappdata}\Programs\STMU\CalendarioFerias
DefaultGroupName=STMU
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=InstaladorCalendarioFeriasSTMU
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\CalendarioFeriasSTMU.exe
CloseApplications=yes

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Files]
Source: "..\dist\CalendarioFeriasSTMU.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Calendário de Férias STMU"; Filename: "{app}\CalendarioFeriasSTMU.exe"
Name: "{autodesktop}\Calendário de Férias STMU"; Filename: "{app}\CalendarioFeriasSTMU.exe"

[Run]
Filename: "{app}\CalendarioFeriasSTMU.exe"; Description: "Abrir o Calendário de Férias STMU"; Flags: nowait postinstall skipifsilent
