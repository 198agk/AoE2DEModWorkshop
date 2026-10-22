# Hover a list of client-area points with SendInput and grab one frame after each.
#
# Why SendInput and not SetCursorPos: measured 2026-10-21 -- hovering the food icon
# with SetCursorPos produced 0 changed pixels, while SendInput's MOUSEEVENTF_MOVE
# produced 3491.  The game reads pointer MOVEMENT from the input stream; relocating
# the cursor emits no movement event, so the game never learns it moved.
#
# Frames are stable enough to compare while the game is paused (F3): two idle frames
# differed by 0 pixels at threshold 24 (measured), so any tooltip that appears is the
# only difference.
#
#   powershell.exe -ExecutionPolicy Bypass -File sendgrid.ps1 -Pts "x,y;x,y" -Out dir -WaitMs 800
param(
    [string]$Pts = "5,5",
    [string]$Out = "_probe\shots\sgrid",
    [string]$Park = "5,5",
    [int]$WaitMs = 800
)
Add-Type -AssemblyName System.Drawing
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public class SgScr {
    [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
    [DllImport("user32.dll")] public static extern bool SetProcessDpiAwarenessContext(IntPtr v);
    [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
    [DllImport("user32.dll")] public static extern bool GetCursorPos(out POINT p);
    [DllImport("user32.dll")] public static extern uint SendInput(uint n, INPUT[] i, int cb);
    [DllImport("user32.dll")] public static extern bool GetClientRect(IntPtr h, out RECT r);
    [DllImport("user32.dll")] public static extern bool ClientToScreen(IntPtr h, ref POINT p);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] public static extern bool BringWindowToTop(IntPtr h);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
    [DllImport("user32.dll")] public static extern bool AttachThreadInput(uint a, uint b, bool f);
    [DllImport("kernel32.dll")] public static extern uint GetCurrentThreadId();
    [DllImport("user32.dll")] public static extern int GetSystemMetrics(int i);
    [StructLayout(LayoutKind.Sequential)] public struct POINT { public int X; public int Y; }
    [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L; public int T; public int R; public int B; }
    [StructLayout(LayoutKind.Sequential)] public struct MOUSEINPUT {
        public int dx; public int dy; public uint mouseData; public uint dwFlags; public uint time; public IntPtr dwExtraInfo; }
    [StructLayout(LayoutKind.Sequential)] public struct INPUT { public uint type; public MOUSEINPUT mi; }
    public static void MoveTo(int px, int py) {
        int sw = GetSystemMetrics(78), sh = GetSystemMetrics(79);
        int ax = (int)Math.Round(px * 65535.0 / (sw - 1));
        int ay = (int)Math.Round(py * 65535.0 / (sh - 1));
        INPUT[] inp = new INPUT[1];
        inp[0].type = 0;
        inp[0].mi.dx = ax; inp[0].mi.dy = ay;
        inp[0].mi.dwFlags = 0x0001 | 0x8000;
        inp[0].mi.time = 0;
        SendInput(1, inp, Marshal.SizeOf(typeof(INPUT)));
    }
}
"@
[void][SgScr]::SetProcessDpiAwarenessContext([IntPtr](-4))
[void][SgScr]::SetProcessDPIAware()
$p = Get-Process AoE2DE_s -ErrorAction Stop
$h = $p.MainWindowHandle
$r = New-Object SgScr+RECT
[void][SgScr]::GetClientRect($h, [ref]$r)
$c = New-Object SgScr+POINT
[void][SgScr]::ClientToScreen($h, [ref]$c)
[void][SgScr]::ShowWindow($h, 9)
[void][SgScr]::BringWindowToTop($h)
$fg = [SgScr]::GetForegroundWindow()
if ($fg -ne $h) {
    $tid = [SgScr]::GetWindowThreadProcessId($h, [ref]([uint32]0))
    [void][SgScr]::AttachThreadInput([SgScr]::GetCurrentThreadId(), $tid, $true)
    [void][SgScr]::SetForegroundWindow($h)
    [void][SgScr]::AttachThreadInput([SgScr]::GetCurrentThreadId(), $tid, $false)
}
Start-Sleep -Milliseconds 300
"client {0}x{1} at {2},{3}; focused={4}" -f $r.R, $r.B, $c.X, $c.Y, ([SgScr]::GetForegroundWindow() -eq $h)
function Grab { $bmp = New-Object System.Drawing.Bitmap($r.R, $r.B); $g = [System.Drawing.Graphics]::FromImage($bmp); $g.CopyFromScreen($c.X, $c.Y, 0, 0, $bmp.Size); $g.Dispose(); return $bmp }
New-Item -ItemType Directory -Force -Path $Out | Out-Null
$parkPt = $Park.Split(',')
[SgScr]::MoveTo($c.X + [int]$parkPt[0], $c.Y + [int]$parkPt[1])
Start-Sleep -Milliseconds 900
$b = Grab
$b.Save((Join-Path $Out 'base.png'), [System.Drawing.Imaging.ImageFormat]::Png)
$b.Dispose()
$i = 0
foreach ($pt in $Pts.Split(';')) {
    if (-not $pt.Trim()) { continue }
    $xy = $pt.Split(',')
    $x = [int]$xy[0]; $y = [int]$xy[1]
    [SgScr]::MoveTo($c.X + [int]$parkPt[0], $c.Y + [int]$parkPt[1])
    Start-Sleep -Milliseconds 120
    [SgScr]::MoveTo($c.X + $x, $c.Y + $y)
    Start-Sleep -Milliseconds $WaitMs
    $b = Grab
    $name = "h{0:d3}.png" -f $i
    $b.Save((Join-Path $Out $name), [System.Drawing.Imaging.ImageFormat]::Png)
    $b.Dispose()
    "h{0:d3} hover {1},{2}" -f $i, $x, $y
    $i++
}
"wrote $i frames + base.png to $Out"