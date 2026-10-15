"""薬剤関連マスタ（5種類のCSV）を、作成ツール（Excel）と同じ処理で自動作成する（内々の効率化用）。

作成ツールの式（2026-09-15版）をそのまま写した。手順の番号はツールの「本ツールの利用方法」と同じ。
  0  基準データ（薬価基準・一般名処方マスタ・例外コード表）に、厚労省の最新版の新しい行を足す
  1-2 YJコードの頭9桁＋ZZZを作り、重複を除いて昇順
  3-4 薬価基準の頭9桁で最初に見つかった行の成分名を付け、頭にGCM
  5  後続品（［…後続…］）の行を除く（エポエチンカッパは除かない）／名称の重複を除く（STEP3）
  6-8 表記の変換：ハイフン削除・ローマ数字→数字・括弧と空白を全角・後続の［…］を除く（STEP5）
     ※「(想定)STEP4」（塩・水和物）はどの出力にも使われていない（式を確認済み）ため行わない
  9  前回の公開版と突き合わせ、一度付けたコードを変えない（STEP7の表：前回11/12/22→残、今回11→追加、今回12/22→削除）
  10-11 YJとの対応表・一般名処方との対応表（成分名でGCMマスタを引く）

使い方:
  python generate_yakuzai_master.py --state <基準データのフォルダ> --yj <今月のYJコードリストCSV> --prev-gcm <前月のGCMマスタCSV> \
      --ym 202610 --ymd 20261015 --date 20261015 --out <出力フォルダ> \
      [--yakka-new <厚労省の薬価基準xlsx>... --yakka-date 20261014] [--ippan-new <厚労省の一般名処方マスタxlsx>]
  --date … 新規のGCMに入れる登録年月日（9月はYJコードリストの日付と同じ 20260915）

出力: 5種類のCSV（公開版と同じ書式）、更新後の基準データ（翌月の --state に使う）、作成ログ.md（判断が要る行の一覧）
"""
import argparse
import csv
import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_yakuzai_master import KINDS  # noqa: E402

ROMAN = [('ⅩⅢ', '１３'), ('Ⅰ', '１'), ('Ⅱ', '２'), ('Ⅲ', '３'), ('Ⅳ', '４'), ('Ⅴ', '５'),
         ('Ⅵ', '６'), ('Ⅶ', '７'), ('Ⅷ', '８'), ('Ⅸ', '９'), ('Ⅹ', '１０')]


def read_csv(path):
    with open(path, encoding='utf-8-sig', newline='') as f:
        r = list(csv.reader(f))
    return r[0], r[1:]


def write_csv(path, head, rows, quote_all=True):
    with open(path, 'w', encoding='utf-8', newline='') as f:
        if quote_all:  # 公開版と同じ：BOMなし・全項目を""で囲む・CRLF
            w = csv.writer(f, quoting=csv.QUOTE_ALL, lineterminator='\r\n')
        else:
            w = csv.writer(f, lineterminator='\n')
        w.writerow(head)
        w.writerows(rows)


# ---- 式の写し -------------------------------------------------------------
def strip_kouzoku(t):
    """=IF(COUNTIF(x,"*後続*"),SUBSTITUTE(x,MID(LEFT(x,FIND("］",x)),FIND("［",x),LEN(x)),""),x)"""
    if '後続' not in t:
        return t
    return strip_bracket(t)


def strip_bracket(t):
    """SUBSTITUTE(x, MID(LEFT(x,FIND("］")), FIND("［"), LEN(x)), "")：最初の［から最初の］までを（すべての出現について）消す"""
    a, b = t.find('［'), t.find('］')
    if a < 0 or b < 0:
        return None  # Excelでは #VALUE!
    part = t[:b + 1][a:]
    return t.replace(part, '') if part else t


def roman(t):
    for x, y in ROMAN:
        t = t.replace(x, y)
    return t


def norm_step3(t):  # STEP3 E〜G
    return t.replace('\xa0', ' ').replace(' ', '　').replace('(', '（').replace(')', '）')


