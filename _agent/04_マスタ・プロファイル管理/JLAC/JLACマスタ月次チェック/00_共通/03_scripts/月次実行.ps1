# JLACマスタ月次チェックの1回実行（入口）。使い方は 00_共通/02_output の「月次実行の使い方」を参照。
#   powershell -ExecutionPolicy Bypass -File 00_共通\03_scripts\月次実行.ps1 -Month 202611提出分 [-Settings <今月の設定.txt>] [-OutDir <出力先>] [-SkipDoublecheck] [-TimeoutMinutes 15]
# 流れ：①設定の点検とツールの実行（monthly_run.mjs run。問題があれば実行せずに止まる）
#       ②ダブルチェックのExcelを作る（make_doublecheck.py --config）
#       ③Excel本体（COM）で全数式を計算して保存（Excelが起動中なら計算しない＝開いているファイルの未保存の編集を失わないため）
#       ④照合の結果を読む（read_doublecheck.py。読み取りだけ）
#       ⑤「月次実行の結果.md」を書く（monthly_run.mjs report）
# 外部への通信はしない。新しいパッケージは使わない（Node標準・Pythonはopenpyxl・ExcelはCOM）。
param(
  [Parameter(Mandatory = $true)][string]$Month,
  [string]$Settings = '',
  [string]$OutDir = '',
  [switch]$SkipDoublecheck,
  [int]$TimeoutMinutes = 15,
  [string]$Carryover = ''
)
# Node・Pythonの標準エラー出力（進み具合の表示）で止まらないよう Continue にし、終了コードで判定する
$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$Scripts = $PSScriptRoot
$Common = Split-Path $Scripts -Parent
$Root = Split-Path $Common -Parent
if (Test-Path -LiteralPath $Month) { $MonthDir = (Resolve-Path -LiteralPath $Month).Path } else { $MonthDir = Join-Path $Root $Month }
if (-not (Test-Path -LiteralPath $MonthDir)) { Write-Host "中止：月フォルダがありません：$MonthDir"; exit 2 }
if ($Settings -eq '') { $Settings = Join-Path $MonthDir '04_reference\今月の設定.txt' }
if ($OutDir -eq '') { $OutDir = Join-Path $MonthDir '02_output' }

foreach ($cmd in @('node', 'python')) {
  if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) { Write-Host "中止：$cmd が見つかりません（Node.js と Python が必要。無いPCではHTML版のツールを使う）"; exit 2 }
}

# ① 設定の点検とツールの実行
Write-Host "① 設定の点検とツールの実行（$([IO.Path]::GetFileName($MonthDir))）"
$runArgs = @("$Scripts\monthly_run.mjs", 'run', '--month', $MonthDir, '--settings', $Settings, '--out', $OutDir)
if ($Carryover -ne '') { $runArgs += @('--carryover', $Carryover) }
$lines = & node @runArgs
$code = $LASTEXITCODE
if ($code -eq 2) { Write-Host '中止：設定の点検で止まりました（上の [止める] を直してから、もう一度実行してください）'; exit 2 }
if ($code -ne 0) { Write-Host "中止：ツールの実行でエラーになりました（終了コード $code）"; exit 1 }
$resLine = $lines | Where-Object { $_ -like 'RESULT *' } | Select-Object -Last 1
$res = $resLine.Substring(7) | ConvertFrom-Json

