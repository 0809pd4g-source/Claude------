"""薬剤関連マスタ（5種類のCSV）の前月比較・整合チェック。

KT（2026-10-15 黒川さん）で説明された確認（前月版との差分を1件ずつ見る・変更区分・昇順）に、
5種類のCSVのあいだで必ず成り立つ関係（9月公開版で全件成り立つことを確認済み）を加えて機械的に点検する。
作成ツール（Excel）の代わりではなく、作ったCSVを送る前の点検に使う。

使い方:
  python check_yakuzai_master.py --prev <前月公開版CSVのフォルダ> --cur <今月CSVのフォルダ> \
      [--yj-new 14 --yj-change 0] [--out <報告.md>]
  --yj-new / --yj-change … YJコードリスト受領時のメールにある新規件数・変更件数（照合に使う）

今月のフォルダにまだ無いCSVは「未作成」と表示し、ある分だけ点検する。
"""
import argparse
import csv
import glob
import io
import os
import re
import sys
from collections import Counter

# 正式名称（ファイル名の先頭）。並びは送付時の5種類の順
KINDS = [
    ('yj', '個別医薬品コード(YJコード)リスト'),
    ('allergy', '薬剤アレルギー用コードマスタ'),
    ('gcm', '剤形・規格・銘柄不明コードマスタ'),
    ('yjmap', '【参考表】『個別医薬品コード（YJコードリスト）』と『剤形・規格・銘柄不明コードマスタ』との対応表'),
    ('ippan', '【参考表】『一般名処方マスタ』と『剤形・規格・銘柄不明コードマスタ』との対応表'),
]
NAME_RE = re.compile(r'^(?P<base>.+)_(?P<ym>\d{6})_(?P<ymd>\d{8})\.csv$')
SHOW = 30  # 明細を表に出す上限


def find(folder, base):
    """正式名称で始まるCSVを探す（_utf8 などの余計な接尾辞つきも拾い、名前の点検で指摘する）"""
    hits = [p for p in glob.glob(os.path.join(folder, '*.csv')) if os.path.basename(p).startswith(base + '_')]
    exact = [p for p in hits if (m := NAME_RE.match(os.path.basename(p))) and m.group('base') == base]
    pick = exact or hits  # 正式名称どおりのものを優先する
    return sorted(pick)[-1] if pick else None


def load(path):
    raw = open(path, 'rb').read()
    bom = raw.startswith(b'\xef\xbb\xbf')
    try:
        text = raw.decode('utf-8-sig')
    except UnicodeDecodeError:
        return {'path': path, 'error': 'UTF-8として読めない（CSV生成ツールで shift-jis を選んだなど）'}
    rows = list(csv.reader(io.StringIO(text, newline='')))
    first = raw.split(b'\n', 1)[0]
    style = {'CRLF': first.endswith(b'\r'), '全項目を""で囲む': raw.lstrip(b'\xef\xbb\xbf').startswith(b'"')}
    return {'path': path, 'bom': bom, 'style': style, 'head': rows[0], 'rows': rows[1:]}


class Report:
    def __init__(self):
        self.lines, self.summary = [], []

    def item(self, kind, title, status, detail=''):
        self.summary.append((kind, title, status))
        self.lines.append(f'- **{status}** {title}' + (f'：{detail}' if detail else ''))

    def table(self, head, rows):
        if not rows:
            return
        self.lines.append('')
        self.lines.append('| ' + ' | '.join(head) + ' |')
        self.lines.append('|' + '---|' * len(head))
        for r in rows[:SHOW]:
            self.lines.append('| ' + ' | '.join(str(x).replace('|', '／') for x in r) + ' |')
        if len(rows) > SHOW:
            self.lines.append(f'| …ほか{len(rows) - SHOW}件 |' + ' |' * (len(head) - 1))
        self.lines.append('')

    def h(self, text):
        self.lines += ['', f'## {text}', '']


def diff(prev, cur, key=0):
    """キー列で突き合わせ、新規・削除・変更（列名つき）を返す"""
    p = {r[key]: r for r in prev['rows']}
    c = {r[key]: r for r in cur['rows']}
    head = cur['head']
    new = [c[k] for k in c if k not in p]
    gone = [p[k] for k in p if k not in c]
    chg = []
    for k in c:
        if k in p and p[k] != c[k]:
            cols = [head[i] for i in range(min(len(head), len(p[k]), len(c[k]))) if p[k][i] != c[k][i]]
            chg.append((k, cols, p[k], c[k]))
    return new, gone, chg


