; Solo se compila en el equipo/CI de mantenimiento. No incluye fuentes.
[Setup]
AppId={{967416AB-8F50-45ED-A871-090B025CA0F5}
AppName=Cuy
AppVersion={#Version}
VersionInfoVersion={#FileVersion}
DefaultDirName={localappdata}\Programs\Cuy
DefaultGroupName=Cuy
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir={#Output}
OutputBaseFilename=cuy-instalar-{#Version}-windows-x64
Compression=lzma2
SolidCompression=yes
UninstallDisplayIcon={app}\cuy.exe

[Files]
Source: "{#Package}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Configurar Cuy"; Filename: "{app}\cuy.exe"; Parameters: "configurar"; WorkingDir: "{app}"
Name: "{group}\Diagnóstico de Cuy"; Filename: "{app}\cuy.exe"; Parameters: "doctor"; WorkingDir: "{app}"

[Run]
Filename: "{app}\cuy.exe"; Parameters: "configurar"; Description: "Configurar conexión a Databricks"; Flags: postinstall skipifsilent unchecked
