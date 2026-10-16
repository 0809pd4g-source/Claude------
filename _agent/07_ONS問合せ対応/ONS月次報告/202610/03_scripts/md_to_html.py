"""読合せスクリプト（MD）を、プレゼン中に見る単一HTMLに変換する。
元：06_会議/開発進捗連絡会議/20261013/03_scripts/md_to_html.py（そのまま写した。ONS月次報告の読合せスクリプトにも使う）。
変更点：見出し（h2）に「スクリプト」を含む章の引用を「読み上げ用」と表示／箇条書きの中の字下げした引用を「投稿文」の枠にする／文字の大きさを切り替えるボタン。

使い方:
  python md_to_html.py <入力.md> <出力.html> <版の表示（例: 表示用v1（元: スクリプトv1））>
外部ライブラリ不要。資料で使う書式（見出し・表・コードブロック・引用・箇条書き・太字・コード）だけを扱う。
"""
import html
import re
import sys

SRC, DST, VERSION = sys.argv[1], sys.argv[2], sys.argv[3]


def inline(text):
    t = html.escape(text, quote=False)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r'<a href="\2">\1</a>', t)
    return t


def slug(n):
    return f"s{n}"


lines = open(SRC, encoding="utf-8").read().splitlines()
out, toc = [], []
i, sec_no, sub_no = 0, 0, 0
h1_text = ""
meta = []
in_section = False
last_label = ""
cur_h3 = ""
cur_h2 = ""


def close_section():
    global in_section
    if in_section:
        out.append("</section>")
        in_section = False


while i < len(lines):
    line = lines[i]

    if line.startswith("```"):
        buf = []
        i += 1
        while i < len(lines) and not lines[i].startswith("```"):
            buf.append(lines[i])
            i += 1
        i += 1
        kind = "図" if "押さえる" in cur_h3 else "台帳に貼る文面"
        out.append(f'<div class="answer"><div class="answer-bar"><span>{kind}</span>'
                   '<button type="button" class="copy">コピー</button></div>'
                   f"<pre>{html.escape(chr(10).join(buf), quote=False)}</pre></div>")
        continue

    m = re.match(r"^(#{1,4}) (.*)$", line)
    if m:
        level, text = len(m.group(1)), m.group(2)
        if level == 1:
            h1_text = text
        elif level == 2:
            close_section()
            sec_no += 1
            sub_no = 0
            sid = slug(sec_no)
            cur_h2 = text
            toc.append((2, sid, text))
            out.append(f'<section class="sec" id="{sid}"><h2>{inline(text)}</h2>')
            in_section = True
        else:
            sub_no += 1
            sid = f"{slug(sec_no)}-{sub_no}"
            if level == 3 and sec_no == 1:
                toc.append((3, sid, text))
            cls = ' class="item"' if (level == 3 and sec_no == 1) else ""
            out.append(f'<h{level} id="{sid}"{cls}>{inline(text)}</h{level}>')
        last_label = text if level >= 3 else ""
        cur_h3 = text if level == 3 else ("" if level == 2 else cur_h3)
        i += 1
        continue

    if line.lstrip().startswith("> ") or line.strip() == ">":
        indented = line.startswith(" ")
        buf = []
        while i < len(lines) and lines[i].lstrip().startswith(">"):
            q = lines[i].lstrip()
            buf.append(q[2:] if q.startswith("> ") else "")
            i += 1
        if sec_no == 0:
            meta.extend(buf)
            continue
        body = "".join(f"<p>{inline(b)}</p>" if b else "" for b in buf)
        if indented:
            box = "投稿文"
        elif "スクリプト" in cur_h3 or "スクリプト" in cur_h2:
            box = "読み上げ用"
        else:
            box = "相談文"
        out.append(f'<div class="consult"><div class="answer-bar"><span>{box}</span>'
                   '<button type="button" class="copy">コピー</button></div>'
                   f'<div class="consult-body">{body}</div>'
                   f'<pre hidden>{html.escape(chr(10).join(buf), quote=False)}</pre></div>')
        continue

    if line.startswith("|"):
        rows = []
        while i < len(lines) and lines[i].startswith("|"):
            rows.append(lines[i])
            i += 1
        cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
        head, body = cells[0], [r for r in cells[2:]]
        t = ['<div class="tbl"><table><thead><tr>']
        t += [f"<th>{inline(c)}</th>" for c in head]
        t.append("</tr></thead><tbody>")
        for r in body:
            t.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>")
        t.append("</tbody></table></div>")
        out.append("".join(t))
        continue

    if re.match(r"^(\s*)(- |\d+\. )", line):
        items = []
        while i < len(lines) and re.match(r"^(\s*)(- |\d+\. )", lines[i]):
            mm = re.match(r"^(\s*)(- |\d+\. )(.*)$", lines[i])
            items.append((len(mm.group(1)) // 2, mm.group(2).strip() != "-", mm.group(3)))
            i += 1
        cls = ' class="check"' if last_label.startswith("確認") else ""
        html_list, stack = [], []
        for depth, ordered, text in items:
            while len(stack) > depth + 1:
                html_list.append(f"</li></{stack.pop()}>")
            if len(stack) == depth + 1:
                html_list.append("</li>")
            while len(stack) < depth + 1:
                tag = "ol" if ordered else "ul"
                html_list.append(f"<{tag}{cls if not stack else ''}>")
                stack.append(tag)
            html_list.append(f"<li>{inline(text)}")
        while stack:
            html_list.append(f"</li></{stack.pop()}>")
        out.append("".join(html_list))
        continue

    if line.strip() == "---":
        i += 1
        continue

    if line.strip():
        m = re.match(r"^\*\*(.+?)\*\*$", line.strip())
        if m:
            last_label = m.group(1)
            kind = "label-check" if last_label.startswith("確認") else "label"
            out.append(f'<p class="{kind}">{inline(last_label)}</p>')
        else:
            out.append(f"<p>{inline(line)}</p>")
    i += 1

close_section()

nav = []
for lv, sid, text in toc:
    nav.append(f'<a class="lv{lv}" href="#{sid}">{inline(text)}</a>')

meta_html = "".join(f"<li>{inline(m)}</li>" for m in meta if m)

page = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(h1_text)}</title>
<style>
:root {{
  --bg: #f6f7f9; --panel: #ffffff; --text: #1f2328; --muted: #5b6470; --line: #d9dde3;
  --accent: #1f5fbf; --accent-bg: #eaf1fc; --answer-bg: #f3f8f2; --answer-line: #9cc59a;
  --consult-bg: #fff8e8; --consult-line: #e3c06a; --check-bg: #fff1f0; --check-line: #e08a84;
  --code-bg: #eef0f3; --th-bg: #eef2f7; --nav-active: #dbe7fb;
}}
@media (prefers-color-scheme: dark) {{
  :root {{
    --bg: #15181d; --panel: #1d2127; --text: #e6e8eb; --muted: #9aa3ad; --line: #343a43;
    --accent: #7fb0ff; --accent-bg: #1f2b3d; --answer-bg: #1b261c; --answer-line: #4f7a4d;
    --consult-bg: #2b2616; --consult-line: #8a7433; --check-bg: #2e1d1c; --check-line: #9a4f4a;
    --code-bg: #262b33; --th-bg: #252b34; --nav-active: #24344d;
  }}
}}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: var(--bg); color: var(--text);
  font-family: "Yu Gothic UI", "Meiryo", system-ui, sans-serif; font-size: 15px; line-height: 1.75; }}