def check_common(rep, kind, prev, cur, label):
    """どのCSVにも共通：ファイル名・文字コード・見出し・キーの重複"""
    name = os.path.basename(cur['path'])
    m = NAME_RE.match(name)
    base = dict(KINDS)[kind]
    if m and m.group('base') == base:
        rep.item(kind, 'ファイル名が正式名称_YYYYMM_YYYYMMDD.csv', 'OK', name)
    else:
        rep.item(kind, 'ファイル名が正式名称_YYYYMM_YYYYMMDD.csv', 'NG',
                 f'{name}（送付前に「{base}_YYYYMM_YYYYMMDD.csv」に直す。_utf8 などの接尾辞は外す）')
    if prev and cur['bom'] != prev['bom']:
        rep.item(kind, '文字コード（BOMの有無）が前月と同じ', '要確認',
                 f'前月 BOM{"あり" if prev["bom"] else "なし"} → 今月 BOM{"あり" if cur["bom"] else "なし"}')
    else:
        rep.item(kind, '文字コードがUTF-8（BOMの有無も前月と同じ）', 'OK')
    if prev and cur['style'] != prev['style']:
        rep.item(kind, '書式（全項目を""で囲む・改行コードCRLF）が前月と同じ', '要確認', f'前月 {prev["style"]} → 今月 {cur["style"]}')
    elif prev:
        rep.item(kind, '書式（全項目を""で囲む・改行コード）が前月と同じ', 'OK')
    if prev and cur['head'] != prev['head']:
        rep.item(kind, '見出し行が前月と同じ', 'NG', f'前月 {prev["head"]} → 今月 {cur["head"]}')
    else:
        rep.item(kind, '見出し行が前月と同じ', 'OK', '、'.join(cur['head']))
    lens = Counter(len(r) for r in cur['rows'])
    if len(lens) == 1 and list(lens)[0] == len(cur['head']):
        rep.item(kind, '全行の列数が見出しと同じ', 'OK', f'{len(cur["head"])}列')
    else:
        rep.item(kind, '全行の列数が見出しと同じ', 'NG', f'{dict(lens)}（非表示列の消し忘れ・余計な列がないか）')
    keys = Counter(r[0] for r in cur['rows'])
    dup = [k for k, n in keys.items() if n > 1]
    rep.item(kind, f'{label}に重複がない', 'OK' if not dup else 'NG', f'{len(dup)}件 {dup[:10]}' if dup else '')
    if prev:
        rep.item(kind, '行数（前月→今月）', '情報', f'{len(prev["rows"])} → {len(cur["rows"])}（{len(cur["rows"]) - len(prev["rows"]):+d}）')


