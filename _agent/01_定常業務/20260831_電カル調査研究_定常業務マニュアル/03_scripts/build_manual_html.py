"""定常業務マニュアル（MD）と関連の手順書（MD）から、引き継ぎ用の単一HTMLを生成する。

正本は MD。HTML は毎回このスクリプトで作り直す（HTMLを手で直さない）。
外部ライブラリ不要・出力は外部依存なしの単一HTML（画像は base64 で埋め込む）。

使い方（_agent フォルダで実行）:
  python 01_定常業務/20260831_電カル調査研究_定常業務マニュアル/03_scripts/build_manual_html.py <出力.html> [--label <版の表示>]

構成（下の PAGES で定義）:
  - 定常業務マニュアル本体：「## 」の章ごとに1ページ（左ナビに章、表示中の章は節も出す）
  - マスタ業務：1ページに「手作業編／ツール編」のタブ。各タブは1つ以上のMD（ファイル全体、または指定した ## 章だけ）
各MDは「同じ名前の最大の vN」を自動で選ぶ（版の書き換えは不要）。
MD中の画像 ![説明](相対パス) は、そのMDからの相対パスで読み、base64で埋め込む。
"""
import base64
import html
import mimetypes
import re
import sys
from pathlib import Path

AGENT = Path(__file__).resolve().parents[3]          # …/_agent
MANUAL_DIR = AGENT / '01_定常業務/20260831_電カル調査研究_定常業務マニュアル/02_output'
JLAC_TOOL_DIR = AGENT / '04_マスタ・プロファイル管理/JLAC/JLACマスタ月次チェック/00_共通/02_output'

APP_TITLE = '電カル調査研究事業 定常業務マニュアル'

# ---- ページ構成 -------------------------------------------------------------
# doc: (フォルダ, 系統名)  … 系統名は「日付_」と「_vN.md」を除いた名前。最大の vN を使う
# only: そのMDの「## 」見出しのうち、先頭の番号・文字がこれで始まるものだけ載せる（None なら全体）
MANUAL = (MANUAL_DIR, '定常業務マニュアル')
MASTER_PAGES = [
    {'id': 'jlac', 'title': 'JLACマスタ月次チェック', 'tabs': [
        ('手作業編', [(MANUAL_DIR, 'JLACマスタ月次チェック_手作業編', None)]),
        ('ツール編', [(MANUAL_DIR, 'JLACマスタチェック手順', None),
                     (JLAC_TOOL_DIR, '月次実行の使い方', None)]),
    ]},
    {'id': 'yakuzai', 'title': '薬剤関連マスタの作成', 'tabs': [
        # 手作業：Excelの作成ツールでの作業・前月比較の目視確認・送付まで／ツール：自動作成・点検スクリプト・Claude Codeへの依頼
        ('手作業編', [(MANUAL_DIR, '薬剤関連マスタ作成手順',
                      ['1.', '2.', '3.', '4.', '5.', '6-1', '6-2', '7-1', '8.', '9.', '10.'])]),
        ('ツール編', [(MANUAL_DIR, '薬剤関連マスタ作成手順', ['6-3', '6-4', '7-2'])]),
    ]},
    {'id': 'jfagy', 'title': 'J-FAGYの版上げ（不定期）', 'tabs': [
        ('手順', [(MANUAL_DIR, 'J-FAGYマスタ更新手順', None)]),
    ]},
]


def latest(folder, stem):
    best = None
    for p in folder.glob(f'*_{stem}_v*.md'):
        m = re.fullmatch(rf'\d{{8}}_{re.escape(stem)}_v(\d+)\.md', p.name)
        if m and (best is None or int(m.group(1)) > best[0]):
            best = (int(m.group(1)), p)
    if not best:
        sys.exit(f'見つからない: {folder}/*_{stem}_vN.md')
    return best[1]


# ---- 文書どうしのリンク ------------------------------------------------------
DOC_LINKS = {}   # 系統名 -> ページID（`…_vN.md` の参照をページへのリンクにする）


