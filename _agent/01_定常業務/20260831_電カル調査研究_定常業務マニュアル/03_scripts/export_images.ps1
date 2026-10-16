# HTML版マニュアルに入れる画像を、手元のExcel・PowerPointから書き出す（元のファイルは読み取り専用で開き、保存しない）。
# 使い方（_agent フォルダで）： powershell -ExecutionPolicy Bypass -File 01_定常業務\20260831_電カル調査研究_定常業務マニュアル\03_scripts\export_images.ps1
# 出力：02_output\images\20261016_画像_*_v1.png。素材を差し替えたら、ここのパス・範囲を直して流し直す。
param([string]$Only = '')   # 出力名の一部を指定すると、その画像だけ書き出す（例：-Only JLAC提出）
$ErrorActionPreference = 'Stop'
$agent = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$out = Join-Path $PSScriptRoot '..\02_output\images'
New-Item -ItemType Directory -Force $out | Out-Null
$jlac = Join-Path $agent '04_マスタ・プロファイル管理\JLAC\JLACマスタ月次チェック\202610提出分'
$yaku = Join-Path $agent '04_マスタ・プロファイル管理\薬剤\薬剤関連マスタ月次作成\202610作成分\02_output\20261015_Excelツール作成の証跡_v1'

# 書き出す範囲：ファイル、シート、範囲、出力名、色枠を付ける範囲（任意）
$jobs = @(
  @{ f = Join-Path $jlac '01_input\1006再提出［令和8年9月末頃以降本番環境適用開始］共有項目JLACコードマスタ_202609_20260915.xlsx';
     s = '1006提出_（新旧コード混合リスト）'; r = 'A1:AF4'; n = 'JLAC提出ファイルの列'; mark = @('M1:M4', 'T1:T4'); narrow = $true; hide = $true },
  @{ f = Join-Path $jlac '02_output\20261006_JLACマスタ確認事項一覧_ACN確認用_JLACセンター20261006提出版_v25.xlsx';
     s = 'このファイルの説明'; r = 'A1:B17'; n = 'JLAC_ACN確認用のシート構成'; mark = @() },
  @{ f = Join-Path $yaku '剤形・規格・銘柄不明コードマスタの作成ツール_20261015.xlsx';
     s = '本ツールの利用方法'; r = 'A1:Y79'; n = '薬剤_作成ツールの利用方法'; mark = @() },
  @{ f = Join-Path $yaku '剤形・規格・銘柄不明コードマスタの作成ツール_20261015.xlsx';
     s = 'STEP7_前回分との整合チェック'; r = 'A1:S8'; n = '薬剤_STEP7_前回分との整合チェック'; mark = @('M1:M8') },
  @{ f = Join-Path $yaku '標準マスタＣＳＶ生成用 1.xlsm';
     s = 'メインシート'; r = 'A1:E20'; n = '薬剤_CSV生成ツールのメインシート'; mark = @('B2:B7') }
)

$xl = New-Object -ComObject Excel.Application
$xl.Visible = $false; $xl.DisplayAlerts = $false; $xl.ScreenUpdating = $true
$xl.AutomationSecurity = 3   # マクロは動かさない
try {
  $open = @{}
  foreach ($j in $jobs) {
    if ($Only -and $j.n -notlike "*$Only*") { continue }
    if (-not $open.ContainsKey($j.f)) { $open[$j.f] = $xl.Workbooks.Open($j.f, 0, $true) }
    $ws = $open[$j.f].Worksheets.Item($j.s)
    $ws.Activate()
    $rg = $ws.Range($j.r)
    if ($j.hide) { foreach ($sh in $ws.Shapes) { $sh.Visible = 0 } }   # シートに貼られた付箋などの図形が表に重ならないよう隠す
    if ($j.narrow) {   # 列の多い表：列幅と文字を一時的に縮め、見出しを折り返して全列を1枚に収める
      $rg.Font.Size = 8; $rg.Columns.ColumnWidth = 9; $rg.Rows.Item(1).WrapText = $true
      $rg.Rows.AutoFit() | Out-Null
    }
    foreach ($m in $j.mark) { $b = $ws.Range($m).BorderAround(1, -4138, 3) }   # 太線・赤（保存しないので元は変わらない）
    $rg.CopyPicture(1, 2)   # 画面どおり・ビットマップ
    $co = $ws.ChartObjects().Add(0, 0, $rg.Width, $rg.Height)
    $co.Activate(); Start-Sleep -Milliseconds 400
    $co.Chart.Paste(); Start-Sleep -Milliseconds 400
    $png = Join-Path $out ('20261016_画像_' + $j.n + '_v1.png')
    $co.Chart.Export($png) | Out-Null
    $co.Delete()
    "書き出し: $png"
  }
  foreach ($wb in $open.Values) { $wb.Close($false) }
} finally { $xl.Quit(); [System.Runtime.InteropServices.Marshal]::ReleaseComObject($xl) | Out-Null }

if ($Only -and 'JFAGYポータル周知' -notlike "*$Only*") { return }
# J-FAGYのポータル周知PPT（本田さんOK版）：期間で分ける構成のスライド
$ppt = Join-Path $agent '05_周知広報\20261001_JFAGY周知文案\02_output\20261001_ポータルサイトのレイアウト変更イメージ（JFAGY）_v4.pptx'
$pp = New-Object -ComObject PowerPoint.Application
try {
  $pr = $pp.Presentations.Open($ppt, $true, $true, $false)   # 読み取り専用・無題のコピーとして開く（図形を消しても元に影響しない）・ウィンドウなし
  # スライド1＝ユーザーが直した本田さんOK版。本田さん宛てのRv依頼メモ（「To 本田さん」の図形）は消してから書き出す（保存しない）
  $sl = $pr.Slides.Item(1)
  for ($k = $sl.Shapes.Count; $k -ge 1; $k--) {
    $sh = $sl.Shapes.Item($k)
    if ($sh.HasTextFrame -and $sh.TextFrame.TextRange.Text -like 'To*本田*') { $sh.Delete() }
  }
  $png = Join-Path $out '20261016_画像_JFAGYポータル周知_v1.png'
  $sl.Export($png, 'PNG', 1600, 900)
  "書き出し: $png"
  $pr.Saved = $true; $pr.Close()
} finally { try { $pp.Quit() } catch { }; [System.Runtime.InteropServices.Marshal]::ReleaseComObject($pp) | Out-Null }