def check_yjlike(rep, kind, prev, cur, yj_new, yj_change):
    """YJコードリスト・薬剤アレルギー用コードマスタ：KTの確認方法（前月との差分を1件ずつ）"""
    new, gone, chg = diff(prev, cur)
    kcol = cur['head'].index('変更区分')
    ok_new = [r for r in new if r[kcol] == '新規']
    rep.item(kind, '新規の行（前月に無いコード）', '情報', f'{len(new)}件（うち変更区分「新規」{len(ok_new)}件）')
    if yj_new is not None:
        rep.item(kind, 'メールの新規件数と一致', 'OK' if len(new) == yj_new else 'NG', f'メール {yj_new}件／CSV {len(new)}件')
    if len(ok_new) != len(new):
        rep.item(kind, '新規の行の変更区分が「新規」', 'NG', f'{len(new) - len(ok_new)}件が「新規」でない')
    rep.table(['コード', '名称', '会社名', '登録年月日', '変更区分'], [[r[0], r[1], r[2], r[3], r[kcol]] for r in new])
    rep.item(kind, '前月にあって今月無いコード（削除）', 'OK' if not gone else 'NG',
             f'{len(gone)}件（YJコードは除外年月日を入れて残すのが基本。削除はYJコードリストの送り主の連絡を確認）' if gone else '0件')
    rep.table(['コード', '名称'], [[r[0], r[1]] for r in gone])
    # 変更：前月「新規」→今月空欄 は正常（先月の印が消えただけ）
    cleared = [x for x in chg if x[1] == ['変更区分'] and x[2][kcol] in ('新規', '変更') and x[3][kcol] == '']
    real = [x for x in chg if x not in cleared]
    rep.item(kind, '前月の「新規」「変更」の印が今月は空欄になった行', '情報', f'{len(cleared)}件（正常：前月の変更の印が消えただけ）')
    marked = [x for x in real if x[3][kcol] == '変更']
    odd = [x for x in real if x[3][kcol] not in ('', '新規', '変更')]  # 除外などを表す想定外の区分
    unmarked = [x for x in real if x[3][kcol] in ('', '新規')]
    n_change_col = sum(1 for r in cur['rows'] if r[kcol] == '変更')
    rep.item(kind, '内容が変わった行（変更区分「変更」）', '要確認' if marked else 'OK',
             f'{len(marked)}件。何が変わったかを1件ずつ見て、あってしかるべき変更か確認する' if marked else '0件')
    if yj_change is not None:
        rep.item(kind, 'メールの変更件数と一致', 'OK' if n_change_col == yj_change else 'NG',
                 f'メール {yj_change}件／CSVの変更区分「変更」{n_change_col}件')
    if odd:
        rep.item(kind, '変更区分が空欄・新規・変更以外の行', '要確認',
                 f'{len(odd)}件 {sorted({x[3][kcol] for x in odd})}（区分の意味を確認する）')
        rep.table(['コード', '変わった列', '前月', '今月'], [[k, '・'.join(c), p, n] for k, c, p, n in odd])
    rep.table(['コード', '変わった列', '前月', '今月'],
              [[k, '・'.join(c), ' / '.join(p[i] for i in range(len(p)) if cur['head'][i] in c),
                ' / '.join(n[i] for i in range(len(n)) if cur['head'][i] in c)] for k, c, p, n in marked])
    rep.item(kind, '内容が変わったのに変更区分が「変更」でない行', 'OK' if not unmarked else 'NG',
             f'{len(unmarked)}件（特にコード・名称の変更は重大）' if unmarked else '0件')
    rep.table(['コード', '変わった列', '前月', '今月'], [[k, '・'.join(c), p, n] for k, c, p, n in unmarked])


def check_allergy_vs_yj(rep, al, yj):
    bad = []
    for i, (a, y) in enumerate(zip(al['rows'], yj['rows'])):
        if a != ['YCM' + y[0]] + y[1:]:
            bad.append((i + 2, y[0], a[0]))
    if len(al['rows']) != len(yj['rows']):
        bad.append(('行数', len(yj['rows']), len(al['rows'])))
    rep.item('allergy', '全行が「YCM＋YJコード」でYJコードリストと同じ並び・同じ内容', 'OK' if not bad else 'NG',
             f'{len(bad)}件' if bad else f'{len(al["rows"])}行一致')
    rep.table(['行', 'YJ', 'アレルギー'], bad)


def check_gcm(rep, prev, cur):
    rows = cur['rows']
    codes = [r[0] for r in rows]
    rep.item('gcm', 'コードが昇順（KT：最終化後に必ず確認）', 'OK' if codes == sorted(codes) else 'NG',
             '' if codes == sorted(codes) else '「剤形・規格・銘柄不明コード」列で昇順に並べ替えてからCSVにする')
    fmt = [c for c in codes if not re.fullmatch(r'GCM[0-9A-Z]{9}ZZZ', c)]
    rep.item('gcm', 'コードの形（GCM＋9桁＋ZZZ）', 'OK' if not fmt else 'NG', f'{fmt[:10]}' if fmt else '')
    names = Counter(r[1] for r in rows)
    dupn = [n for n, k in names.items() if k > 1]
    rep.item('gcm', '薬剤成分名に重複がない（手順6）', 'OK' if not dupn else 'NG', f'{dupn[:10]}' if dupn else '')
    new, gone, chg = diff(prev, cur)
    kcol = cur['head'].index('変更区分')
    dcol = cur['head'].index('登録年月日')
    bad_new = [r for r in new if r[kcol] != '新規' or not re.fullmatch(r'\d{8}', r[dcol])]
    rep.item('gcm', '新規の行（前月に無いコード）', '要確認' if new else 'OK',
             f'{len(new)}件。YJコードリストの新規から生まれたものか、名称が自然か確認する' if new else '0件')
    rep.table(['コード', '薬剤成分名', '登録年月日', '変更区分'], [[r[0], r[1], r[dcol], r[kcol]] for r in new])
    if bad_new:
        rep.item('gcm', '新規の行に登録年月日（yyyymmdd）と「新規」がある（手順9-e）', 'NG', f'{len(bad_new)}件')
    rep.item('gcm', '前月のコードがすべて残っている（一度付番したコードは消さない）', 'OK' if not gone else 'NG',
             f'{len(gone)}件' if gone else '')
    rep.table(['コード', '薬剤成分名'], [[r[0], r[1]] for r in gone])
    cleared = [x for x in chg if x[1] == ['変更区分'] and x[2][kcol] == '新規' and x[3][kcol] == '']
    real = [x for x in chg if x not in cleared]
    rep.item('gcm', '前月「新規」→今月空欄', '情報', f'{len(cleared)}件（正常：手順9-bで前回分はA〜E列だけ貼るため印が消える）')
    left = [r for r in rows if r[kcol] == '新規' and r[0] not in {x[0] for x in new}]
    if left:
        rep.item('gcm', '前月からある行に「新規」が残っている', 'NG', f'{len(left)}件 {[r[0] for r in left[:10]]}')
    rep.item('gcm', '既存コードの名称・日付などが変わった行', 'OK' if not real else '要確認',
             f'{len(real)}件。名称の変更は付番の踏襲（手順9）が崩れていないか確認する' if real else '0件')
    rep.table(['コード', '変わった列', '前月', '今月'], [[k, '・'.join(c), p, n] for k, c, p, n in real])