def link_docs(code_text):
    m = re.search(r'\d{8}_(.+?)_v(?:N|\d+)\.md', code_text)
    if m and m.group(1) in DOC_LINKS:
        return f'<a class="doclink" href="#{DOC_LINKS[m.group(1)]}"><code>{code_text}</code></a>'
    return f'<code>{code_text}</code>'


# ---- Markdown → HTML（このマニュアルで使う書式だけ） ------------------------
class Ctx:
    def __init__(self, base_dir, prefix):
        self.base_dir, self.prefix, self.n = base_dir, prefix, 0
        self.heads = []          # (level, id, text)

    def hid(self):
        self.n += 1
        return f'{self.prefix}-h{self.n}'


def inline(t, ctx):
    codes = []

    def keep(m):
        codes.append(html.escape(m.group(1), quote=False))
        return f'\x00{len(codes) - 1}\x00'
    t = re.sub(r'`([^`]+)`', keep, t)
    imgs = []

    def img(m):
        imgs.append((m.group(1), m.group(2)))
        return f'\x01{len(imgs) - 1}\x01'
    t = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', img, t)
    t = html.escape(t, quote=False)
    t = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', t)
    t = re.sub(r'\[([^\]]+)\]\((https?://[^)\s]+)\)', r'<a href="\2" target="_blank" rel="noopener">\1</a>', t)
    t = re.sub(r'(?<![">=])(https?://[^\s<）)」、]+)', r'<a href="\1" target="_blank" rel="noopener">\1</a>', t)
    t = re.sub(r'\x00(\d+)\x00', lambda m: link_docs(codes[int(m.group(1))]), t)
    t = re.sub(r'\x01(\d+)\x01', lambda m: embed_img(*imgs[int(m.group(1))], ctx), t)
    return t


def embed_img(alt, rel, ctx):
    p = (ctx.base_dir / rel).resolve()
    if not p.exists():
        return f'<span class="warn">［画像が見つからない：{html.escape(rel)}］</span>'
    if p.suffix.lower() == '.svg':
        # 図（SVG）はそのまま埋め込む：ページのCSS変数（明暗）で色が付くように、図の色は class（dg-…）で指定する
        svg = re.sub(r'^\s*<\?xml[^>]*\?>\s*', '', p.read_text(encoding='utf-8'))
        return f'<figure class="diagram">{svg}<figcaption>{html.escape(alt)}</figcaption></figure>'
    mime = mimetypes.guess_type(p.name)[0] or 'image/png'
    data = p.read_bytes()
    b64 = base64.b64encode(data).decode()
    # 横長の画像（幅1800px超のPNG。Excelの横に長い表など）は縮めずに横スクロールで見せる（縮めると字が読めない）
    wide = mime == 'image/png' and data[:8] == b'\x89PNG\r\n\x1a\n' and int.from_bytes(data[16:20], 'big') > 1800
    cls = ' class="wide"' if wide else ''
    return (f'<figure{cls}><img src="data:{mime};base64,{b64}" alt="{html.escape(alt)}" loading="lazy">'
            f'<figcaption>{html.escape(alt)}</figcaption></figure>')


LIST_RE = re.compile(r'^(\s*)([-*]|\d+\.)\s+(.*)$')


