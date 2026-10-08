"""OneNote貼り付け用の議事メモ（Markdownの入れ子箇条書き）を、入れ子<ul>のHTMLに変換する。

使い方:
    python onenote_html.py <議事メモ.md>      # 同じフォルダに同名の .html を出力

入力の書き方（議事録・逐語録_共通ルール §8-4）:
    # YYYYMMDD_会議名          → タイトル（大きめの文字）
    YYYY年M月D日  HH:MM         → タイトル直下の1行（任意。# の次の段落）
    ## 議題                     → 小見出し（太字の段落）
    - 問い・話題（発言者）      → 1段目（●）
      - 応答（発言者）          → 2段目（○）。スペース2つ単位で深くなる
    | 表 |                      → 表（対応表など）
    それ以外の行                → 段落
ブラウザで開いて Ctrl+A → Ctrl+C → OneNoteに貼り付ける。
"""
import html, re, sys
from pathlib import Path

def convert(md: str) -> str:
    out, stack = [], []  # stack: 開いている<ul>の深さ
    def close_to(depth):
        while len(stack) > depth:
            out.append("</li></ul>"); stack.pop()
    table = []
    def flush_table():
        if not table: return
        rows = [r for r in table if not re.match(r"^\|[\s\-:|]+\|$", r)]
        cells = [[html.escape(c.strip()) for c in r.strip("|").split("|")] for r in rows]
        h = '<table border="1" style="border-collapse:collapse">'
        for i, r in enumerate(cells):
            tag = "th" if i == 0 else "td"
            h += "<tr>" + "".join(f'<{tag} style="padding:2px 6px">{c}</{tag}>' for c in r) + "</tr>"
        out.append(h + "</table>"); table.clear()
    for raw in md.splitlines():
        line = raw.rstrip()
        if line.startswith("|"):
            close_to(0); table.append(line); continue
        flush_table()
        m = re.match(r"^( *)[-*] (.*)$", line)
        if m:
            depth = len(m.group(1)) // 2 + 1
            text = html.escape(m.group(2))
            text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
            if len(stack) < depth:
                while len(stack) < depth:
                    style = "disc" if len(stack) == 0 else ("circle" if len(stack) == 1 else "square")
                    out.append(f'<ul style="list-style-type:{style}"><li>'); stack.append(depth)
            else:
                close_to(depth)
                out.append("</li><li>")
            out.append(text)
            continue
        close_to(0)
        if not line.strip():
            continue
        t = html.escape(line.lstrip("# ").strip())
        t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
        if line.startswith("# "):
            out.append(f'<p style="font-size:20pt">{t}</p>')
        elif line.startswith("#"):
            out.append(f"<p><b>{t}</b></p>")
        else:
            out.append(f"<p>{t}</p>")
    flush_table()
    close_to(0)
    body = "\n".join(out).replace("<ul style=\"list-style-type:disc\"><li></li><li>", "<ul style=\"list-style-type:disc\"><li>")
    return ('<!DOCTYPE html><html lang="ja"><head><meta charset="utf-8"><title>OneNote貼り付け用</title>'
            '<style>body{font-family:"Meiryo UI","Yu Gothic UI",sans-serif;font-size:11pt;line-height:1.6;max-width:900px}</style>'
            f'</head><body>\n{body}\n</body></html>\n')

if __name__ == "__main__":
    src = Path(sys.argv[1])
    dst = src.with_suffix(".html")
    dst.write_text(convert(src.read_text(encoding="utf-8")), encoding="utf-8")
    print(dst)