main {{ zoom: var(--zoom, 1); }}
.sizer {{ display: flex; gap: 6px; margin: 0 6px 12px; }}
.sizer button {{ font: inherit; font-size: 12px; cursor: pointer; border: 1px solid var(--line);
  background: var(--panel); color: var(--text); border-radius: 5px; padding: 2px 10px; }}
.sizer button[aria-pressed="true"] {{ background: var(--nav-active); border-color: var(--accent); }}
.consult-body {{ font-size: 1.05em; }}
.layout {{ display: grid; grid-template-columns: 280px minmax(0, 1fr); }}
nav {{ position: sticky; top: 0; height: 100vh; overflow-y: auto; padding: 16px 12px;
  border-right: 1px solid var(--line); background: var(--panel); }}
nav .brand {{ font-weight: 700; font-size: 14px; margin: 0 6px 12px; }}
nav a {{ display: block; color: var(--text); text-decoration: none; border-radius: 6px;
  padding: 4px 8px; font-size: 13px; }}
nav a.lv2 {{ font-weight: 700; margin-top: 8px; }}
nav a.lv3 {{ padding-left: 20px; color: var(--muted); }}
nav a:hover, nav a.active {{ background: var(--nav-active); color: var(--text); }}
main {{ padding: 24px 32px 80px; max-width: 1100px; min-width: 0; overflow-wrap: anywhere; }}
h1 {{ font-size: 24px; margin: 0 0 8px; }}
.meta {{ color: var(--muted); font-size: 13px; margin: 0 0 20px; padding-left: 18px; }}
.sec {{ background: var(--panel); border: 1px solid var(--line); border-radius: 10px;
  padding: 8px 24px 20px; margin: 0 0 20px; }}
h2 {{ font-size: 20px; border-bottom: 2px solid var(--accent); padding-bottom: 6px; }}
h3 {{ font-size: 17px; margin-top: 28px; }}
h3.item {{ background: var(--accent-bg); border-left: 5px solid var(--accent);
  padding: 8px 12px; border-radius: 6px; }}
h4 {{ font-size: 15px; }}
p.label {{ font-weight: 700; color: var(--accent); margin: 16px 0 4px; }}
p.label-check {{ font-weight: 700; margin: 16px 0 4px; }}
ul.check, ol.check {{ background: var(--check-bg); border-left: 4px solid var(--check-line);
  border-radius: 6px; padding: 10px 14px 10px 34px; }}
