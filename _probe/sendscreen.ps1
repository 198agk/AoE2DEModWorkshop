# Move the pointer with SendInput instead of SetCursorPos.
#
# Why: the game (AoE2DE_s.exe) reads pointer MOVEMENT through the system's input
# stream, not by polling GetCursorPos.  SetCursorPos only relocates the cursor and
# posts no movement event, so the game never learns the pointer moved -- measured:
# hovering the food icon produced 0 changed pixels, while clicking (which DOES go
# through mouse_event) navigated every menu correctly.  SendInput's MOUSEEVENTF_MOVE
# with ABSOLUTE coordinates injects a real movement event.
param([string]$Cmd = 'move', [int]$X = 0, [int]$Y = 0, [int]$WaitMs = 900, [string]$Out = 'C:\Windows\Temp\aoe_shot.png')
Add-Type -AssemblyName System.Drawing
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public class SiScr {
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
    [StructLayout(LayoutKind.Sequential)] public struct INPUT {
        public uint type; public MOUSEINPUT mi; }
    public static void MoveTo(int px, int py) {
        int sw = GetSystemMetrics(78), sh = GetSystemMetrics(79);
        int ax = (int)Math.Round(px * 65535.0 / (sw - 1));
        int ay = (int)Math.Round(py * 65535.0 / (sh - 1));
        INPUT[] inp = new INPUT[1];
        inp[0].type = 0;
        inp[0].mi.dx = ax; inp[0].mi.dy = ay;
        inp[0].mi.dwFlags = 0x0001 | 0x8000;   // MOVE | ABSOLUTE
        inp[0].mi.time = 0;
        SendInput(1, inp, Marshal.SizeOf(typeof(INPUT)));
    }
    public static void Click() {
        INPUT[] d = new INPUT[1];
        d[0].type = 0; d[0].mi.dwFlags = 0x0002;
        SendInput(1, d, Marshal.SizeOf(typeof(INPUT)));
        System.Threading.Thread.Sleep(70);
        INPUT[] u = new INPUT[1];
        u[0].type = 0; u[0].mi.dwFlags = 0x0004;
        SendInput(1, u, Marshal.SizeOf(typeof(INPUT)));
    }
}
"@
[void][SiScr]::SetProcessDpiAwarenessContext([IntPtr](-4))
[void][SiScr]::SetProcessDPIAware()
$p = Get-Process AoE2DE_s -ErrorAction Stop
$h = $p.MainWindowHandle
$r = New-Object SiScr+RECT
[void][SiScr]::GetClientRect($h, [ref]$r)
$c = New-Object SiScr+POINT
[void][SiScr]::ClientToScreen($h, [ref]$c)
function Focus {
    [void][SiScr]::ShowWindow($h, 9)
    [void][SiScr]::BringWindowToTop($h)
    $fg = [SiScr]::GetForegroundWindow()
    if ($fg -ne $h) {
        $tid = [SiScr]::GetWindowThreadProcessId($h, [ref]([uint32]0))
        $cur = [SiScr]::GetCurrentThreadId()
        [void][SiScr]::AttachThreadInput($cur, $tid, $true)
        [void][SiScr]::SetForegroundWindow($h)
        [void][SiScr]::AttachThreadInput($cur, $tid, $false)
    }
    Start-Sleep -Milliseconds 250
    return ([SiScr]::GetForegroundWindow() -eq $h)
}
function Grab { $bmp = New-Object System.Drawing.Bitmap($r.R, $r.B); $g = [System.Drawing.Graphics]::FromImage($bmp); $g.CopyFromScreen($c.X, $c.Y, 0, 0, $bmp.Size); $g.Dispose(); return $bmp }
switch ($Cmd) {
  'move' {
    $ok = Focus
    [void][SiScr]::SetCursorPos(5, 5); Start-Sleep -Milliseconds 200
    $a = Grab
    [SiScr]::MoveTo($c.X + $X, $c.Y + $Y)
    Start-Sleep -Milliseconds $WaitMs
    $b = Grab
    $chg = 0; $n = 0; $minx = 99999; $miny = 99999; $maxx = -1; $maxy = -1
    for ($yy = 0; $yy -lt $b.Height; $yy += 2) {
      for ($xx = 0; $xx -lt $b.Width; $xx += 2) {
        $p1 = $a.GetPixel($xx, $yy); $p2 = $b.GetPixel($xx, $yy)
        $d = [math]::Abs($p1.R - $p2.R) + [math]::Abs($p1.G - $p2.G) + [math]::Abs($p1.B - $p2.B)
        if ($d -gt 24) { $chg++; if ($xx -lt $minx) {$minx=$xx}; if ($yy -lt $miny) {$miny=$yy}; if ($xx -gt $maxx) {$maxx=$xx}; if ($yy -gt $maxy) {$maxy=$yy} }
        $n++
      }
    }
    "moved (SendInput) to client ({0},{1}) = physical ({2},{3}); focused={4}" -f $X, $Y, ($c.X + $X), ($c.Y + $Y), $ok
    "pixels changed >24 over the whole frame: {0}/{1}" -f $chg, $n
    if ($maxx -ge 0) { "change bbox: ({0},{1})-({2},{3})" -f $minx, $miny, $maxx, $maxy }
    $a.Dispose(); $b.Dispose()
  }
  'shot' {
    $b = Grab; $b.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png); $b.Dispose()
    "client {0}x{1} at {2},{3} -> {4}" -f $r.R, $r.B, $c.X, $c.Y, $Out
  }
  'click' {
    $ok = Focus
    [SiScr]::MoveTo($c.X + $X, $c.Y + $Y)
    Start-Sleep -Milliseconds 350
    [SiScr]::Click()
    Start-Sleep -Milliseconds $WaitMs
    "clicked (SendInput) client ({0},{1}) focused={2}" -f $X, $Y, $ok
  }
  default { "unknown -Cmd '$Cmd' (move|shot|click)"; exit 2 }
}