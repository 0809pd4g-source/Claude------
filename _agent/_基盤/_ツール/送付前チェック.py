"""印刷・PDF化・社外送付・格納の前に、Office文書（pptx・docx・xlsx）に残っているものを点検し、必要なら消した送付用コピーを作る。

使い方:
  python _agent/_基盤/_ツール/送付前チェック.py <ファイル> [<ファイル> ...]           # 点検だけ（ファイルは変更しない）
  python _agent/_基盤/_ツール/送付前チェック.py <ファイル> --clean                  # 送付用コピーを作って消す
  python _agent/_基盤/_ツール/送付前チェック.py <ファイル> --clean --out <フォルダ>  # 送付用コピーの置き場所を指定

点検（ファイルをzipとして読むだけ。元ファイルには触らない）:
  FAIL（送る前に必ず対処）: コメント／変更履歴（Word）／非表示スライド（PowerPoint）
  WARN（意図したものか確認）: 作成者・最終更新者・会社名などのプロパティ／スピーカーノート／非表示シート／
                              隠し文字（Word）／変更履歴の記録がオン（Word）／外部ファイルへのリンク／
                              書きかけの目印の文字（【回答案】・TODO・XX・（仮）・○○ など）
--clean（Office本体で開いて保存するので、テーブル・外部データ接続を含むExcelも壊さない）:
  元ファイルは変更せず「<元の名前>_送付用.<拡張子>」を作り、コメント・個人情報・ドキュメントのプロパティを消す。
  変更履歴・非表示スライド・ノート・非表示シートは中身の判断が要るので消さない（点検結果に残る）。
  消したあとに送付用コピーを点検し直し、Office本体で開き直せる（修復を求められない）ことも確かめる。
  安全のため、同じOfficeアプリが起動中のとき、対象ファイルを誰かが開いているとき（~$ファイルがある）は実行しない。

手順の正本: 定常業務マニュアル最新版 Section 11「印刷・PDF化・社外送付の前のチェック」
"""
import os, re, shutil, subprocess, sys, tempfile, zipfile

# 書きかけ・埋め忘れの目印だけ（「要確認」「★宿題」「○×の表」は正規の記載にも使うので対象外）
MARKERS = re.compile(r'【回答案】|TODO|ToDo:|(?<![A-Za-z])(?:XX|xx)(?![A-Za-z])|（仮）|\?\?\?|(?<![○〇])[○〇]{2}(?![○〇])')
APPS = {'.pptx': ('POWERPNT.EXE', 'PowerPoint'), '.docx': ('WINWORD.EXE', 'Word'), '.xlsx': ('EXCEL.EXE', 'Excel')}


def read(z, name):
    try:
        return z.read(name).decode('utf-8', errors='replace')
    except KeyError:
        return ''


def texts(xml):
    return ''.join(re.findall(r'<(?:a|w):t(?:\s[^>]*)?>([^<]*)</(?:a|w):t>', xml))


def check_props(z, out):
    core, app = read(z, 'docProps/core.xml'), read(z, 'docProps/app.xml')
    for tag, label in (('dc:creator', '作成者'), ('cp:lastModifiedBy', '最終更新者')):
        m = re.search(rf'<{tag}>([^<]+)</{tag}>', core)
        if m:
            out.append(('WARN', f'プロパティの{label}が残っている：{m.group(1)}'))
    for tag, label in (('Company', '会社名'), ('Manager', '管理者')):
        m = re.search(rf'<{tag}>([^<]+)</{tag}>', app)
        if m:
            out.append(('WARN', f'プロパティの{label}が残っている：{m.group(1)}'))
    if 'docProps/custom.xml' in z.namelist():
        n = len(re.findall(r'<property ', read(z, 'docProps/custom.xml')))
        if n:
            out.append(('WARN', f'ユーザー設定のプロパティが{n}件ある'))


def check_links(z, out):
    urls = set()
    for name in z.namelist():
        if name.endswith('.rels'):
            for m in re.finditer(r'<Relationship [^>]*>', read(z, name)):
                tag = m.group(0)
                if 'TargetMode="External"' in tag and '/hyperlink"' not in tag:
                    t = re.search(r'Target="([^"]+)"', tag)
                    if t:
                        urls.add(t.group(1))
    for u in sorted(urls):
        out.append(('WARN', f'外部ファイルへのリンク（受け取った人の環境では開けない）：{u}'))


def check_markers(where, text, out, found):
    for m in MARKERS.finditer(text):
        if len(found) >= 10:
            return
        s = text[max(0, m.start() - 15):m.end() + 15].replace('\n', ' ')
        found.append(1)
        out.append(('WARN', f'書きかけの目印「{m.group(0)}」（{where}）：…{s}…'))