def norm_step5(t):  # STEP5 E〜T（c㎡の置換は無い）
    t = roman(t.replace('－', ''))
    t = t.replace('(', '（').replace(')', '）').replace(' ', '　')
    return strip_kouzoku(t)


def norm_yjmap(t):  # YJとの対応表 AC〜AS
    t = roman(t.replace('－', '').replace('c㎡', '平方センチメートル'))
    if t != 'ドルナーゼ アルファ（遺伝子組換え）':
        t = t.replace('\xa0', ' ').replace(' ', '　')
    t = t.replace('(', '（').replace(')', '）')
    return strip_kouzoku(t)


def norm_ippan(t):  # 一般名処方との対応表 F〜S、例外コード表 F〜S
    t = roman(t.replace('－', '').replace('c㎡', '平方センチメートル'))
    return strip_kouzoku(t)


def keep_last(rows, key):
    """=IF(COUNTIF(下の行,自分)=0,1,0) が1の行＝同じコードの最後の行だけ残す（並びは保つ）"""
    last = {}
    for i, r in enumerate(rows):
        last[key(r)] = i
    return [r for i, r in enumerate(rows) if last[key(r)] == i]


# ---- 手順0：基準データの更新 ---------------------------------------------
def read_mhlw_xlsx(path, ncol):
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.worksheets[0]
    out = []
    for r in ws.iter_rows(min_row=2, values_only=True):
        if r[1]:
            out.append(['' if v is None else str(v) for v in r[:ncol]])
    return out


def update_state(st, a, log):
    if a.yakka_new:
        have = {r[1] for r in st['yakka']}
        add = []
        for p in a.yakka_new:
            for r in read_mhlw_xlsx(p, 4):
                if r[1] not in have:
                    add.append(r + [a.yakka_date or ''])
                    have.add(r[1])
        st['yakka'] += add
        log.append(f'- 手順0-b 薬価基準：{len(add)}件を追加（コード追加日 {a.yakka_date}）')
        for r in add:
            log.append(f'  - {r[1]} {r[2]} {r[3]}')
    if a.ippan_new:
        new = read_mhlw_xlsx(a.ippan_new, 5)
        seen = {tuple(r) for r in st['ippan']}
        add = [r for r in new if tuple(r) not in seen]  # 最下行に貼って「重複の削除」（先にある行が残る）
        st['ippan'] = sorted(st['ippan'] + add, key=lambda r: r[1])  # ※一般名コードを昇順（同じコードは古い順のまま）
        log.append(f'- 手順0-a 一般名処方マスタ：{len(add)}行を追加。⚠️例外コード表は自動で更新していない（厚労省の「例外コード品目対照表」を見て手で足す）')


