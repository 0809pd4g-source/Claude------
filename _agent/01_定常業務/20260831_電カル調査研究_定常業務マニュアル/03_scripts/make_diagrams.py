"""HTML版マニュアルに入れる流れの図（SVG）を作る。

図の中身は、各MDの表（出典は図ごとに書いた）を写したもの。MDを直したら、ここのデータも直して作り直す。
色は class（dg-…）だけで指定し、色そのものは書かない（HTMLに埋め込んだとき、ページのCSS変数で明暗に合わせて色が付く）。

使い方（_agent フォルダで実行）:
  python 01_定常業務/20260831_電カル調査研究_定常業務マニュアル/03_scripts/make_diagrams.py
出力: 02_output/images/ の SVG 4枚
"""
from html import escape
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / '02_output' / 'images'


def svg(w, h, body, name, title):
    mid = f'arr-{name}'
    defs = (f'<defs><marker id="{mid}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
            f'<path d="M0,0 L10,5 L0,10 z" class="dg-arrow"/></marker></defs>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" role="img" aria-label="{escape(title)}">'
            f'<title>{escape(title)}</title>{defs}{body.replace("ARROW", mid)}</svg>\n')


def box(x, y, w, h, cls, lines, first_bold=True):
    """角丸の箱と、複数行の文字（1行目は太字、2行目以降は小さめ）"""
    out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" class="{cls}"/>']
    ty = y + 19
    for i, t in enumerate(lines):
        c = 'dg-b' if (i == 0 and first_bold) else ('dg-t' if i == 0 else 'dg-s')
        out.append(f'<text x="{x + 8}" y="{ty}" class="{c}">{escape(t)}</text>')
        ty += 17 if i == 0 else 15
    return ''.join(out)