def check_yjmap(rep, prev, cur, yj, gcm):
    rows = cur['rows']
    if yj:
        bad = [i + 2 for i, (m, y) in enumerate(zip(rows, yj['rows'])) if m[:3] != y[:3]]
        if len(rows) != len(yj['rows']):
            bad.append('行数が違う')
        rep.item('yjmap', 'YJコード・医薬品名・製造販売会社がYJコードリストと同じ並び・同じ内容', 'OK' if not bad else 'NG',
                 f'{len(bad)}件 行{bad[:10]}' if bad else f'{len(rows)}行一致')
    if gcm:
        g = {r[0]: r[1] for r in gcm['rows']}
        miss = [r for r in rows if r[3] not in g]
        rep.item('yjmap', '剤形・規格・銘柄不明コードがすべてマスタにある', 'OK' if not miss else 'NG', f'{len(miss)}件' if miss else '')
        rep.table(['YJ', 'GCM'], [[r[0], r[3]] for r in miss])
        nm = [r for r in rows if r[3] in g and g[r[3]] != r[4]]
        rep.item('yjmap', '薬剤成分名がマスタの名称と同じ', 'OK' if not nm else 'NG', f'{len(nm)}件' if nm else '')
        rep.table(['YJ', 'GCM', '対応表の名称', 'マスタの名称'], [[r[0], r[3], r[4], g[r[3]]] for r in nm])
        used = {r[3] for r in rows}
        unused = [c for c in g if c not in used]
        rep.item('yjmap', '対応表で使われていないマスタのコード', '情報',
                 f'{len(unused)}件 {unused[:10]}（除外年月日のあるコードなど。前月と同じ顔ぶれなら問題なし）')
    if prev:
        new, gone, chg = diff(prev, cur)
        gchg = [x for x in chg if '剤形・規格・銘柄不明コード' in x[1] or '薬剤成分名(剤形・規格・銘柄不明)' in x[1]]
        other = [x for x in chg if x not in gchg]
        rep.item('yjmap', '既存のYJコードの紐づけ先（GCM）・成分名が変わった行', 'OK' if not gchg else '要確認',
                 f'{len(gchg)}件' if gchg else '0件')
        rep.table(['YJ', '変わった列', '前月', '今月'], [[k, '・'.join(c), p[3:], n[3:]] for k, c, p, n in gchg])
        rep.item('yjmap', 'それ以外の変更（医薬品名・会社名）', '情報', f'{len(other)}件（YJコードリストの「変更」と同じ行なら問題なし）')
        rep.item('yjmap', '新規のYJコードの紐づけ', '要確認' if new else 'OK', f'{len(new)}件。紐づけ先の成分名が自然か確認する' if new else '0件')
        rep.table(['YJ', '医薬品名', 'GCM', '薬剤成分名'], [[r[0], r[1], r[3], r[4]] for r in new])