def render(lines, ctx, shift=0):
    out, i = [], 0
    while i < len(lines):
        line = lines[i]
        s = line.strip()
        if not s:
            i += 1
            continue
        if s.startswith('```'):
            buf = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith('```'):
                buf.append(lines[i])
                i += 1
            i += 1
            out.append(f'<pre><code>{html.escape(chr(10).join(buf), quote=False)}</code></pre>')
            continue
        m = re.match(r'^(#{1,6})\s+(.*)$', s)
        if m:
            lv = len(m.group(1))
            hid = ctx.hid()
            ctx.heads.append((lv, hid, m.group(2)))
            tag = min(lv + shift, 6)
            out.append(f'<h{tag} id="{hid}">{inline(m.group(2), ctx)}</h{tag}>')
            i += 1
            continue
        if re.fullmatch(r'-{3,}|\*{3,}', s):
            out.append('<hr>')
            i += 1
            continue
        if s.startswith('|'):
            rows = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                rows.append(lines[i].strip())
                i += 1
            out.append(table(rows, ctx))
            continue
        if s.startswith('>'):
            buf = []
            while i < len(lines) and lines[i].strip().startswith('>'):
                buf.append(re.sub(r'^\s*>\s?', '', lines[i]))
                i += 1
            cls = ' class="caution"' if any('⚠' in b for b in buf) else ''
            out.append(f'<blockquote{cls}>{render(buf, ctx, shift)}</blockquote>')
            continue
        if LIST_RE.match(line):
            items = []
            while i < len(lines):
                l = lines[i]
                if not l.strip():
                    # 空行の後も同じリストが続くなら続ける
                    if i + 1 < len(lines) and LIST_RE.match(lines[i + 1]):
                        i += 1
                        continue
                    break
                m2 = LIST_RE.match(l)
                if m2:
                    items.append([len(m2.group(1).expandtabs(4)), m2.group(2), m2.group(3)])
                elif l.startswith(' ') and items:
                    items[-1][2] += '\n' + l.strip()
                else:
                    break
                i += 1
            out.append(listhtml(items, ctx))
            continue
        buf = []
        while i < len(lines) and lines[i].strip() and not re.match(r'^(#{1,6}\s|```|\||>)', lines[i].strip()) \
                and not LIST_RE.match(lines[i]):
            buf.append(lines[i].strip())
            i += 1
        if len(buf) == 1 and re.fullmatch(r'!\[[^\]]*\]\([^)]+\)', buf[0]):
            out.append(inline(buf[0], ctx))   # 画像だけの段落は <p> で包まない（figure は p の中に置けない）
        else:
            out.append(f'<p>{"<br>".join(inline(b, ctx) for b in buf)}</p>')
    return '\n'.join(out)


def item_body(text, ctx):
    """箇条書き1項目の中身。字下げした引用（> …）は入れ子の引用にする"""
    out, quote = [], []

    def flush():
        if quote:
            cls = ' class="caution"' if any('⚠' in q for q in quote) else ''
            out.append(f'<blockquote{cls}>' + '<br>'.join(inline(q, ctx) for q in quote) + '</blockquote>')
            quote.clear()
    for t in text.split('\n'):
        if t.startswith('>'):
            quote.append(re.sub(r'^>\s?', '', t))
        else:
            flush()
            out.append(('<br>' if out and not out[-1].endswith('</blockquote>') else '') + inline(t, ctx))
    flush()
    return ''.join(out)


def listhtml(items, ctx):
    out, stack = [], []
    for ind, mark, text in items:
        tag = 'ol' if mark[0].isdigit() else 'ul'
        while stack and ind < stack[-1][0]:
            out.append(f'</li></{stack.pop()[1]}>')
        if stack and ind == stack[-1][0] and tag != stack[-1][1]:
            out.append(f'</li></{stack.pop()[1]}>')   # 同じ字下げで番号付き⇔「-」が変わったら別のリスト
        if not stack or ind > stack[-1][0]:
            start = f' start="{mark[:-1]}"' if tag == 'ol' and mark[:-1] != '1' else ''
            out.append(f'<{tag}{start}>')
            stack.append((ind, tag))
        else:
            out.append('</li>')
        cb = ''
        mm = re.match(r'^\[( |x)\]\s*(.*)$', text, re.S)
        if mm:
            cb = '<span class="cb">' + ('☑' if mm.group(1) == 'x' else '☐') + '</span> '
            text = mm.group(2)
        out.append('<li>' + cb + item_body(text, ctx))
    while stack:
        out.append(f'</li></{stack.pop()[1]}>')
    return ''.join(out)


