"""The one native dialog in this tool: "which folder should these go in?".

Written 2026-11-26 for 「或者你让这个功能存的图片，让用户选择存放位置」.  The two
blank-sheet buttons had just learned to keep a copy in `<tool>/sheets`, which
answered "where is it" but not "I keep my art on D:".  The page can hand the
browser a download but it cannot name a folder, so the folder has to be picked
by Windows itself.

Why PowerShell and not tkinter: the shipped `runtime/` has no `tkinter/` and no
`tcl/` (checked by glob -- the embeddable distribution does not carry them), so
a Python dialog is simply not available.  Why not the Tauri dialog plugin:
`desktop/src-tauri/Cargo.toml` carries no dialog crate, and adding one means a
new exe build for what a five-line Windows call already does.

Two facts were measured before writing this, because a folder dialog that never
appears is worse than no button at all:

* `FolderBrowserDialog` shows a real modal window from this machine (screenshot:
  title 浏览文件夹, the tree listing SSD (D:) and this very workspace).
* it still shows when the caller has no window of its own -- a `Popen` with
  `CREATE_NO_WINDOW` and three closed standard streams was enough, which is what
  `run_ui.py --serve-only` and the packaged exe both are.  The same flags are
  what `aoe2mod/autoupdate.py` already uses to spawn its own child.

The result comes back through a file rather than stdout: PowerShell 5.1 encodes
console output in the OEM code page, and a folder called 「我的图」 would arrive
as mojibake.  `[IO.File]::WriteAllText` with an explicit UTF-8 encoder does not.
"""
import os
import subprocess
import tempfile

#: The script PowerShell runs.  `AOE2MOD_PICK_START` is the folder to open at,
#: `AOE2MOD_PICK_OUT` is where the answer goes.  Both are passed by environment
#: variable, never spliced into the source: a path with a quote in it must not be
#: able to become PowerShell.
#:
#: The 1x1 invisible owner form is not decoration.  Without an owner the dialog
#: can open BEHIND the browser and the player sees nothing happen; a form that is
#: shown but transparent makes Windows treat the dialog as this process own, so
#: it comes to the front and the taskbar shows a live window.
SCRIPT = r"""$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$owner = New-Object System.Windows.Forms.Form
$owner.Text = 'sheets'
$owner.TopMost = $true
$owner.ShowInTaskbar = $false
$owner.FormBorderStyle = 'None'
$owner.Size = New-Object System.Drawing.Size(1,1)
$owner.StartPosition = 'CenterScreen'
$owner.Opacity = 0
$owner.Show()
$owner.Activate()
$d = New-Object System.Windows.Forms.FolderBrowserDialog
$d.Description = '空表要存到哪个文件夹？'
$d.ShowNewFolderButton = $true
if ($env:AOE2MOD_PICK_START -and (Test-Path -LiteralPath $env:AOE2MOD_PICK_START)) {
    $d.SelectedPath = $env:AOE2MOD_PICK_START
}
$r = $d.ShowDialog($owner)
$owner.Close()
if ($r -eq [System.Windows.Forms.DialogResult]::OK) {
    $enc = New-Object System.Text.UTF8Encoding $false
    [IO.File]::WriteAllText($env:AOE2MOD_PICK_OUT, $d.SelectedPath, $enc)
    exit 0
}
exit 3
"""

#: How long a player may leave the dialog open before this gives up on them.
#: Ten minutes: long enough to browse to another drive and make a folder, short
#: enough that a wedged PowerShell does not hold a thread forever.
TIMEOUT = 600


def available():
    """Whether this machine can show the dialog at all. Windows only."""
    return os.name == "nt" and bool(os.environ.get("SystemRoot"))


def pick_folder(start="", timeout=TIMEOUT):
    """Show the folder dialog and answer the chosen path; "" means cancelled.

    Blocking -- the caller runs this on its own thread, because a modal window
    can sit on screen for minutes and no HTTP reply may wait that long.  Any
    failure (no PowerShell, a killed process, a timeout) comes back as "" with
    the reason in `last_error()`; the caller treats it as "nothing picked" and
    the folder in use does not change.
    """
    global _LAST_ERROR
    _LAST_ERROR = ""
    if not available():
        _LAST_ERROR = "这个系统没有文件夹对话框"
        return ""
    work = tempfile.mkdtemp(prefix="aoe2mod-pick-")
    script = os.path.join(work, "pick.ps1")
    answer = os.path.join(work, "answer.txt")
    try:
        with open(script, "w", encoding="utf-8-sig", newline="\r\n") as fh:
            fh.write(SCRIPT)
        env = dict(os.environ)
        env["AOE2MOD_PICK_START"] = start or ""
        env["AOE2MOD_PICK_OUT"] = answer
        cmd = ["powershell", "-NoProfile", "-STA", "-ExecutionPolicy", "Bypass",
               "-File", script]
        flags = 0x08000000 | 0x00000200          # CREATE_NO_WINDOW | NEW_GROUP
        p = subprocess.Popen(cmd, env=env, stdin=subprocess.DEVNULL,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             creationflags=flags)
        try:
            out, err = p.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            p.kill()
            p.communicate()
            _LAST_ERROR = "文件夹对话框等太久了"
            return ""
        if p.returncode == 3:
            return ""                              # cancelled, not an error
        if p.returncode != 0:
            why = (err or b"").decode("utf-8", "replace").strip()
            # A dialog the player closed, or one this process tore down, exits
            # non-zero with nothing on stderr.  Only PowerShell COMPLAINING is
            # worth a sentence: "起不来" over a window that was in fact on
            # screen sends the player looking for a bug that is not there.
            if why:
                _LAST_ERROR = "文件夹对话框起不来：%s" % (why[:200],)
            return ""
        try:
            with open(answer, "r", encoding="utf-8") as fh:
                got = fh.read().strip()
        except Exception:                          # noqa: BLE001
            _LAST_ERROR = "文件夹对话框没留下答案"
            return ""
        return got
    finally:
        for path in (script, answer):
            try:
                os.remove(path)
            except Exception:                      # noqa: BLE001
                pass
        try:
            os.rmdir(work)
        except Exception:                          # noqa: BLE001
            pass


_LAST_ERROR = ""


def last_error():
    """Why the last `pick_folder` answered "": cancelled, or a reason."""
    return _LAST_ERROR
