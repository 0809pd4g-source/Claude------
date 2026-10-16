# 親を失って止まったままの git.exe を数える・片付ける（2026-10-16）
#
# 使い方:
#   powershell -ExecutionPolicy Bypass -File _agent\_基盤\_ツール\git孤児掃除.ps1          # 数えるだけ（何も止めない）
#   powershell -ExecutionPolicy Bypass -File _agent\_基盤\_ツール\git孤児掃除.ps1 -Apply   # 止める
#
# 止めるのは「起動から -MinMinutes 分（既定10分）以上たち、かつ起動元（親）のプロセスがもう無い git.exe」だけ。
# 親が生きている git（いま動いているセッション・アプリが使っているもの）は止めない。
# .git\index.lock がある（だれかが書き込み中）ときは止めずに終わる。
#
# 背景: Claude のデスクトップアプリが状態確認のために起動した git（status・rev-parse・config など）が、
# セッションが落ちたり再開したりしたときに手放され、1日で200〜300個たまっていた。たまると git や Bash の操作が数分かかるようになる。
param(
  [switch]$Apply,
  [int]$MinMinutes = 10,
  [string]$Repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
)
$ErrorActionPreference = 'Stop'
$now = Get-Date
$all = @(Get-CimInstance Win32_Process -Filter "Name='git.exe'")
$pids = @{}; Get-Process | ForEach-Object { $pids[$_.Id] = $true }
$orphan = @($all | Where-Object { -not $pids.ContainsKey([int]$_.ParentProcessId) -and ($now - $_.CreationDate).TotalMinutes -ge $MinMinutes })
Write-Output ("git.exe {0}個のうち、親が無く{1}分以上たったもの {2}個" -f $all.Count, $MinMinutes, $orphan.Count)
if ($orphan.Count -gt 0) {
  $orphan | ForEach-Object {
    $c = $_.CommandLine -replace '-c\s+\S+', '' -replace '"[^"]*git\.exe"', '' -replace '^\S*git(\.exe)?', ''
    ($c.Trim() -split '\s+' | Select-Object -First 3) -join ' '
  } | Group-Object | Sort-Object Count -Descending | Select-Object -First 5 | ForEach-Object { Write-Output ("  {0,4}  {1}" -f $_.Count, $_.Name) }
}
if (-not $Apply) { Write-Output '（数えただけ。止めるには -Apply）'; exit 0 }
if (Test-Path (Join-Path $Repo '.git\index.lock')) { Write-Output "中止：$Repo\.git\index.lock がある（書き込み中）。時間をおいてやり直す"; exit 1 }
$n = 0
foreach ($p in $orphan) {
  try { Stop-Process -Id $p.ProcessId -Force -ErrorAction Stop; $n++ } catch { }
}
Write-Output ("止めた：{0}個" -f $n)