def table(rows, ctx):
    def cells(r):
        # `\|` と、コード（`…`）の中の | では列を割らない
        r = r.replace('\\|', '\x02')
        r = re.sub(r'`[^`]*`', lambda m: m.group(0).replace('|', '\x02'), r)
        r = r.strip().strip('|')
        return [c.strip().replace('\x02', '|') for c in r.split('|')]
    head = cells(rows[0])
    body = [cells(r) for r in rows[2:]] if len(rows) > 1 and re.fullmatch(r'[|\s:-]+', rows[1]) else [cells(r) for r in rows[1:]]
    h = ''.join(f'<th>{inline(c, ctx)}</th>' for c in head)
    b = ''.join('<tr>' + ''.join(f'<td>{inline(c, ctx)}</td>' for c in r) + '</tr>' for r in body)
    return f'<div class="tw"><table><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table></div>'


def split_h2(text):
    """(前書き, [(見出し, 本文行)]) に分ける。コードブロック内の # は見出しにしない"""
    pre, secs, cur, fence = [], [], None, False
    for line in text.splitlines():
        if line.strip().startswith('```'):
            fence = not fence
        if not fence and line.startswith('## '):
            cur = (line[3:].strip(), [])
            secs.append(cur)
            continue
        (cur[1] if cur else pre).append(line)
    return pre, secs


def is_log(title):
    """「やったこと・やっていないこと」の章（番号付きも）。改訂の記録はMDにだけ残す"""
    return re.sub(r'^\d+\.\s*', '', title).startswith('やったこと')


def pick(secs, only):
    """only の指定で章・節を選ぶ。'6.' は ## 6 の全体、'6-1' は ## 6 の前置き＋### 6-1 だけ"""
    if only is None:
        return [s for s in secs if not is_log(s[0])]
    chosen = []
    for title, lines in secs:
        if is_log(title):
            continue
        num = re.match(r'(\d+)\.', title)
        n = num.group(1) if num else None
        if any(title.startswith(o) for o in only if o.endswith('.')):
            chosen.append((title, lines))
            continue
        subs = [o for o in only if n and o.startswith(n + '-')]
        if not subs:
            continue
        keep, on, fence = [], True, False
        for l in lines:
            if l.strip().startswith('```'):
                fence = not fence
            if not fence and l.startswith('### '):
                on = any(l[4:].startswith(o) for o in subs)
            if on:
                keep.append(l)
        chosen.append((title, keep))
    return chosen


def h1_of(lines):
    for l in lines:
        if l.startswith('# '):
            return l[2:].strip()
    return ''


# ---- 組み立て ---------------------------------------------------------------
def build(label):
    pages, nav = [], []
    sources = []
    man = latest(*MANUAL)
    sources.append(man)
    DOC_LINKS['定常業務マニュアル'] = 'p-top'
    for mp in MASTER_PAGES:
        for _, docs in mp['tabs']:
            for folder, stem, only in docs:
                DOC_LINKS.setdefault(stem, f'p-{mp["id"]}')

    # 本体：前書き＝表紙、## ごとに1ページ
    pre, secs = split_h2(man.read_text(encoding='utf-8'))
    ctx = Ctx(man.parent, 'top')
    body = [l for l in pre if not l.startswith('# ')]
    pages.append(('p-top', 'はじめに', f'<h2>はじめに</h2>{render(body, ctx)}{start_cards()}', []))
    nav.append(('本体', [('p-top', 'はじめに', [])]))
    group = []
    for n, (title, lines) in enumerate(secs, 1):
        if is_log(title):
            continue
        num = re.match(r'(\d+)\.', title)
        pid = f'p-m{num.group(1)}' if num else f'p-x{n}'   # 章番号から付ける（「1.」→ p-m1）
        ctx = Ctx(man.parent, pid)
        content = render(lines, ctx)
        subs = [(hid, t) for lv, hid, t in ctx.heads if lv == 3]
        pages.append((pid, title, f'<h2>{inline(title, ctx)}</h2>{content}', subs))
        group.append((pid, title, subs))
    nav.append(('定常業務マニュアル', group))

    # マスタ業務：タブ
    group = []
    for mp in MASTER_PAGES:
        pid = f'p-{mp["id"]}'
        tabs_btn, tabs_body = [], []
        for k, (tname, docs) in enumerate(mp['tabs']):
            parts = []
            for folder, stem, only in docs:
                p = latest(folder, stem)
                if p not in sources:
                    sources.append(p)
                text = p.read_text(encoding='utf-8')
                pre2, secs2 = split_h2(text)
                ctx = Ctx(p.parent, f'{pid}-t{k}-{len(parts)}')
                chosen = pick(secs2, only)
                lines = []
                if k == 0 or only is None:   # 前書き（対象・作業フォルダ等）は最初のタブには必ず付ける
                    lines += [l for l in pre2 if not l.startswith('# ')]
                for t, ls in chosen:
                    lines += ['## ' + t] + ls
                parts.append(f'<div class="srcdoc"><div class="srcname">{html.escape(h1_of(pre2) or stem)}'
                             f'<span class="fname">{html.escape(p.name)}</span></div>{render(lines, ctx, shift=1)}</div>')
            sel = 'true' if k == 0 else 'false'
            tabs_btn.append(f'<button type="button" role="tab" aria-selected="{sel}" data-tab="{pid}-tab{k}">{tname}</button>')
            tabs_body.append(f'<div class="tabpanel" id="{pid}-tab{k}"{"" if k == 0 else " hidden"}>{"".join(parts)}</div>')
        tabbar = f'<div class="tabs" role="tablist">{"".join(tabs_btn)}</div>' if len(tabs_btn) > 1 else ''
        pages.append((pid, mp['title'], f'<h2>{html.escape(mp["title"])}</h2>{tabbar}{"".join(tabs_body)}', []))
        group.append((pid, mp['title'], []))
    nav.append(('マスタ業務（手作業編／ツール編）', group))
    return pages, nav, sources


