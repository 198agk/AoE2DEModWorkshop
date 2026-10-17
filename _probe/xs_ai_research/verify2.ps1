$D = 'D:\Software\DeepSeek Harness\工作区2\_probe\xs_ai_research'
$u8  = [System.Text.UTF8Encoding]::new($false)
$gbk = [System.Text.Encoding]::GetEncoding(936)

$cur = [System.IO.File]::ReadAllLines("$D\AI_SCRIPTING_AIREF.md", $u8)
$bak = [System.IO.File]::ReadAllLines("$D\AI_SCRIPTING_AIREF.corrupt.bak.md", $u8)

Write-Output "lines: cur=$($cur.Count) bak=$($bak.Count)"

$mism = @()
for ($i = 0; $i -lt $cur.Count; $i++) {
    if ($cur[$i] -ceq $bak[$i]) { continue }
    $recon = $gbk.GetString($u8.GetBytes($cur[$i]))
    if ($recon -cne $bak[$i]) { $mism += $i }
}
Write-Output "re-corruption mismatches: $($mism.Count)"
foreach ($i in $mism) {
    Write-Output ""
    Write-Output "===== L$($i+1) ====="
    Write-Output "  BAK: $($bak[$i])"
    Write-Output "  CUR: $($cur[$i])"
    Write-Output "  SIM: $($gbk.GetString($u8.GetBytes($cur[$i])))"
}