def check_ippan(rep, prev, cur, gcm):
    rows = cur['rows']
    codes = [r[0] for r in rows]
    rep.item('ippan', '一般名コードが昇順', 'OK' if codes == sorted(codes) else '要確認')
    if gcm:
        g = {r[0]: r[1] for r in gcm['rows']}
        miss = [r for r in rows if r[2] not in g]
        rep.item('ippan', '剤形・規格・銘柄不明コードがすべてマスタにある', 'OK' if not miss else 'NG', f'{len(miss)}件' if miss else '')
        rep.table(['一般名コード', 'GCM'], [[r[0], r[2]] for r in miss])
        nm = [r for r in rows if r[2] in g and g[r[2]] != r[3]]
        rep.item('ippan', '薬剤成分名がマスタの名称と同じ', 'OK' if not nm else 'NG', f'{len(nm)}件' if nm else '')
        rep.table(['一般名コード', 'GCM', '対応表の名称', 'マスタの名称'], [[r[0], r[2], r[3], g[r[2]]] for r in nm])
    if prev:
        new, gone, chg = diff(prev, cur)
        rep.item('ippan', '前月との差', 'OK' if not (new or gone or chg) else '要確認',
                 f'新規{len(new)}・削除{len(gone)}・変更{len(chg)}。差が出るのは主に一般名処方マスタを更新した月か、GCMの成分名が増えた・変わった月（見立て）')
        rep.table(['区分', '一般名コード', '内容'], [['新規', r[0], r[1:]] for r in new] + [['削除', r[0], r[1:]] for r in gone]
                  + [['変更', k, f'{p[1:]} → {n[1:]}'] for k, c, p, n in chg])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--prev', required=True)
    ap.add_argument('--cur', required=True)
    ap.add_argument('--yj-new', type=int)
    ap.add_argument('--yj-change', type=int)
    ap.add_argument('--out')
    a = ap.parse_args()
    prev = {k: (load(p) if (p := find(a.prev, b)) else None) for k, b in KINDS}
    cur = {k: (load(p) if (p := find(a.cur, b)) else None) for k, b in KINDS}
    rep = Report()
    labels = {'yj': 'YJコード', 'allergy': 'コード', 'gcm': 'コード', 'yjmap': 'YJコード', 'ippan': '一般名コード'}
    for k, base in KINDS:
        rep.h(base)
        if not cur[k]:
            rep.item(k, '今月のCSV', '未作成', f'{a.cur} に「{base}_…csv」が無い')
            continue
        if 'error' in cur[k]:
            rep.item(k, os.path.basename(cur[k]['path']), 'NG', cur[k]['error'])
            cur[k] = None
            continue
        if prev[k] and 'error' in prev[k]:
            rep.item(k, '前月のCSV', '要確認', prev[k]['error'])
            prev[k] = None
        if not prev[k]:
            rep.item(k, '前月のCSV', '要確認', f'{a.prev} に前月分が無いため前月比較はしない')
        rep.lines.append(f'今月：`{os.path.basename(cur[k]["path"])}`／前月：`{os.path.basename(prev[k]["path"]) if prev[k] else "なし"}`')
        rep.lines.append('')
        check_common(rep, k, prev[k], cur[k], labels[k])
        if k in ('yj', 'allergy') and prev[k]:
            check_yjlike(rep, k, prev[k], cur[k], a.yj_new if k == 'yj' else None, a.yj_change if k == 'yj' else None)
        if k == 'allergy' and cur['yj']:
            check_allergy_vs_yj(rep, cur[k], cur['yj'])
        if k == 'gcm' and prev[k]:
            check_gcm(rep, prev[k], cur[k])
        if k == 'yjmap':
            check_yjmap(rep, prev[k], cur[k], cur['yj'], cur['gcm'])
        if k == 'ippan':
            check_ippan(rep, prev[k], cur[k], cur['gcm'])
    cnt = Counter(s for _, _, s in rep.summary)
    head = ['# 薬剤関連マスタ チェック結果', '',
            f'- 今月：`{a.cur}`', f'- 前月：`{a.prev}`',
            f'- 結果：NG {cnt["NG"]}件／要確認 {cnt["要確認"]}件／未作成 {cnt["未作成"]}件／OK {cnt["OK"]}件',
            '- 見方：NGは直してから送る。要確認は明細を1件ずつ見て、あってしかるべき変更か判断する（不自然なら本田さんに報告）。情報は判断不要。']
    text = '\n'.join(head + rep.lines) + '\n'
    if a.out:
        open(a.out, 'w', encoding='utf-8').write(text)
    sys.stdout.reconfigure(encoding='utf-8')
    print(f'NG {cnt["NG"]} / 要確認 {cnt["要確認"]} / 未作成 {cnt["未作成"]} / OK {cnt["OK"]}' + (f' → {a.out}' if a.out else ''))
    if not a.out:
        print(text)
    return 1 if cnt['NG'] else 0


if __name__ == '__main__':
    sys.exit(main())
