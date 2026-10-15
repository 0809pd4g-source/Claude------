"""2つの確認事項一覧Excel（版違い・実装違い）を比較する。コメント列と値の一致、シート構成を確認する。
使い方: python compare_outputs.py <基準.xlsx> <比較.xlsx> [<基準findings.json> <比較findings.json>] [--skip "シート名|シート名"] [--replace "v20=v21"]
  - json（run_check.mjs --json の明細）を渡すと、指摘明細（strict）に加えて、全レベルの明細・通知・コメントも比べる
    （2026-10-15〜。v14で通知の不具合を明細とコメントだけの照合で見逃した教訓。指摘明細の basis〔v21〜の判定の根拠〕は比べない）
  - --skip：比べないシート（比較側にだけある新しいシートなど。基準側にあるシートを外すときも使う）
  - --replace：比べる前に両方の文字列で置き換える（版番号の表記など）。「旧=新」を「|」区切りで複数
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
    args, opt = [], {}
    it = iter(sys.argv[1:])
    for a in it:
        if a.startswith('--'):
            opt[a[2:]] = next(it)
        else:
            args.append(a)
    skip = set(filter(None, opt.get('skip', '').split('|')))
    reps = [tuple(x.split('=', 1)) for x in filter(None, opt.get('replace', '').split('|'))]

    def norm(v):
        if v == '':
            return None
        if isinstance(v, str):
            for a, b in reps:
                v = v.replace(a, b)
        return v

    a, b = sheets(args[0]), sheets(args[1])
    print('シート構成 基準:', list(a))
    print('シート構成 比較:', list(b))
    if skip:
        print('比べないシート:', sorted(skip))
    fails = 0
    for name in a:
        if name in skip:
            continue
        if name not in b:
            print('NG シートなし:', name); fails += 1; continue
        ra, rb = a[name], b[name]
        n = max(len(ra), len(rb))
        diff = []
        for i in range(n):
            x = ra[i] if i < len(ra) else ()
            y = rb[i] if i < len(rb) else ()
            w = max(len(x), len(y))
            x = tuple(norm(v) for v in x) + (None,) * (w - len(x))
            y = tuple(norm(v) for v in y) + (None,) * (w - len(y))
            if x != y:
                cols = [j + 1 for j in range(w) if x[j] != y[j]]
                diff.append((i + 1, cols, [(x[j - 1], y[j - 1]) for j in cols[:2]]))
        print(('OK ' if not diff else 'NG ') + f'{name}: 行数 {len(ra)} / {len(rb)}、差異行 {len(diff)}')
        for d in diff[:5]:
            print('   ', d)
        fails += bool(diff)
    extra = [n for n in b if n not in a and n not in skip]
    if extra:
        print('NG 比較側にだけあるシート:', extra); fails += 1
    if len(args) > 3:
        ja = json.load(open(args[2], encoding='utf-8'))
        jb = json.load(open(args[3], encoding='utf-8'))
        fa, fb = ja['findings'], jb['findings']
        key = lambda f: (f['sheet'], f['row'], f['check'], f['msg'], f['known'])
        sa = {key(f) for f in fa if f['level'] == 'strict'}
        sb = {key(f) for f in fb if f['level'] == 'strict'}
        print(f'指摘明細(strict) 基準 {len(sa)} / 比較 {len(sb)}、基準のみ {len(sa - sb)}、比較のみ {len(sb - sa)}')
        for k in list(sa - sb)[:5]: print('   基準のみ', k)
        for k in list(sb - sa)[:5]: print('   比較のみ', k)
        fails += bool(sa ^ sb)
        # 全レベルの明細（basis 以外の項目すべて。並び順も含めて同じか）
        strip = lambda f: json.dumps({k: v for k, v in f.items() if k != 'basis'}, ensure_ascii=False, sort_keys=True)
        la, lb = [strip(f) for f in fa], [strip(f) for f in fb]
        same = la == lb
        print(('OK ' if same else 'NG ') + f'指摘明細(全レベル・根拠以外の全項目・順序) 基準 {len(la)} / 比較 {len(lb)}')
        if not same:
            ca, cb = set(la), set(lb)
            for k in list(ca - cb)[:3]: print('   基準のみ', k[:300])
            for k in list(cb - ca)[:3]: print('   比較のみ', k[:300])
        fails += not same
        na = [(n['level'], n['title'], n['detail']) for n in ja.get('notices', [])]
        nb = [(n['level'], n['title'], n['detail']) for n in jb.get('notices', [])]
        print(('OK ' if na == nb else 'NG ') + f'通知 基準 {len(na)} / 比較 {len(nb)}')
        if na != nb:
            for x in [x for x in na if x not in nb][:3]: print('   基準のみ', x[:2])
            for x in [x for x in nb if x not in na][:3]: print('   比較のみ', x[:2])
        fails += na != nb
        ma, mb = ja.get('comments', {}), jb.get('comments', {})
        print(('OK ' if ma == mb else 'NG ') + f'コメント 基準 {len(ma)}行 / 比較 {len(mb)}行')
        if ma != mb:
            for k in sorted(set(ma) ^ set(mb))[:5]: print('   片方だけ', k)
            for k in [k for k in ma if k in mb and ma[k] != mb[k]][:5]: print('   文面が違う', k)
        fails += ma != mb
    print('FAIL', fails)
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