# ---- 本体 -----------------------------------------------------------------
def build(st, yj_rows, prev_gcm, date, log):
    issues = []
    # 1-2
    zzz = sorted({r[0][:9] + 'ZZZ' for r in yj_rows})
    # 3-4（VLOOKUP：薬価基準の並びで最初の行）
    by9 = {}
    for r in st['yakka']:
        by9.setdefault(r[1][:9] + 'ZZZ', r)
    step2 = {}
    for z in zzz:
        if z not in by9:
            issues.append(f'❌ 手順3：{z} の頭9桁が薬価基準に無い（成分名を付けられない。薬価基準の更新漏れ）')
            continue
        step2[z] = by9[z][2]
    # 5（STEP3）
    s3 = [('GCM' + z, norm_step3(step2[z])) for z in zzz if z in step2]
    names3 = {n for _, n in s3}
    seen, kept = set(), []
    kz = {}
    for code, n in s3:
        dup = n in seen
        seen.add(n)
        kouzoku = ('後続' in n) and ('エポエチンカッパ' not in n)
        if kouzoku:
            base = strip_bracket(n)
            if base is None or base not in names3:
                kz.setdefault(base, []).append((code, n))  # J列 Error：先発品のコードが無い
            continue
        if dup:
            continue
        kept.append((code, n))
    for base, lst in kz.items():
        code, n = sorted(lst)[0]
        if base in {x for _, x in kept}:
            continue
        kept.append((code, n))  # 手順5の但し書き：最も若いコードだけ残し、［後続］はSTEP5で消える
        issues.append(f'⚠️ 手順5-a：先発品のコードが無い後続品 → {code}「{n}」を残した（但し書きどおり。他 {len(lst) - 1}件は除いた）。確認する')
    kept.sort()
    # 6-8（STEP5・STEP6）
    s6 = [(code, norm_step5(n)) for code, n in kept]
    c6 = Counter(n for _, n in s6)
    for code, n in s6:
        if n is None or '後続' in n:
            issues.append(f'❌ STEP6 後続フラグ：{code}「{n}」')
        elif c6[n] > 1:
            issues.append(f'❌ STEP6 名称の重複：{code}「{n}」')
        if re.search('[Ⅰ-Ⅹ]', n or '') or '－' in (n or ''):
            issues.append(f'❌ STEP6 ローマ数字・ハイフンが残った：{code}「{n}」')
    # 9（STEP7）
    rows7 = [r[:5] + ['前回'] for r in prev_gcm] + [[c, n, '', '', '', '今回'] for c, n in s6]
    cnt_cn = Counter(r[0] + r[1] for r in rows7)
    cnt_n = Counter(r[1] for r in rows7)
    cnt_c = Counter(r[0] for r in rows7)
    table = {'前回11': '残', '前回12': '残', '前回22': '残', '今回11': '追加', '今回12': '削除', '今回22': '削除'}
    master = []
    for r in rows7:
        k = f'{r[5]}{cnt_cn[r[0] + r[1]]}{cnt_n[r[1]]}'
        m = table.get(k)
        if m is None:
            issues.append(f'❌ 手順9：表に無い組み合わせ {k}：{r[0]}「{r[1]}」')
            continue
        if m == '追加':
            m = '追加' if cnt_c[r[0]] == 1 else '削除'
        if k == '前回11' and not r[4] and r[1] != 'ドルナーゼ アルファ（遺伝子組換え）':
            # 除外年月日が入っている行と、ツールの式で特別扱いしているドルナーゼ アルファ（半角スペース）は既知なので出さない
            issues.append(f'⚠️ 手順9（前回11）：{r[0]}「{r[1]}」は今回の名称と合わない（名称の表記が変わった・薬価から消えた等）。必要に応じて除外年月日を入れる')
        if m == '残':
            master.append(r[:5] + [''])
        elif m == '追加':
            master.append([r[0], r[1], '', date, '', '新規'])
    master.sort(key=lambda r: r[0])
    gname = {}
    for r in master:
        gname.setdefault(r[1], r[0])
    # 10 YJとの対応表・薬剤アレルギー用
    yjmap, allergy = [], []
    for r in yj_rows:
        z = r[0][:9] + 'ZZZ'
        n = norm_yjmap(step2[z]) if z in step2 else None
        g = gname.get(n)
        if g is None:
            issues.append(f'❌ 手順10：YJ {r[0]} {r[1]} の成分名「{n}」がGCMマスタに無い（#N/A）')
        yjmap.append([r[0], r[1], r[2], g or '#N/A', n or '#N/A'])
        allergy.append(['YCM' + r[0]] + r[1:6])
    # 11 一般名処方との対応表（改修版：重複削除のシートを参照）
    ip = keep_last(st['ippan'], lambda r: r[1])
    ex = keep_last(st['exc'], lambda r: r[1])
    exmap = {}
    for r in ex:
        exmap.setdefault(r[1], norm_ippan(r[3]))
    ippan = []
    for r in ip:
        d = norm_ippan(step2[r[1]]) if r[1] in step2 else None
        if d is None:
            d = exmap.get(r[1])
        c = gname.get(d, '該当なし') if d is not None else '該当なし'
        if c == '該当なし':
            issues.append(f'❌ 手順11：一般名コード {r[1]} {r[2]} の紐づけ先が見つからない（成分名「{d}」）')
        ippan.append([r[1], r[2], c, d if d is not None else '#N/A'])
    return master, yjmap, allergy, ippan, issues


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--state', required=True)
    ap.add_argument('--yj', required=True)
    ap.add_argument('--prev-gcm', required=True)
    ap.add_argument('--ym', required=True)
    ap.add_argument('--ymd', required=True)
    ap.add_argument('--date', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--yakka-new', nargs='*')
    ap.add_argument('--yakka-date')
    ap.add_argument('--ippan-new')
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding='utf-8')
    st = {'yakka': read_csv(os.path.join(a.state, '薬価基準.csv'))[1],
          'ippan': read_csv(os.path.join(a.state, '一般名処方マスタ.csv'))[1],
          'exc': read_csv(os.path.join(a.state, '例外コード表.csv'))[1]}
    yj_head, yj_rows = read_csv(a.yj)
    prev_head, prev_gcm = read_csv(a.prev_gcm)
    log = [f'# 薬剤関連マスタ 自動作成ログ（{a.ym}_{a.ymd}）', '', '## 手順0 基準データの更新', '']
    update_state(st, a, log)
    if len(log) == 4:
        log.append('- 更新なし（--yakka-new・--ippan-new の指定なし）')
    master, yjmap, allergy, ippan, issues = build(st, yj_rows, prev_gcm, a.date, log)
    os.makedirs(a.out, exist_ok=True)
    base = dict(KINDS)
    fn = lambda k: os.path.join(a.out, f'{base[k]}_{a.ym}_{a.ymd}.csv')
    write_csv(fn('yj'), yj_head, yj_rows)
    write_csv(fn('allergy'), ['ＹＣＭ＋ＹＪコード', '医薬品名', '会社名', '登録年月日', '除外年月日', '変更区分'], allergy)
    write_csv(fn('gcm'), ['剤形・規格・銘柄不明コード', '薬剤成分名(剤形・規格・銘柄不明)', '(空欄)', '登録年月日', '除外年月日', '変更区分'], master)
    write_csv(fn('yjmap'), ['ＹＪコード', '医薬品名', '製造販売会社', '剤形・規格・銘柄不明コード', '薬剤成分名(剤形・規格・銘柄不明)'], yjmap)
    write_csv(fn('ippan'), ['一般名コード', '一般名処方の標準的な記載', '剤形・規格・銘柄不明コード', '薬剤成分名(剤形・規格・銘柄不明)'], ippan)
    sd = os.path.join(a.out, '基準データ（翌月用）')
    os.makedirs(sd, exist_ok=True)
    write_csv(os.path.join(sd, '薬価基準.csv'), ['区分', '薬価基準収載医薬品コード', '成分名', '規格', 'コード追加日'], st['yakka'], False)
    write_csv(os.path.join(sd, '一般名処方マスタ.csv'), ['区分', '一般名コード', '一般名処方の標準的な記載', '成分名', '規格'], st['ippan'], False)
    write_csv(os.path.join(sd, '例外コード表.csv'), ['区分', '一般名コード', '一般名処方の標準的な記載', '成分名'], st['exc'], False)
    new = [r for r in master if r[5] == '新規']
    log += ['', '## 結果', '',
            f'- GCMマスタ {len(master)}行（新規 {len(new)}件）・YJとの対応表 {len(yjmap)}行・一般名処方との対応表 {len(ippan)}行',
            '', '## 確認が要る行（❌は直す・⚠️は判断する）', '']
    log += [f'- {x}' for x in issues] or ['- なし']
    if new:
        log += ['', '## 新規のGCM（成分名が自然か確認する）', ''] + [f'- {r[0]} {r[1]}' for r in new]
    open(os.path.join(a.out, '作成ログ.md'), 'w', encoding='utf-8').write('\n'.join(log) + '\n')
    bad = sum(1 for x in issues if x.startswith('❌'))
    print(f'出力：{a.out}  GCM {len(master)}行（新規{len(new)}）／確認 ❌{bad}件・⚠️{len(issues) - bad}件')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
