$enc = [System.Text.Encoding]::GetEncoding(936)
$targets = @{}
foreach ($t in 0xE6C6, 0xE6D5, 0x9225, 0x922B, 0x922E, 0x6402, 0x947E, 0x7D66) { $targets[$t] = $null }
for ($b1 = 0x81; $b1 -le 0xFE; $b1++) {
  for ($b2 = 0x40; $b2 -le 0xFE; $b2++) {
    if ($b2 -eq 0x7F) { continue }
    $s = $enc.GetString([byte[]]@($b1, $b2))
    if ($s.Length -ne 1) { continue }
    $c = [int][char]$s
    if ($targets.ContainsKey($c)) { $targets[$c] = ('{0:X2} {1:X2}' -f $b1, $b2) }
  }
}
foreach ($k in ($targets.Keys | Sort-Object)) {
  $v = $targets[$k]
  if ($null -eq $v) { $v = '(not from a 2-byte GBK code)' }
  Write-Output ("U+{0:X4} <- {1}" -f $k, $v)
}