def start_cards():
    items = [('p-m1', '業務一覧と週次カレンダー', 'いつ・何を・どこを見るか'),
             ('p-jlac', 'JLACマスタ月次チェック', '手作業編とツール編'),
             ('p-yakuzai', '薬剤関連マスタの作成', '手作業編とツール編'),
             ('p-jfagy', 'J-FAGYの版上げ', '不定期・周知まで')]
    return '<h3>まず見るところ</h3><div class="cards">' + ''.join(
        f'<a class="card" href="#{i}"><b>{html.escape(t)}</b><span>{html.escape(d)}</span></a>' for i, t, d in items) + '</div>'


CSS = """
:root{--bg:#ffffff;--fg:#1f2328;--muted:#59636e;--line:#d1d9e0;--side:#f6f8fa;--accent:#0b5cad;--accent-bg:#e6f0fb;
--code-bg:#eff2f5;--th-bg:#f0f3f6;--warn-bg:#fff6e0;--warn-line:#d4a72c;--hit:#fff1a8;--card:#ffffff;--shadow:rgba(0,0,0,.08)}
[data-theme=dark]{--bg:#0f1419;--fg:#e6edf3;--muted:#9aa5b1;--line:#30363d;--side:#161b22;--accent:#6cb6ff;--accent-bg:#1c2b3d;
--code-bg:#1f262e;--th-bg:#1a2129;--warn-bg:#2e2611;--warn-line:#a27c1c;--hit:#5a4a00;--card:#161b22;--shadow:rgba(0,0,0,.4)}
*{box-sizing:border-box}
body{margin:0;font-family:"Yu Gothic UI","Meiryo",system-ui,sans-serif;font-size:15px;line-height:1.75;color:var(--fg);background:var(--bg)}
header{position:sticky;top:0;z-index:5;display:flex;gap:12px;align-items:center;padding:8px 16px;background:var(--side);border-bottom:1px solid var(--line)}
header h1{font-size:16px;margin:0;flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
header .ver{font-size:12px;color:var(--muted);white-space:nowrap}
#q{width:260px;padding:5px 9px;border:1px solid var(--line);border-radius:6px;background:var(--bg);color:var(--fg)}
button{font:inherit;cursor:pointer;color:var(--fg);background:var(--bg);border:1px solid var(--line);border-radius:6px;padding:3px 10px}
.wrap{display:flex;min-height:calc(100vh - 46px)}
nav{width:290px;flex:none;background:var(--side);border-right:1px solid var(--line);padding:10px 8px 40px;position:sticky;top:46px;height:calc(100vh - 46px);overflow:auto;font-size:14px}
nav .grp{font-size:12px;color:var(--muted);margin:14px 8px 4px;font-weight:bold}
nav a{display:block;padding:3px 8px;border-radius:5px;color:var(--fg);text-decoration:none}
nav a:hover{background:var(--accent-bg)}
nav a.on{background:var(--accent-bg);color:var(--accent);font-weight:bold}
nav .subs{display:none;margin-left:10px;border-left:2px solid var(--line)}
nav .subs a{font-size:13px;color:var(--muted)}
nav li.open .subs{display:block}
nav ul{list-style:none;margin:0;padding:0}
main{flex:1;min-width:0;padding:16px 32px 80px;max-width:1100px}
main h2,main h3,main h4,main h5{scroll-margin-top:56px}
main h2{font-size:22px;border-bottom:2px solid var(--accent);padding-bottom:4px}
main h3{font-size:18px;margin-top:28px;border-left:4px solid var(--accent);padding-left:8px}
main h4{font-size:16px;margin-top:20px}
main h5{font-size:15px;margin-top:16px;color:var(--accent)}
a{color:var(--accent);overflow-wrap:anywhere}
code{background:var(--code-bg);padding:1px 4px;border-radius:4px;font-size:.9em;word-break:break-all}
pre{background:var(--code-bg);padding:10px;border-radius:6px;overflow:auto}
pre code{padding:0;background:none;word-break:normal}
.tw{overflow-x:auto;margin:10px 0}
table{border-collapse:collapse;font-size:14px}
th,td{border:1px solid var(--line);padding:5px 8px;vertical-align:top}
th{background:var(--th-bg);text-align:left}
blockquote{margin:10px 0;padding:6px 12px;border-left:4px solid var(--line);color:var(--fg);background:var(--side)}
blockquote.caution{border-left-color:var(--warn-line);background:var(--warn-bg)}
.cb{color:var(--muted)}
.tabs{display:flex;gap:6px;margin:12px 0;border-bottom:1px solid var(--line)}
.tabs button{border-bottom:none;border-radius:6px 6px 0 0;padding:6px 18px}
.tabs button[aria-selected=true]{background:var(--accent-bg);color:var(--accent);font-weight:bold;border-color:var(--accent)}
.srcdoc{margin-bottom:36px}
.srcname{font-size:13px;color:var(--muted);border:1px dashed var(--line);border-radius:6px;padding:4px 10px;display:flex;gap:10px;flex-wrap:wrap}
.srcname .fname{font-family:monospace}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:12px}
.card{display:flex;flex-direction:column;padding:12px;border:1px solid var(--line);border-radius:8px;background:var(--card);box-shadow:0 1px 3px var(--shadow);text-decoration:none;color:var(--fg)}
.card span{font-size:13px;color:var(--muted)}
figure{margin:12px 0}
figure.diagram{overflow-x:auto}
figure.diagram svg{display:block;min-width:720px;max-width:100%;height:auto}
.dg-box{fill:var(--card);stroke:var(--line)}
.dg-mtg{fill:var(--accent-bg);stroke:var(--accent)}
.dg-work{fill:var(--warn-bg);stroke:var(--warn-line)}
.dg-head{fill:var(--th-bg);stroke:var(--line)}
.dg-t{fill:var(--fg);font-size:13px}
.dg-b{fill:var(--fg);font-size:13px;font-weight:bold}
.dg-s{fill:var(--muted);font-size:11px}
.dg-line{stroke:var(--muted);stroke-width:1.5;fill:none}
.dg-arrow{fill:var(--muted)}
figure img{max-width:100%;border:1px solid var(--line)}
figure.wide{overflow-x:auto}
figure.wide img{max-width:none;height:auto;width:auto;max-height:none}
figure.wide figcaption::after{content:"（横にスクロールできます）"}
figcaption{font-size:12px;color:var(--muted)}
.warn{color:var(--warn-line)}
#results{display:none;position:fixed;top:46px;right:16px;width:480px;max-height:70vh;overflow:auto;background:var(--bg);border:1px solid var(--line);border-radius:8px;box-shadow:0 4px 16px var(--shadow);z-index:6}
#results a{display:block;padding:6px 10px;border-bottom:1px solid var(--line);text-decoration:none;color:var(--fg);font-size:13px}
#results a b{color:var(--accent);font-weight:normal;font-size:12px;display:block}
#results mark{background:var(--hit);color:inherit}
footer{font-size:12px;color:var(--muted);margin-top:40px;border-top:1px solid var(--line);padding-top:8px}
@media (max-width:800px){nav{display:none}.wrap.navopen nav{display:block;position:fixed;z-index:7;width:80%}main{padding:12px}#q{width:140px}#results{width:92%}}
@media (min-width:801px){#menu{display:none}}
@media print{header,nav,#results{display:none}section.page{display:block!important}.tabpanel{display:block!important}}
"""