def arrow(x1, y1, x2, y2):
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" class="dg-line" marker-end="url(#ARROW)"/>'


def text(x, y, t, cls='dg-s', anchor='start'):
    return f'<text x="{x}" y="{y}" class="{cls}" text-anchor="{anchor}">{escape(t)}</text>'


def legend(x, y):
    items = [('dg-mtg', '会議'), ('dg-work', '作業・締切'), ('dg-box', '社内定例')]
    out = []
    for i, (c, t) in enumerate(items):
        out.append(f'<rect x="{x + i * 110}" y="{y}" width="16" height="12" rx="2" class="{c}"/>')
        out.append(text(x + i * 110 + 22, y + 11, t))
    return ''.join(out)


# ---- #9 1週間の流れ（出典：定常業務マニュアル 1章「週次カレンダー」） ----------------
WEEK = {
    '月': [('dg-mtg', ['10:30 ラップアップ', '先週の三者定例の後続']),
           ('dg-box', ['13:15 昼会']),
           ('dg-mtg', ['13:30 開発進捗連絡会議', '議事メモ→水曜に返送']),
           ('dg-mtg', ['14:00 開発課題検討会', '夕会までにPlanner起票']),
           ('dg-box', ['17:00 夕会']),
           ('dg-work', ['書面開催の週', '資料入手→火曜に読合せ'])],
    '火': [('dg-box', ['13:15 昼会']),
           ('dg-mtg', ['14:15 ONS問合せ会議', '読み合わせ → 会議後に台帳綺麗化']),
           ('dg-mtg', ['15:00 ONS共有会'])],
    '水': [('dg-box', ['13:15 昼会', 'ONS返送日']),
           ('dg-work', ['15:00 議事要旨', '厚労省Rv依頼の締切']),
           ('dg-box', ['17:00 夕会', 'ONS受領日']),
           ('dg-work', ['18:00 議事要旨', '刈り取り'])],
    '木': [('dg-work', ['昼まで WBSスライド', 'TODO・確認事項（8-2）']),
           ('dg-work', ['終日 三者定例', '事前連携（3-3）'])],
    '金': [('dg-mtg', ['10:00 全体WBS確認会']),
           ('dg-box', ['13:15 昼会']),
           ('dg-mtg', ['13:30 三者定例', '→翌週月曜ラップアップ']),
           ('dg-box', ['16:30 夕会（長め）'])],
}


def week():
    W, colw, gap, x0, top, bh, bg = 1000, 188, 10, 12, 48, 50, 8
    body = []
    for i, (d, items) in enumerate(WEEK.items()):
        x = x0 + i * (colw + gap)
        body.append(f'<rect x="{x}" y="8" width="{colw}" height="30" rx="6" class="dg-head"/>')
        body.append(text(x + colw / 2, 28, d + '曜', 'dg-b', 'middle'))
        for k, (c, lines) in enumerate(items):
            body.append(box(x, top + k * (bh + bg), colw, bh, c, lines))
    # 木曜の準備 → 金曜の会議
    xt, xf = x0 + 3 * (colw + gap) + colw, x0 + 4 * (colw + gap)
    body.append(arrow(xt, top + bh / 2, xf, top + bh / 2))
    body.append(arrow(xt, top + (bh + bg) + bh / 2, xf, top + 2 * (bh + bg) + bh / 2))
    H = top + 6 * (bh + bg) + 34
    body.append(legend(x0, H - 22))
    body.append(text(W - 12, H - 12, '月次・不定期の作業は週次カレンダーの下の注記を見る', 'dg-s', 'end'))
    return svg(W, H, ''.join(body), 'week', '1週間の流れ（週次カレンダー）')


# ---- #10 ONSの1週間の流れ（出典：定常業務マニュアル 7章「ONSの1週間の流れ」） -----------
ONS = [('dg-work', ['月・水 受領', '①の新規・更問を②へ転記', '①L列 厚労省確認中', '②M列 ACN回答作成']),
       ('dg-work', ['受領後〜金', '既出か確認・回答案', '区分：読み合せ／方針確認', 'Bは金曜中にRv依頼']),
       ('dg-work', ['月〜火 Rv', '本田さん→向井さん', '読み合わせスクリプト', '（7-2 会議前）']),
       ('dg-mtg', ['火 14:15 会議', 'ONS問合せ会議で', '厚労省と読み合わせ', '（7-2 会議中）']),
       ('dg-work', ['火 会議後', '台帳綺麗化→本田さんRv', '②M列 ONS回答済(日付)', '日付＝連携日（翌水曜）']),
       ('dg-work', ['水 返送', '②の回答を①に転記', '本田さんRv→080スレッド', '①L列 厚労省回答済'])]


def ons():
    W, n, gap, x0, y = 1000, len(ONS), 22, 12, 40
    bw = (W - 2 * x0 - gap * (n - 1)) / n
    body = [text(x0, 24, '台帳①＝基金側（ONSチームとのやり取り）／台帳②＝厚労省側（厚労省内の検討）', 'dg-s')]
    for i, (c, lines) in enumerate(ONS):
        x = x0 + i * (bw + gap)
        body.append(box(x, y, bw, 92, c, lines))
        if i:
            body.append(arrow(x - gap + 2, y + 46, x - 2, y + 46))
    body.append(legend(x0, 150))
    return svg(W, 172, ''.join(body), 'ons', 'ONSの1週間の流れ')


# ---- #11 JLACマスタの月次の流れ（出典：JLACマスタチェック手順 1章「公開までの流れ」・3章・9章） --
JLAC = [  # (列, 段 0=JLACセンター 1=厚労省・ACN, class, 文字)
    (0, 0, 'dg-box', ['N-2月末', '付番委員会で採択']),
    (1, 0, 'dg-box', ['N-1月 第1・2週', 'JSMLのHPで公開する', 'マスタの整備']),
    (2, 0, 'dg-box', ['N-1月 第3・4週', '電カル共有向け', 'マスタの整備']),
    (3, 0, 'dg-mtg', ['N月1日 提出', '電カル共有向け']),
    (4, 1, 'dg-work', ['N月 第1週', '一次チェック（3章）', '本田さんRv→', '7日頃に疑義を連携']),
    (5, 0, 'dg-box', ['N月 第2週', '確認・反映', '（再提出）']),
    (6, 1, 'dg-work', ['N月15日頃 公開', '二次チェック', '最終化で3種類を', '作る（9章）']),
]


def jlac():
    W, cols, x0, lane_x, gap = 1000, 7, 120, 12, 8
    bw = (W - x0 - 12 - gap * (cols - 1)) / cols
    ys = [36, 156]
    body = []
    for k, name in enumerate(['JLACセンター', '厚労省・ACN']):
        body.append(f'<rect x="{lane_x}" y="{ys[k] - 8}" width="{W - 24}" height="108" rx="8" class="dg-head"/>')
        body.append(text(lane_x + 8, ys[k] + 50, name, 'dg-b'))
    pos = []
    for col, lane, c, lines in JLAC:
        x = x0 + col * (bw + gap)
        body.append(box(x, ys[lane] + 4, bw, 84, c, lines))
        pos.append((x, ys[lane] + 4))
    for (xa, ya), (xb, yb) in zip(pos, pos[1:]):
        if ya == yb:
            body.append(arrow(xa + bw, ya + 42, xb, yb + 42))
        else:
            body.append(arrow(xa + bw, ya + 42, xb, yb + 42))
    body.append(text(W - 12, 282, '本手順の担当は「厚労省・ACN」の段（オレンジ）', 'dg-s', 'end'))
    return svg(W, 292, ''.join(body), 'jlac', 'JLACマスタの月次の流れ')


# ---- #12 周知の共通ルールとマスタ別ルール（出典：定常業務マニュアル 8-4 の対応表・8-5） --------
def notice():
    W = 1000
    body = []
    body.append(box(250, 10, 500, 70, 'dg-mtg', ['周知の共通ルール（定常業務マニュアル）',
                                                  '8-4 DX機構への取り込み・ポータル更新の依頼メール',
                                                  '8-5 ポータルの周知文（期間で分ける構成・旧版の扱い）']))
    masters = [('J-FAGY（不定期）', 'J-FAGYマスタ更新手順', '周知する変更の範囲・KB0012085'),
               ('JLAC（月次）', 'JLACマスタチェック手順 9-4', '注記の更新はイレギュラー時のみ'),
               ('薬剤関連（月次）', '薬剤関連マスタ作成手順', '周知の記載なし（要確認）')]
    bw, gap, x0, y = 300, 26, 12 + 9, 130
    for i, (h, doc, note) in enumerate(masters):
        x = x0 + i * (bw + gap)
        body.append(box(x, y, bw, 70, 'dg-box', [h, '個別ルールの正本：' + doc, note]))
        body.append(arrow(500, 80, x + bw / 2, y - 2))
    body.append(text(500, 222, '共通の型を使い、マスタ固有の事情（周知する変更・記事ID・旧版の扱い・実績）は各手順書に書く',
                     'dg-s', 'middle'))
    steps = ['周知PPTを作る', '本田さんRv→OK', '機構へ依頼メール', 'ポータル公開・取り込みを確認']
    sw, sg, sy = 220, 30, 266
    sx0 = (W - (sw * 4 + sg * 3)) / 2
    for i, t in enumerate(steps):
        x = sx0 + i * (sw + sg)
        body.append(box(x, sy, sw, 34, 'dg-work', [f'{i + 1}. {t}']))
        if i:
            body.append(arrow(x - sg + 2, sy + 17, x - 2, sy + 17))
    body.append(text(12, sy - 8, '毎回の流れ（どのマスタも同じ）', 'dg-s'))
    return svg(W, 312, ''.join(body), 'notice', '周知の共通ルールとマスタ別ルール')


def main():
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    OUT.mkdir(parents=True, exist_ok=True)
    for name, f in [('週次の流れ', week), ('ONSの1週間の流れ', ons), ('JLACマスタの月次の流れ', jlac),
                    ('周知の共通ルールとマスタ別ルール', notice)]:
        p = OUT / f'20261016_図_{name}_v1.svg'
        p.write_text(f(), encoding='utf-8')
        print('出力:', p.name)


if __name__ == '__main__':
    main()