def slide_order(z):
    pres, rels = read(z, 'ppt/presentation.xml'), read(z, 'ppt/_rels/presentation.xml.rels')
    rid2t = dict(re.findall(r'Id="(rId\d+)"[^>]*Target="([^"]+)"', rels))
    rid2t.update({a: b for b, a in re.findall(r'Target="([^"]+)"[^>]*Id="(rId\d+)"', rels)})
    order = re.findall(r'<p:sldId [^>]*r:id="(rId\d+)"', pres)
    return ['ppt/' + rid2t[r].lstrip('/').replace('ppt/', '') for r in order if r in rid2t]


def check_pptx(z, out):
    names, found = z.namelist(), []
    ncm = sum(len(re.findall(r'<(?:p:cm|p188:cm)[ >]', read(z, n))) for n in names
              if n.startswith('ppt/comments/'))
    if ncm:
        out.append(('FAIL', f'コメントが{ncm}件ある'))
    for i, s in enumerate(slide_order(z), 1):
        xml = read(z, s)
        if re.search(r'<p:sld [^>]*show="0"', xml):
            out.append(('FAIL', f'スライド{i}が非表示（送るなら削除するか表示に戻す）'))
        check_markers(f'スライド{i}', texts(xml), out, found)
        rel = read(z, s.replace('slides/', 'slides/_rels/') + '.rels')
        m = re.search(r'Target="\.\./notesSlides/([^"]+)"', rel)
        if m:
            note = texts(read(z, 'ppt/notesSlides/' + m.group(1))).strip()
            if note and not re.fullmatch(r'\d+', note):
                out.append(('WARN', f'スライド{i}にノートがある：{note[:40]}'))


def check_docx(z, out):
    names, found = z.namelist(), []
    ncm = len(re.findall(r'<w:comment ', read(z, 'word/comments.xml')))
    if ncm:
        out.append(('FAIL', f'コメントが{ncm}件ある'))
    parts = [n for n in names if re.match(r'word/(document|header\d*|footer\d*|footnotes|endnotes)\.xml$', n)]
    rev = vanish = 0
    for p in parts:
        xml = read(z, p)
        rev += len(re.findall(r'<w:(?:ins|del|moveFrom|moveTo) ', xml)) + len(re.findall(r'<w:(?:rPrChange|pPrChange) ', xml))
        vanish += len(re.findall(r'<w:vanish/>', xml))
        check_markers('本文' if 'document' in p else p.split('/')[-1], texts(xml), out, found)
    if rev:
        out.append(('FAIL', f'変更履歴（承諾・却下していない変更）が{rev}件ある'))
    if vanish:
        out.append(('WARN', f'隠し文字の設定が{vanish}か所ある'))
    if '<w:trackRevisions' in read(z, 'word/settings.xml'):
        out.append(('WARN', '変更履歴の記録がオンのまま（受け取った人の編集も履歴に残る）'))


def check_xlsx(z, out):
    names, found = z.namelist(), []
    ncm = sum(len(re.findall(r'<comment ', read(z, n))) for n in names if re.match(r'xl/comments\d*\.xml$', n))
    nth = sum(len(re.findall(r'<threadedComment ', read(z, n))) for n in names if n.startswith('xl/threadedComments/'))
    if ncm or nth:
        out.append(('FAIL', f'コメント・メモが{max(ncm, nth)}件ある'))
    for m in re.finditer(r'<sheet [^>]*>', read(z, 'xl/workbook.xml')):
        st = re.search(r'state="(hidden|veryHidden)"', m.group(0))
        if st:
            nm = re.search(r'name="([^"]+)"', m.group(0)).group(1)
            out.append(('WARN', f'非表示のシート「{nm}」（{"完全に非表示" if st.group(1) == "veryHidden" else "非表示"}）'))
    if any(n.startswith('xl/externalLinks/') for n in names):
        out.append(('WARN', '他のブックへのリンク（外部参照）がある'))
    check_markers('セルの文字', ' '.join(re.findall(r'<t[^>]*>([^<]*)</t>', read(z, 'xl/sharedStrings.xml'))), out, found)


def check(path):
    ext = os.path.splitext(path)[1].lower()
    out = []
    with zipfile.ZipFile(path) as z:
        {'.pptx': check_pptx, '.docx': check_docx, '.xlsx': check_xlsx}[ext](z, out)
        check_props(z, out)
        check_links(z, out)
    return out


def report(path, out):
    print(f'\n=== {os.path.basename(path)}')
    if not out:
        print('  OK  残っているものは見つからなかった')
    for level, msg in sorted(out, key=lambda x: x[0] != 'FAIL'):
        print(f'  {level}  {msg}')
    nf = sum(1 for l, _ in out if l == 'FAIL')
    print(f'  → FAIL {nf}件 / WARN {len(out) - nf}件')
    return nf