# ②〜④ ダブルチェック
$dcJson = ''
$dcStatus = ''
if ($SkipDoublecheck) {
  $dcStatus = 'ダブルチェックは作っていない（-SkipDoublecheck を指定）'
} elseif (-not $res.csvPrev) {
  $dcStatus = 'ダブルチェックは作っていない（前月の基準が前月公開CSVでない月。make_doublecheck.py は前月公開CSVだけに対応）'
} else {
  Write-Host '② ダブルチェックのExcelを作る'
  & python "$Scripts\make_doublecheck.py" $res.acn $res.dc --config $res.state
  if ($LASTEXITCODE -ne 0) { $dcStatus = "ダブルチェックのExcelを作れなかった（make_doublecheck.py の終了コード $LASTEXITCODE）" }
  else {
    Write-Host '③ Excel本体で全数式を計算して保存'
    $running = @(Get-Process -Name EXCEL -ErrorAction SilentlyContinue)
    $lock = Join-Path (Split-Path $res.dc -Parent) ('~$' + [IO.Path]::GetFileName($res.dc))
    if ($running.Count -gt 0) {
      $dcStatus = "Excelが起動中（$($running.Count)件）のため計算していない。開いているファイルの未保存の編集を失わないよう、Excelをすべて閉じてから、ダブルチェックのファイルをExcelで開いて計算・保存し、read_doublecheck.py と monthly_run.mjs report を流す（使い方の「Excelが起動中だったとき」）"
      Write-Host "  中止（計算）：$dcStatus"
    } elseif (Test-Path -LiteralPath $lock) {
      $dcStatus = 'ダブルチェックのファイルが開かれている（~$ファイルがある）ため計算していない'
      Write-Host "  中止（計算）：$dcStatus"
    } else {
      $errBefore = @(Get-ChildItem -Path $env:TEMP -Filter 'error*.xml' -ErrorAction SilentlyContinue).Count
      $t0 = Get-Date
      # この処理が起動したExcelのプロセス番号を控える（時間切れのとき、そのExcelだけを止めるため）
      $pidFile = Join-Path $env:TEMP ("jlac_monthly_excel_" + [guid]::NewGuid().ToString() + '.txt')
      $job = Start-Job -ArgumentList $res.dc, $pidFile -ScriptBlock {
        param($p, $pidFile)
        $o = $null
        try {
          $o = New-Object -ComObject Excel.Application
          try {
            Add-Type -Namespace JlacW -Name U -MemberDefinition '[DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint p);'
            $xp = [uint32]0; [void][JlacW.U]::GetWindowThreadProcessId([IntPtr]$o.Hwnd, [ref]$xp); Set-Content -LiteralPath $pidFile -Value $xp
          } catch { }
          $o.Visible = $false; $o.DisplayAlerts = $false
          $wb = $o.Workbooks.Open($p, 0, $false)
          $o.CalculateFull()
          $wb.Save(); $wb.Close($false)
          'DONE'
        } catch { 'ERROR ' + $_.Exception.Message } finally {
          if ($o -ne $null) { $o.Quit(); [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($o) }
        }
      }
      if (Wait-Job $job -Timeout ($TimeoutMinutes * 60)) {
        $msg = (Receive-Job $job) -join ' '
        Remove-Job $job
        $secs = [int]((Get-Date) - $t0).TotalSeconds
        if ($msg -notlike '*DONE*') { $dcStatus = "Excelでの計算に失敗：$msg" }
        else {
          $errAfter = @(Get-ChildItem -Path $env:TEMP -Filter 'error*.xml' -ErrorAction SilentlyContinue).Count
          if ($errAfter -gt $errBefore) { Write-Host '  ⚠️ Excelの修復ログ（%TEMP%\error*.xml）が増えました。ダブルチェックのファイルを開いて確かめてください' }
          Write-Host "  計算・保存しました（$secs 秒）"
          Remove-Item -LiteralPath $pidFile -ErrorAction SilentlyContinue
          Write-Host '④ 照合の結果を読む'
          $dcJson = [IO.Path]::ChangeExtension($res.dc, '.照合.json')
          & python "$Scripts\read_doublecheck.py" $res.dc $dcJson --seconds $secs
          if ($LASTEXITCODE -ne 0) { $dcStatus = '照合の読み取りに失敗'; $dcJson = '' }
        }
      } else {
        Stop-Job $job; Remove-Job $job -Force
        # 止めるのは、この処理が起動したExcel（控えたプロセス番号）だけ。番号が取れなかったときは止めずに案内する
        $xp = if (Test-Path -LiteralPath $pidFile) { (Get-Content -LiteralPath $pidFile | Select-Object -First 1) } else { '' }
        if ($xp -match '^\d+$' -and [int]$xp -gt 0) { Stop-Process -Id ([int]$xp) -Force -ErrorAction SilentlyContinue }
        else { Write-Host '  ⚠️ 計算に使ったExcelのプロセス番号が取れなかったため止めていません。タスクマネージャーで画面の無いExcelを終了してください' }
        $dcStatus = "Excelでの計算が $TimeoutMinutes 分で終わらなかったため止めた。ダブルチェックのファイルをExcelで開いて手で計算・保存してから、read_doublecheck.py と monthly_run.mjs report を流す"
        Write-Host "  中止（計算）：$dcStatus"
      }
    }
  }
}

# ⑤ まとめ
Write-Host '⑤ 月次実行の結果を書く'
$repArgs = @("$Scripts\monthly_run.mjs", 'report', '--state', $res.state)
if ($dcJson -ne '') { $repArgs += @('--dc', $dcJson) }
if ($dcStatus -ne '') { $repArgs += @('--dcstatus', $dcStatus) }
& node @repArgs
if ($LASTEXITCODE -ne 0) { Write-Host '中止：結果のまとめでエラーになりました'; exit 1 }
Write-Host ''
Write-Host "完了：まず「$([IO.Path]::GetFileName($res.summary))」を上から読んでください（$OutDir）"
