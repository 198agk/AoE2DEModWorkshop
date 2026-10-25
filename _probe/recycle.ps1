# Move files and directories to the Recycle Bin.  Nothing is destroyed.
#
# The user was explicit: deletions must be recoverable, and a failed experiment's
# recorded artifacts are not worth protecting.  `Remove-Item` cannot undo itself,
# so this uses the shell's own recycle verb through Microsoft.VisualBasic.
#
# ASCII only, and no Chinese path literals: powershell.exe -File reads a BOM-less
# .ps1 as ANSI, which mangles non-ASCII text and once produced
# "Cannot find path 'D:\Software\AI\<mojibake>'".
param(
    [Parameter(Mandatory = $true)]
    [string]$ListFile,
    [switch]$DryRun
)

Add-Type -AssemblyName Microsoft.VisualBasic

$root = Split-Path -Parent $PSScriptRoot
$moved = 0
$missing = 0

Get-Content -LiteralPath $ListFile -Encoding UTF8 | ForEach-Object {
    $rel = $_.Trim()
    if (-not $rel -or $rel.StartsWith("#")) { return }
    $full = Join-Path $root $rel
    if (-not (Test-Path -LiteralPath $full)) {
        Write-Output ("MISSING  " + $rel)
        $script:missing++
        return
    }
    if ($DryRun) {
        Write-Output ("WOULD    " + $rel)
        return
    }
    try {
        if (Test-Path -LiteralPath $full -PathType Container) {
            [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteDirectory(
                $full,
                [Microsoft.VisualBasic.FileIO.UIOption]::OnlyErrorDialogs,
                [Microsoft.VisualBasic.FileIO.RecycleOption]::SendToRecycleBin)
        } else {
            [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile(
                $full,
                [Microsoft.VisualBasic.FileIO.UIOption]::OnlyErrorDialogs,
                [Microsoft.VisualBasic.FileIO.RecycleOption]::SendToRecycleBin)
        }
        Write-Output ("RECYCLED " + $rel)
        $script:moved++
    } catch {
        Write-Output ("FAILED   " + $rel + "  :: " + $_.Exception.Message)
    }
}

Write-Output ("--- recycled " + $moved + ", missing " + $missing)
