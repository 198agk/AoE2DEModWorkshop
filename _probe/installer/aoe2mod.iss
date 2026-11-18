; 模组工坊 安装包脚本（Inno Setup 6）
; 用法：ISCC.exe _probe\installer\aoe2mod.iss
; 装到 %LOCALAPPDATA%\Programs\AoE2ModWorkshop，不要管理员权限 —— 这个工具会往
; 自己目录旁边写 log\ 和 _mods_out\，装进 Program Files 之后那些写入会被拦。

; 版本号不在这里手写第二遍：`_probe/_tmp/pack_sel2.sh` 从 `aoe2mod/appversion.py`
; 的 VERSION 算出来，用 /DAppVer= 传进来 —— 就是玩家在关于页看到的那个四位
; 小数（1.0001），不是三段式。 下面这个值只是直接双击 ISCC 时的兜底，
; `_probe/test_about_page.py` 会拿它和 appversion.VERSION 对一次。
; 只有 Rust 那两个 manifest 用三段式：cargo 明确拒绝 `1.0001`（invalid leading
; zero in minor version number），它们拿的是派生出来的 SEMVER。
#ifndef AppVer
  #define AppVer "1.0003"
#endif
; 仓库根不写死：这个脚本就住在 <repo>\_probe\installer\，往上两级就是它。
; 换机器/换盘符不用改文件；要指到别处就 ISCC.exe /DRepoDir=D:\path\repo aoe2mod.iss
#ifndef RepoDir
  #define RepoDir SourcePath + "..\.."
#endif
#define SrcDir RepoDir + "\_out\AoE2ModWorkshop-COMPLETE"

[Setup]
AppId={{6C1E4B23-7A4D-4F18-9C55-2B7E0D9A3F61}
AppName=AoE2 DE Mod Workshop
AppVerName=AoE2 DE Mod Workshop {#AppVer}
AppVersion={#AppVer}
AppPublisher=RemonBo
AppPublisherURL=https://github.com/198agk
AppSupportURL=https://github.com/198agk
VersionInfoVersion={#AppVer}
VersionInfoDescription=AoE2 DE Mod Workshop 安装程序
VersionInfoCompany=RemonBo
DefaultDirName={localappdata}\Programs\AoE2ModWorkshop
DefaultGroupName=AoE2 DE Mod Workshop
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir={#RepoDir}\_out
OutputBaseFilename=AoE2DEModWorkshop-{#AppVer}-setup
SetupIconFile={#RepoDir}\brand\app-icon.ico
; 安装向导左右两张图也从同一张母版 app-icon.png 生成（_probe/installer/ 下两个 .bmp），
; 不再用 Inno 自带的那个蓝色盒子 —— 一个包从图标到向导里外都该是同一个东西。
WizardImageFile={#RepoDir}\_probe\installer\wizard.bmp
WizardSmallImageFile={#RepoDir}\_probe\installer\wizard-small.bmp
WizardImageStretch=no
UninstallDisplayIcon={app}\AoE2 DE Mod Workshop.exe
UninstallDisplayName=AoE2 DE Mod Workshop {#AppVer}
LicenseFile={#RepoDir}\LICENSE
InfoBeforeFile={#SrcDir}\README.txt
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
SetupLogging=yes
ShowLanguageDialog=auto
AllowNoIcons=yes
DisableReadyPage=no

[Languages]
Name: "zh"; MessagesFile: "{#RepoDir}\_probe\installer\ChineseSimplified.isl"
Name: "en"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "{#SrcDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\AoE2 DE Mod Workshop"; Filename: "{app}\AoE2 DE Mod Workshop.exe"; WorkingDir: "{app}"
Name: "{group}\{cm:UninstallProgram,AoE2 DE Mod Workshop}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\AoE2 DE Mod Workshop"; Filename: "{app}\AoE2 DE Mod Workshop.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\AoE2 DE Mod Workshop.exe"; Description: "{cm:LaunchProgram,AoE2 DE Mod Workshop}"; WorkingDir: "{app}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\log"
Type: filesandordirs; Name: "{app}\_mods_out"
; 自带解释器第一次启动会在 runtime\Lib 下写出 __pycache__。那些字节不是安装程序
; 放的，卸载时默认不会碰，于是卸载完只剩一个装着 .pyc 的空壳目录。逐条点名删掉。
Type: filesandordirs; Name: "{app}\runtime\Lib\__pycache__"
Type: filesandordirs; Name: "{app}\runtime\Lib\encodings\__pycache__"
Type: filesandordirs; Name: "{app}\runtime\Lib\collections\__pycache__"
Type: filesandordirs; Name: "{app}\runtime\DLLs\__pycache__"
Type: dirifempty; Name: "{app}"

[Code]
function InitializeSetup(): Boolean;
var
  FreeMB, TotalMB: Cardinal;
  Root: String;
begin
  Result := True;
  Root := ExpandConstant('{localappdata}');
  { 完整包解压后约 420 MB；留 900 MB 余量，装到一半没空间比直接拒绝更糟 }
  if GetSpaceOnDisk(Root, True, FreeMB, TotalMB) then
  begin
    if FreeMB < 900 then
    begin
      MsgBox('系统盘剩余空间不足 900 MB，装不下这个工具（解压后约 420 MB）。' + #13#10 +
             '先清理一些空间，再运行安装程序。', mbError, MB_OK);
      Result := False;
    end;
  end;
end;