PS = r'''
param([string]$Path, [string]$AppName)
$ErrorActionPreference = 'Stop'
function Try-Remove($doc, $t) { try { $doc.RemoveDocumentInformation($t) } catch { Write-Output "NG RemoveDocumentInformation $t" } }
# 変数名はアプリ名の引数と大文字小文字違いで衝突しないように（PowerShellは区別しない）
$o = $null
try {
  if ($AppName -eq 'Word') {
    $o = New-Object -ComObject Word.Application; $o.Visible = $false; $o.DisplayAlerts = 0
    $d = $o.Documents.Open($Path, $false, $false, $false)
    Try-Remove $d 1; Try-Remove $d 4; Try-Remove $d 8
    $d.Save(); $d.Close($false)
    $d = $o.Documents.Open($Path, $false, $true, $false); $d.Close($false)
  } elseif ($AppName -eq 'Excel') {
    $o = New-Object -ComObject Excel.Application; $o.Visible = $false; $o.DisplayAlerts = $false
    $d = $o.Workbooks.Open($Path, 0, $false)
    Try-Remove $d 1; Try-Remove $d 4; Try-Remove $d 8
    $d.Save(); $d.Close($false)
    $d = $o.Workbooks.Open($Path, 0, $true); $d.Close($false)
  } else {
    $o = New-Object -ComObject PowerPoint.Application
    $d = $o.Presentations.Open($Path, 0, 0, 0)
    Try-Remove $d 1; Try-Remove $d 4; Try-Remove $d 8
    $d.Save(); $d.Close()
    $d = $o.Presentations.Open($Path, -1, 0, 0); $d.Close()
  }
  Write-Output 'DONE'
} catch {
  Write-Output ('ERROR ' + $_.Exception.Message)
} finally {
  if ($o -ne $null) { $o.Quit(); [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($o) }
}
'''


def running(image):
    r = subprocess.run(['tasklist', '/FI', f'IMAGENAME eq {image}', '/NH'], capture_output=True, text=True, errors='replace')
    return image.lower() in r.stdout.lower()


def clean(path, outdir):
    ext = os.path.splitext(path)[1].lower()
    image, app = APPS[ext]
    d, base = os.path.split(os.path.abspath(path))
    if os.path.exists(os.path.join(d, '~$' + base[2:])) or os.path.exists(os.path.join(d, '~$' + base)):
        sys.exit(f'中止：{base} を誰かが開いている（~$ファイルがある）。閉じてから実行してください')
    if running(image):
        sys.exit(f'中止：{app} が起動中です。開いているファイルの未保存の編集を失わないよう、{app} をすべて閉じてから実行してください')
    stem = os.path.splitext(base)[0]
    dst = os.path.join(outdir or d, f'{stem}_送付用{ext}')
    if os.path.exists(dst):
        sys.exit(f'中止：{os.path.basename(dst)} がすでにある（上書きしない）。不要なら削除してから実行してください')
    shutil.copy2(path, dst)
    ps1 = os.path.join(tempfile.gettempdir(), 'send_check_clean.ps1')
    with open(ps1, 'w', encoding='utf-8-sig') as f:
        f.write(PS)
    r = subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', ps1, '-Path', dst, '-AppName', app],
                       capture_output=True, text=True, errors='replace', timeout=300)
    msg = (r.stdout + r.stderr).strip()
    if 'DONE' not in msg:
        print(f'  ⚠️ {app}での処理に失敗：{msg}（作りかけの {os.path.basename(dst)} は削除した）')
        os.remove(dst)
        return None
    for line in msg.splitlines():
        if line.startswith('NG '):
            print(f'  （参考）{line}')
    print(f'\n送付用コピーを作成し、{app}で開き直せることを確認した：{dst}')
    return dst


def main():
    args = sys.argv[1:]
    do_clean = '--clean' in args
    outdir = None
    if '--out' in args:
        i = args.index('--out')
        outdir = args[i + 1]
        del args[i:i + 2]
    files = [a for a in args if not a.startswith('--')]
    if not files:
        sys.exit(__doc__)
    total = 0
    for p in files:
        if os.path.splitext(p)[1].lower() not in APPS:
            print(f'\n=== {p}\n  対象外（pptx・docx・xlsxのみ）')
            continue
        total += report(p, check(p))
        if do_clean:
            dst = clean(p, outdir)
            if dst:
                print('--- 送付用コピーの点検')
                total_after = report(dst, check(dst))
                if total_after:
                    print('  → まだFAILが残っている：中身の判断が要るもの（変更履歴・非表示スライド等）を対処してください')
    sys.exit(1 if total and not do_clean else 0)


if __name__ == '__main__':
    main()
