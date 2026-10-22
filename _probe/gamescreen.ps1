# 一个必须 DPI-aware 的屏幕通道：窗口矩形、截屏、光标、点击都在同一套物理坐标里。
#
# 为什么：本项目踩过一次。2560x1440 逻辑 / 3840x2160 物理（150% 缩放）的机器上，
# 非 DPI-aware 进程里 CopyFromScreen 抓的是"逻辑"矩形，而 SetCursorPos 用的却是物理像素，
# 于是"截图看到的按钮"和"实际点到的地方"差 1.5 倍。诊断证据：同一句话在 OCR 里出现在
# (1027,762)，点击后画面不动、hover 也 0 像素变化 —— 不是游戏不吃输入，是点在别处。

param([string]$Cmd = 'rect', [int]$X = 0, [int]$Y = 0, [int]$WaitMs = 600, [string]$Out = 'C:\Windows\Temp\aoe_shot.png', [string]$Key = 'ESC')

Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms
Add-Type @"
using System;
using System.Runtime.InteropServices;
using System.Text;
public class Scr {
  [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
  [DllImport("user32.dll")] public static extern bool SetProcessDpiAwarenessContext(IntPtr ctx);
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
  [DllImport("user32.dll")] public static extern bool GetCursorPos(out POINT p);
  [DllImport("user32.dll")] public static extern void mouse_event(uint f, uint dx, uint dy, uint d, IntPtr e);
  [DllImport("user32.dll")] public static extern void keybd_event(byte vk, byte scan, uint flags, IntPtr extra);
  [DllImport("user32.dll")] public static extern bool GetClientRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool ClientToScreen(IntPtr h, ref POINT p);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll")] public static extern bool BringWindowToTop(IntPtr h);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int cmd);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  [DllImport("user32.dll")] public static extern bool AttachThreadInput(uint a, uint b, bool f);
  [DllImport("kernel32.dll")] public static extern uint GetCurrentThreadId();
  [DllImport("user32.dll")] public static extern int GetWindowTextW(IntPtr h, StringBuilder s, int n);
  public struct POINT { public int X, Y; }
  public struct RECT { public int L, T, R, B; }
}
"@

# --- 第一件事：把自己变成 DPI-aware，之后所有坐标都是物理像素
[void][Scr]::SetProcessDpiAwarenessContext([IntPtr](-4))   # PER_MONITOR_AWARE_V2
[void][Scr]::SetProcessDPIAware()                          # 老系统兜底

$p = Get-Process AoE2DE_s -ErrorAction SilentlyContinue
if (-not $p) { "game not running"; exit 1 }
$h = $p.MainWindowHandle

function ClientRect {
  $cr = New-Object Scr+RECT
  [void][Scr]::GetClientRect($h, [ref]$cr)
  $tl = New-Object Scr+POINT
  $tl.X = 0; $tl.Y = 0
  [void][Scr]::ClientToScreen($h, [ref]$tl)
  return @{ X = $tl.X; Y = $tl.Y; W = $cr.R; H = $cr.B }
}

function Focus {
  [void][Scr]::ShowWindow($h, 9)
  [void][Scr]::BringWindowToTop($h)
  $mine = [Scr]::GetCurrentThreadId(); $theirs = 0
  [void][Scr]::GetWindowThreadProcessId($h, [ref]$theirs)
  [void][Scr]::AttachThreadInput($mine, $theirs, $true)
  [void][Scr]::SetForegroundWindow($h)
  [void][Scr]::AttachThreadInput($mine, $theirs, $false)
  Start-Sleep -Milliseconds 250
  return ([Scr]::GetForegroundWindow() -eq $h)
}

function Grab([int]$gx = -1, [int]$gy = -1, [int]$gw = -1, [int]$gh = -1) {
  $c = ClientRect
  if ($gx -lt 0) { $gx = $c.X; $gy = $c.Y; $gw = $c.W; $gh = $c.H }
  $bmp = New-Object System.Drawing.Bitmap($gw, $gh)
  $g = [System.Drawing.Graphics]::FromImage($bmp)
  $g.CopyFromScreen($gx, $gy, 0, 0, (New-Object System.Drawing.Size($gw, $gh)))
  $g.Dispose()
  return $bmp
}

switch ($Cmd) {
  'rect' {
    $wr = New-Object Scr+RECT
    [void][Scr]::GetWindowRect($h, [ref]$wr)
    $c = ClientRect
    $pt = New-Object Scr+POINT
    [void][Scr]::GetCursorPos([ref]$pt)
    $screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
    "dpi-aware: {0}" -f [Scr]::GetProcessDPIAwareness
    "window rect (physical): {0},{1} .. {2},{3}  ({4}x{5})" -f $wr.L, $wr.T, $wr.R, $wr.B, ($wr.R - $wr.L), ($wr.B - $wr.T)
    "client area (physical): {0},{1}  {2}x{3}" -f $c.X, $c.Y, $c.W, $c.H
    "screen (physical): {0}x{1}" -f $screen.Width, $screen.Height
    "cursor now: {0},{1}" -f $pt.X, $pt.Y
  }
  'shot' {
    $c = ClientRect
    $bmp = Grab
    $bmp.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png)
    "client {0}x{1} at {2},{3} -> {4}" -f $c.W, $c.H, $c.X, $c.Y, $Out
    $bmp.Dispose()
  }
  'click' {
    $c = ClientRect
    $ok = Focus
    "focused: $ok"
    [void][Scr]::SetCursorPos($c.X + $X, $c.Y + $Y)
    Start-Sleep -Milliseconds 180
    [Scr]::mouse_event(0x0002, 0, 0, 0, [IntPtr]::Zero)
    Start-Sleep -Milliseconds 70
    [Scr]::mouse_event(0x0004, 0, 0, 0, [IntPtr]::Zero)
    Start-Sleep -Milliseconds $WaitMs
    $pt = New-Object Scr+POINT
    [void][Scr]::GetCursorPos([ref]$pt)
    "clicked client ({0},{1}) = physical ({2},{3}); cursor reads {4},{5}" -f $X, $Y, ($c.X + $X), ($c.Y + $Y), $pt.X, $pt.Y
  }
  'hover' {
    $c = ClientRect
    $ok = Focus
    [void][Scr]::SetCursorPos(5, 5)
    Start-Sleep -Milliseconds 500
    $a = Grab
    [void][Scr]::SetCursorPos($c.X + $X, $c.Y + $Y)
    Start-Sleep -Milliseconds 900
    $b = Grab
    $chg = 0; $n = 0
    for ($yy = [math]::Max(0, $Y - 40); $yy -lt [math]::Min($c.H, $Y + 40); $yy += 2) {
      for ($xx = [math]::Max(0, $X - 120); $xx -lt [math]::Min($c.W, $X + 120); $xx += 2) {
        $p1 = $a.GetPixel($xx, $yy); $p2 = $b.GetPixel($xx, $yy)
        if (([math]::Abs($p1.R - $p2.R) + [math]::Abs($p1.G - $p2.G) + [math]::Abs($p1.B - $p2.B)) -gt 12) { $chg++ }
        $n++
      }
    }
    "hover at client ({0},{1}) = physical ({2},{3}), focused={4}" -f $X, $Y, ($c.X + $X), ($c.Y + $Y), $ok
    "pixels changed around it: {0}/{1} ({2:P1})" -f $chg, $n, ($chg / [math]::Max(1, $n))
    if ($chg -eq 0) { "VERDICT: the game did not react to the cursor here" } else { "VERDICT: the game saw the cursor" }
    $a.Dispose(); $b.Dispose()
  }
  'key' {
    $ok = Focus
    $codes = @{ 'ESC' = 0x1B; 'ENTER' = 0x0D; 'SPACE' = 0x20; 'TAB' = 0x09; 'F10' = 0x79; 'F1' = 0x70; 'F2' = 0x71; 'F3' = 0x72; 'F4' = 0x73; 'H' = 0x48; 'A' = 0x41; 'B' = 0x42; 'E' = 0x45; 'Q' = 0x51; 'W' = 0x57; 'S' = 0x53; 'D' = 0x44; 'F' = 0x46; 'G' = 0x47; 'C' = 0x43; 'V' = 0x56; 'Z' = 0x5A; 'X' = 0x58; 'PERIOD' = 0xBE; 'COMMA' = 0xBC }
    $vk = $codes[$Key.ToUpper()]
    if (-not $vk) { "usage: -Cmd key -Key H   (known: $($codes.Keys -join ' '))"; exit 2 }
    $a = Grab
    [Scr]::keybd_event([byte]$vk, 0, 0, [IntPtr]::Zero)
    Start-Sleep -Milliseconds 90
    [Scr]::keybd_event([byte]$vk, 0, 2, [IntPtr]::Zero)
    Start-Sleep -Milliseconds $WaitMs
    $b = Grab
    $chg = 0; $n = 0
    for ($yy = 0; $yy -lt $b.Height; $yy += 5) {
      for ($xx = 0; $xx -lt $b.Width; $xx += 5) {
        $p1 = $a.GetPixel($xx, $yy); $p2 = $b.GetPixel($xx, $yy)
        if (([math]::Abs($p1.R - $p2.R) + [math]::Abs($p1.G - $p2.G) + [math]::Abs($p1.B - $p2.B)) -gt 15) { $chg++ }
        $n++
      }
    }
    "focused={0}; after key {4}: {1}/{2} ({3:P2})" -f $ok, $chg, $n, ($chg / [math]::Max(1, $n)), $Key
    $a.Dispose(); $b.Dispose()
  }
  default { "unknown -Cmd '$Cmd' (rect|shot|click|hover|key)"; exit 2 }
}
