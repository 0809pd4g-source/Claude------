"""前月公開版CSVと今月のYJコードリストから、今月の4種類のCSVの「予測版」を作る（答え合わせ用）。

作成ツール（Excel）で作ったCSVと突き合わせ、違う行だけを人が確かめるために使う。送付物には使わない。
予測できるのは次の範囲だけ（9月公開版で成り立つ関係から）：
  - 薬剤アレルギー用コードマスタ ＝「YCM」＋YJコードリストの各行（全行そのまま予測できる）
  - YJとの対応表 ＝ YJコードリストの医薬品名・会社名 ＋ 前月の紐づけ先。新規YJは、同じ頭9桁の既存YJがあればその紐づけ先
  - 剤形・規格・銘柄不明コードマスタ ＝ 前月の行（変更区分を空欄に）。新規YJで頭9桁が未知のものは予測できない（一覧に出す）
  - 一般名処方との対応表 ＝ 前月と同じ（一般名処方マスタを更新した月・GCMの成分名が増えた/変わった月は外れる）

使い方:
  python make_expected.py --prev <前月公開版フォルダ> --yj <今月のYJコードリストCSV> --ym 202610 --ymd 20261015 --out <出力フォルダ>
  python make_expected.py --compare <予測版フォルダ> <作成したCSVのフォルダ>   … 行単位で違いを出す
"""
import argparse
import csv
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_yakuzai_master import KINDS, find, load  # noqa: E402


def write(path, head, rows):
    with open(path, 'w', encoding='utf-8', newline='') as f:  # 公開版と同じ：BOMなし・全項目を""で囲む・CRLF
        w = csv.writer(f, quoting=csv.QUOTE_ALL, lineterminator='\r\n')
        w.writerow(head)
        w.writerows(rows)


def make(a):
    sys.stdout.reconfigure(encoding="utf-8")
    base = dict(KINDS)
    prev = {k: load(find(a.prev, b)) for k, b in KINDS}
    yj = load(a.yj)
    os.makedirs(a.out, exist_ok=True)
    name = lambda k: os.path.join(a.out, f'{base[k]}_{a.ym}_{a.ymd}.csv')
    notes = []
    # YJコードリスト（受け取ったものを正式名称にしただけ）
    write(name('yj'), yj['head'], yj['rows'])
    # 薬剤アレルギー用
    write(name('allergy'), prev['allergy']['head'], [['YCM' + r[0]] + r[1:] for r in yj['rows']])
    # YJとの対応表
    pm = {r[0]: r for r in prev['yjmap']['rows']}
    by9 = {}
    for r in prev['yjmap']['rows']:
        by9.setdefault(r[0][:9], r)
    gname = {r[0]: r[1] for r in prev['gcm']['rows']}
    rows, unknown = [], []
    for r in yj['rows']:
        src = pm.get(r[0]) or by9.get(r[0][:9])
        if src:
            rows.append(r[:3] + src[3:5])
        else:
            rows.append(r[:3] + ['（予測不可）', '（予測不可）'])
            unknown.append(r)
        if r[0] not in pm and src:
            notes.append(f'新規YJ {r[0]} {r[1]} → 同じ頭9桁の既存の紐づけ先 {src[3]} {src[4]}（予測）')
    write(name('yjmap'), prev['yjmap']['head'], rows)
    # 剤形・規格・銘柄不明コードマスタ
    kcol = prev['gcm']['head'].index('変更区分')
    g = [r[:kcol] + [''] + r[kcol + 1:] for r in prev['gcm']['rows']]
    write(name('gcm'), prev['gcm']['head'], g)
    for r in unknown:
        notes.append(f'新規YJ {r[0]} {r[1]}：頭9桁 {r[0][:9]} が前月に無い → 新しいGCMコード GCM{r[0][:9]}ZZZ が増えるか、同じ成分名の既存GCMにまとまる（手順5・6・9しだい。予測版には入れていない）')
    # 一般名処方との対応表
    write(name('ippan'), prev['ippan']['head'], prev['ippan']['rows'])
    open(os.path.join(a.out, '予測の注記.txt'), 'w', encoding='utf-8').write(
        '\n'.join(notes or ['新規YJなし：一般名処方マスタの更新（手順0-a）も無ければ、ほぼ全行を予測できる（除外年月日を手で入れた行は外れる）']) + '\n')
    print(f'予測版を {a.out} に出力（注記 {len(notes)}件）')


def compare(exp_dir, act_dir):
    sys.stdout.reconfigure(encoding='utf-8')
    total = 0
    for k, b in KINDS:
        e, c = find(exp_dir, b), find(act_dir, b)
        if not e or not c:
            print(f'[{b}] 比較できない（予測版 {"あり" if e else "なし"}／作成版 {"あり" if c else "なし"}）')
            continue
        E, C = load(e), load(c)
        if 'error' in E or 'error' in C:
            print(f'[{b}] 読めない：{E.get("error") or C.get("error")}')
            total += 1
            continue
        diffs = []
        if E['head'] != C['head']:
            diffs.append(('見出し', E['head'], C['head']))
        # 1列目（コード）で突き合わせる。途中に行が入っても、それ以降が全部「違う」にならないように
        ek = {r[0]: r for r in E['rows']}
        ck = {r[0]: r for r in C['rows']}
        for key, r in ek.items():
            if key not in ck:
                diffs.append(('予測のみ', key, r))
            elif r != ck[key]:
                diffs.append(('違う', key, f'予測 {r}\n        作成 {ck[key]}'))
        for key, r in ck.items():
            if key not in ek:
                diffs.append(('作成のみ', key, r))
        order = [r[0] for r in E['rows'] if r[0] in ck] == [r[0] for r in C['rows'] if r[0] in ek]
        raw_same = open(e, 'rb').read() == open(c, 'rb').read()
        cnt = {t: sum(1 for d in diffs if d[0] == t) for t in ('予測のみ', '作成のみ', '違う')}
        print(f'[{b}] 違い {len(diffs)}件 {cnt}・並び順{"同じ" if order else "が違う"}'
              + ('（ファイルのバイト列も一致）' if raw_same else ''))
        for d in diffs[:20]:
            print(f'  {d[0]} {d[1]}  {d[2]}')
        total += len(diffs) + (0 if order else 1)
    return 1 if total else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--prev'); ap.add_argument('--yj'); ap.add_argument('--ym'); ap.add_argument('--ymd'); ap.add_argument('--out')
    ap.add_argument('--compare', nargs=2)
    a = ap.parse_args()
    if a.compare:
        return compare(*a.compare)
    make(a)
    return 0


if __name__ == '__main__':
    sys.exit(main())