JS = r"""
window.VERSION = __VERSION__;
window.APP_TITLE = __TITLE__;
window.SOURCES = __SOURCES__;
(function(){
  document.title = APP_TITLE;
  document.getElementById('apptitle').textContent = APP_TITLE;
  document.querySelectorAll('.vertext').forEach(function(e){ e.textContent = VERSION; });
  document.getElementById('srcs').textContent = SOURCES;
  var root = document.documentElement;
  var saved = localStorage.getItem('manual-theme');
  if (saved) root.dataset.theme = saved;
  else if (matchMedia('(prefers-color-scheme: dark)').matches) root.dataset.theme = 'dark';
  document.getElementById('theme').onclick = function(){
    root.dataset.theme = root.dataset.theme === 'dark' ? 'light' : 'dark';
    localStorage.setItem('manual-theme', root.dataset.theme);
  };
  document.getElementById('menu').onclick = function(){ document.querySelector('.wrap').classList.toggle('navopen'); };
  var pages = Array.prototype.slice.call(document.querySelectorAll('section.page'));
  function showTab(panel){
    var bar = panel.parentNode.querySelector('.tabs');
    if (!bar) return;
    bar.querySelectorAll('button').forEach(function(b){
      var on = b.dataset.tab === panel.id;
      b.setAttribute('aria-selected', on ? 'true' : 'false');
      document.getElementById(b.dataset.tab).hidden = !on;
    });
  }
  document.querySelectorAll('.tabs button').forEach(function(b){
    b.onclick = function(){ location.hash = b.dataset.tab; };
  });
  // 検索の索引（route より先に作る：検索結果のURL #xN で開き直しても同じ場所に行けるように）
  var idx = [];
  function ownText(e){   // 入れ子の箇条書きの文字は親に含めない（二重に出さない）
    var t = '';
    e.childNodes.forEach(function(n){ if (n.nodeName !== 'UL' && n.nodeName !== 'OL') t += n.textContent; });
    return t;
  }
  pages.forEach(function(p){
    var title = p.dataset.title;
    p.querySelectorAll('h2,h3,h4,h5,p,li,td,pre').forEach(function(e){
      if (!e.id) e.id = 'x' + idx.length;
      var t = e.nodeName === 'LI' ? ownText(e) : e.textContent;
      idx.push({id: e.id, page: title, text: t, low: t.toLowerCase()});
    });
  });
  function route(){
    var id = decodeURIComponent(location.hash.slice(1)) || 'p-top';
    var el = document.getElementById(id);
    var page = el && el.closest('section.page');
    if (!page) { el = page = document.getElementById('p-top'); }   // ページの外を指すハッシュは「はじめに」へ
    pages.forEach(function(p){ p.hidden = p !== page; });
    var panel = el.classList.contains('tabpanel') ? el : el.closest('.tabpanel');
    if (panel) showTab(panel);
    document.querySelectorAll('nav li').forEach(function(li){
      var on = li.dataset.page === page.id;
      li.classList.toggle('open', on);
      li.querySelector('a').classList.toggle('on', on);
    });
    var top = el === page || el.classList.contains('tabpanel');
    setTimeout(function(){ if (top) window.scrollTo(0, 0); else el.scrollIntoView(); }, 0);   // ブラウザ自身のアンカー移動の後で合わせる
    document.querySelector('.wrap').classList.remove('navopen');
  }
  window.addEventListener('hashchange', route);
  route();
  // 検索：見出し・段落・箇条書き・表のセル・コードが対象。英字の大文字・小文字は区別しない
  var q = document.getElementById('q'), res = document.getElementById('results');
  function esc(s){ return s.replace(/[&<>"]/g, function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]; }); }
  q.addEventListener('input', function(){
    var w = q.value.trim();
    if (w.length < 2) { res.style.display = 'none'; return; }
    var wl = w.toLowerCase();
    var hits = idx.filter(function(x){ return x.low.indexOf(wl) >= 0; }).slice(0, 60);
    res.innerHTML = hits.length ? hits.map(function(h){
      var i = h.low.indexOf(wl), s = Math.max(0, i - 30);
      var snip = esc(h.text.slice(s, i)) + '<mark>' + esc(h.text.slice(i, i + w.length)) + '</mark>' + esc(h.text.slice(i + w.length, i + w.length + 50));
      return '<a href="#' + h.id + '"><b>' + esc(h.page) + '</b>' + snip + '</a>';
    }).join('') : '<a>見つかりません</a>';
    res.style.display = 'block';
  });
  res.addEventListener('click', function(){ res.style.display = 'none'; });
  document.addEventListener('keydown', function(e){ if (e.key === 'Escape') res.style.display = 'none'; });
})();
"""


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    sys.stdout.reconfigure(encoding='utf-8')
    out = Path(sys.argv[1])
    label = sys.argv[sys.argv.index('--label') + 1] if '--label' in sys.argv else '雛形'
    pages, nav, sources = build(label)
    ver = label
    srcs = '・'.join(re.sub(r'^\d{8}_', '', p.stem) for p in sources)
    navh = []
    for grp, items in nav:
        navh.append(f'<div class="grp">{html.escape(grp)}</div><ul>')
        for pid, title, subs in items:
            sub = ''.join(f'<a href="#{h}">{html.escape(re.sub(r"[`*]", "", t))}</a>' for h, t in subs)
            navh.append(f'<li data-page="{pid}"><a href="#{pid}">{html.escape(re.sub(r"[`*]", "", title))}</a>'
                        f'{f"<div class=subs>{sub}</div>" if sub else ""}</li>')
        navh.append('</ul>')
    body = ''.join(f'<section class="page" id="{pid}" data-title="{html.escape(t)}" hidden>{c}</section>'
                   for pid, t, c, _ in pages)
    js = JS.replace('__VERSION__', repr(ver)).replace('__TITLE__', repr(APP_TITLE)).replace('__SOURCES__', repr(srcs))
    doc = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{APP_TITLE}</title>
<style>{CSS}</style>
</head>
<body>
<header><button type="button" id="menu" aria-label="目次">☰</button><h1 id="apptitle">{APP_TITLE}</h1>
<span class="ver vertext"></span><input id="q" type="search" placeholder="検索（2文字以上）" aria-label="検索">
<button type="button" id="theme" aria-label="明暗の切替">◐</button></header>
<div id="results"></div>
<div class="wrap"><nav aria-label="目次">{''.join(navh)}</nav>
<main>{body}<footer>このHTMLは生成物です。直すときは元のMD（正本）を直して作り直す。版：<span class="vertext"></span>（元のMD：<span id="srcs"></span>）</footer></main></div>
<script>{js}</script>
</body>
</html>
"""
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(doc, encoding='utf-8')
    print(f'出力: {out}（{out.stat().st_size // 1024} KB、{len(pages)}ページ）')
    for p in sources:
        print('  元:', p.relative_to(AGENT))


if __name__ == '__main__':
    main()
