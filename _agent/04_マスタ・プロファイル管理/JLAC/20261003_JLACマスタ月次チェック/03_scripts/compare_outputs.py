"""2つの確認事項一覧Excel（版違い・実装違い）を比較する。コメント列と値の一致、シート構成を確認する。
使い方: python compare_outputs.py <基準.xlsx> <比較.xlsx> [<基準findings.json> <比較findings.json>]
"""
import sys, json
import openpyxl

sys.stdout.reconfigure(encoding='utf-8')


def sheets(path):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    out = {ws.title: [tuple(r) for r in ws.iter_rows(values_only=True)] for ws in wb.worksheets}
    wb.close()
    return out


def main():
    a, b = sheets(sys.argv[1]), sheets(sys.argv[2])
    print('シート構成 基準:', list(a))
    print('シート構成 比較:', list(b))
    fails = 0
    for name in a:
        if name not in b:
            print('NG シートなし:', name); fails += 1; continue
        ra, rb = a[name], b[name]
        n = max(len(ra), len(rb))
        diff = []
        for i in range(n):
            x = ra[i] if i < len(ra) else ()
            y = rb[i] if i < len(rb) else ()
            w = max(len(x), len(y))
            x = tuple(v if v != '' else None for v in x) + (None,) * (w - len(x))
            y = tuple(v if v != '' else None for v in y) + (None,) * (w - len(y))
            if x != y:
                cols = [j + 1 for j in range(w) if x[j] != y[j]]
                diff.append((i + 1, cols, [(x[j - 1], y[j - 1]) for j in cols[:2]]))
        print(('OK ' if not diff else 'NG ') + f'{name}: 行数 {len(ra)} / {len(rb)}、差異行 {len(diff)}')
        for d in diff[:5]:
            print('   ', d)
        fails += bool(diff)
    if len(sys.argv) > 4:
        fa = json.load(open(sys.argv[3], encoding='utf-8'))['findings']
        fb = json.load(open(sys.argv[4], encoding='utf-8'))['findings']
        key = lambda f: (f['sheet'], f['row'], f['check'], f['msg'], f['known'])
        sa = {key(f) for f in fa if f['level'] == 'strict'}
        sb = {key(f) for f in fb if f['level'] == 'strict'}
        print(f'指摘明細(strict) 基準 {len(sa)} / 比較 {len(sb)}、基準のみ {len(sa - sb)}、比較のみ {len(sb - sa)}')
        for k in list(sa - sb)[:5]: print('   基準のみ', k)
        for k in list(sb - sa)[:5]: print('   比較のみ', k)
        fails += bool(sa ^ sb)
    print('FAIL', fails)
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