code {{ background: var(--code-bg); padding: 1px 5px; border-radius: 4px; font-size: 13px; }}
a {{ color: var(--accent); }}
.tbl {{ overflow-x: auto; margin: 8px 0 16px; }}
table {{ border-collapse: collapse; width: 100%; font-size: 13.5px; }}
th, td {{ border: 1px solid var(--line); padding: 6px 8px; vertical-align: top; text-align: left; }}
th {{ background: var(--th-bg); white-space: nowrap; }}
.answer, .consult {{ border-radius: 8px; margin: 10px 0 18px; overflow: hidden; }}
.answer {{ background: var(--answer-bg); border: 1px solid var(--answer-line); }}
.consult {{ background: var(--consult-bg); border: 1px solid var(--consult-line); }}
.answer-bar {{ display: flex; justify-content: space-between; align-items: center;
  padding: 4px 10px; font-size: 12px; color: var(--muted); border-bottom: 1px solid var(--line); }}
.answer pre {{ margin: 0; padding: 12px 14px; white-space: pre-wrap; word-break: break-word;
  font-family: inherit; font-size: 14px; }}
.consult-body {{ padding: 6px 14px; }}
.consult-body p {{ margin: 6px 0; }}
button.copy {{ font: inherit; font-size: 12px; cursor: pointer; border: 1px solid var(--line);
  background: var(--panel); color: var(--text); border-radius: 5px; padding: 2px 10px; }}
button.copy.done {{ border-color: var(--answer-line); }}
footer {{ color: var(--muted); font-size: 12px; margin-top: 24px; }}
@media (max-width: 860px) {{
  .layout {{ grid-template-columns: minmax(0, 1fr); }}
  nav {{ position: static; height: auto; border-right: none; border-bottom: 1px solid var(--line); }}
  main {{ padding: 16px; }}
  .sec {{ padding: 4px 14px 14px; }}
}}
@media print {{
  nav, button.copy {{ display: none; }}
  .layout {{ display: block; }}
  .sec {{ break-inside: auto; border: none; }}
}}
</style>
</head>
<body>
<div class="layout">
<nav aria-label="目次"><div class="brand" id="brand"></div>
<div class="sizer" role="group" aria-label="文字の大きさ"><button type="button" data-zoom="1">標準</button><button type="button" data-zoom="1.2">大</button><button type="button" data-zoom="1.4">特大</button></div>
{''.join(nav)}</nav>
<main>
<h1 id="title">{html.escape(h1_text)}</h1>
<ul class="meta">{meta_html}</ul>
{chr(10).join(out)}
<footer id="footer"></footer>
</main>
</div>
<script>
window.VERSION = {VERSION!r};
window.DOC_TITLE = {h1_text!r};
document.title = window.DOC_TITLE + "｜" + window.VERSION;
document.getElementById("title").textContent = window.DOC_TITLE;
document.getElementById("brand").textContent = window.VERSION;
document.getElementById("footer").textContent = window.DOC_TITLE + "｜" + window.VERSION + "（MDの資料から自動生成）";

function copyText(text, btn) {{
  const done = () => {{ btn.textContent = "コピーしました"; btn.classList.add("done");
    setTimeout(() => {{ btn.textContent = "コピー"; btn.classList.remove("done"); }}, 1500); }};
  const fallback = () => {{
    const ta = document.createElement("textarea");
    ta.value = text; document.body.appendChild(ta); ta.select();
    document.execCommand("copy"); ta.remove(); done();
  }};
  if (navigator.clipboard && window.isSecureContext) {{
    navigator.clipboard.writeText(text).then(done, fallback);
  }} else {{ fallback(); }}
}}
document.querySelectorAll("button.copy").forEach(btn => {{
  btn.addEventListener("click", () => copyText(btn.closest(".answer, .consult").querySelector("pre").textContent, btn));
}});

const sizeButtons = [...document.querySelectorAll(".sizer button")];
function setZoom(z) {{
  document.documentElement.style.setProperty("--zoom", z);
  sizeButtons.forEach(b => b.setAttribute("aria-pressed", String(b.dataset.zoom === z)));
  try {{ localStorage.setItem("readthrough-zoom", z); }} catch (e) {{}}
}}
sizeButtons.forEach(b => b.addEventListener("click", () => setZoom(b.dataset.zoom)));
let savedZoom = "1";
try {{ savedZoom = localStorage.getItem("readthrough-zoom") || "1"; }} catch (e) {{}}
setZoom(sizeButtons.some(b => b.dataset.zoom === savedZoom) ? savedZoom : "1");

const links = [...document.querySelectorAll("nav a")];
const targets = links.map(a => document.getElementById(a.getAttribute("href").slice(1)));
const obs = new IntersectionObserver(entries => {{
  entries.forEach(e => {{
    if (e.isIntersecting) {{
      links.forEach(a => a.classList.toggle("active", a.getAttribute("href") === "#" + e.target.id));
    }}
  }});
}}, {{ rootMargin: "0px 0px -70% 0px" }});
targets.forEach(t => t && obs.observe(t));
</script>
</body>
</html>
"""
open(DST, "w", encoding="utf-8").write(page)
print(DST, len(page))
