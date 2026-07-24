# -*- coding: utf-8 -*-
"""技術解説書 v2.1.0 PDF を Markdown に変換する（テキスト中心方針）。

処理内容:
  - PyMuPDF でページテキストを抽出
  - ページ区切り／ページ番号のみの行を除去
  - 目次(TOC)を自動解析し、章(##)・節(###)見出しを再現
  - 図/表キャプション（図N. / 表N.）を太字化。図は画像プレースホルダ注記を付す
  - PDF の視覚折返しで分断された行を段落に結合（箇条書きマーカーは行頭を保持）

図・画像そのものは抽出しない（方針：テキスト中心）。
"""
import re
import sys
import fitz  # PyMuPDF

SRC = "01_入力/電子カルテ情報共有サービスの導入に関するシステムベンダ向け技術解説書_v2.1.0.pdf"

DOC_TITLE = "電子カルテ情報共有サービスの導入に関するシステムベンダ向け技術解説書（記録条件仕様含む）"
DOC_SUBTITLE = "令和8年6月 2.1.0版　厚生労働省医政局"

# 箇条書きマーカー（行頭でこれらに一致したら段落結合せず新しい行にする）
BULLET_RE = re.compile(
    r"^(?:[・･►▶‣◦]|[０-９0-9]{1,2}[.．)）]|[（(][０-９0-9]{1,3}[)）]|[①-⑳]|[ａ-ｚa-z][.．)）]|【[^】]+】)\s*"
)
# 図/表キャプション
FIG_RE = re.compile(r"^図\s*[0-9０-９]")
TBL_RE = re.compile(r"^表\s*[0-9０-９]")
# TOC 行: "1. はじめに ......... 6" / "1.1 本書の趣旨 ......... 6"
# 番号直後の任意のドット(章見出し "1." 形式)を許容する
TOC_RE = re.compile(r"^(\d+(?:\.\d+)?)\.?\s+(.+?)\s*[.…・]{3,}\s*(\d+)\s*$")
# 本文見出し候補: 行頭 "N. " または "N.N "
HEAD_CAND_RE = re.compile(r"^(\d+(?:\.\d+)?)\.?\s+(\S.*)$")


def norm(s: str) -> str:
    """空白除去して正規化（見出し照合用）。"""
    return re.sub(r"\s+", "", s)


def load_pages():
    doc = fitz.open(SRC)
    pages = []
    for page in doc:
        pages.append(page.get_text("text"))
    return pages


def clean_page(text: str, page_no: int):
    """ページ番号のみの行・空白のみ行の整理。行のリストを返す。"""
    out = []
    for ln in text.split("\n"):
        s = ln.rstrip()
        st = s.strip()
        if st == "":
            out.append("")
            continue
        # ページ番号のみの行（そのページ番号または近傍の数字）を除去
        if re.fullmatch(r"\d{1,3}", st) and int(st) == page_no:
            continue
        out.append(st)
    return out


def build_toc(pages):
    """TOC を解析して {正規化見出し文字列: level} を返す。level: 1=章,2=節。"""
    toc = {}
    for text in pages[:8]:  # 目次は前半に存在
        for ln in text.split("\n"):
            m = TOC_RE.match(ln.strip())
            if not m:
                continue
            num, title, _pg = m.group(1), m.group(2).strip(), m.group(3)
            level = 1 if "." not in num else 2
            key = norm(num + title)
            toc[key] = (num, title, level)
    return toc


def main(out_path: str):
    pages = load_pages()
    toc = build_toc(pages)

    # 全ページを1つの行リストに（ページ番号除去済み）
    lines = []
    for i, text in enumerate(pages, start=1):
        pl = clean_page(text, i)
        lines.extend(pl)

    md = []
    md.append(f"# {DOC_TITLE}")
    md.append("")
    md.append(f"> {DOC_SUBTITLE}")
    md.append("")

    buf = []  # 段落結合バッファ
    table_mode = [False]  # 表領域では行区切りを保持（セル単位で読めるようにする）

    def flush():
        if buf:
            md.append("".join(buf).strip())
            md.append("")
            buf.clear()

    # 目次ブロックはスキップ用フラグ（"目次" 行〜最初の本文章 "1. はじめに"）
    in_toc = False
    started_body = False

    idx = 0
    n = len(lines)
    while idx < n:
        raw = lines[idx]
        s = raw.strip()

        # 目次スキップ
        if not started_body and s == "目次":
            in_toc = True
            idx += 1
            continue
        if in_toc:
            # 本文開始（章1見出し）を検出したら目次終了
            m = HEAD_CAND_RE.match(s)
            if m and norm(m.group(1) + m.group(2)) in toc and m.group(1) == "1":
                in_toc = False
                started_body = True
            else:
                idx += 1
                continue

        if s == "":
            flush()
            md.append("")
            table_mode[0] = False  # 空行で表領域を抜ける
            idx += 1
            continue

        # 見出し判定
        m = HEAD_CAND_RE.match(s)
        if m:
            key = norm(m.group(1) + m.group(2))
            if key in toc:
                num, title, level = toc[key]
                flush()
                table_mode[0] = False
                prefix = "##" if level == 1 else "###"
                md.append(f"{prefix} {num} {title}")
                md.append("")
                started_body = True
                idx += 1
                continue

        # 図キャプション
        if FIG_RE.match(s):
            flush()
            table_mode[0] = False
            md.append(f"**{s}**")
            md.append("")
            md.append("> （図：画像は原典PDFを参照）")
            md.append("")
            idx += 1
            continue

        # 表キャプション → 以降を表領域とし、行区切りを保持
        if TBL_RE.match(s):
            flush()
            md.append(f"**{s}**")
            md.append("")
            table_mode[0] = True
            idx += 1
            continue

        # 表領域中は各行を独立行（箇条書き）として保持
        if table_mode[0]:
            md.append(f"- {s}")
            idx += 1
            continue

        # 箇条書きマーカー行 → 段落を区切り、行頭を保持
        if BULLET_RE.match(s):
            flush()
            buf.append(s)
            # 続く折返しは結合されるが、次の空行/マーカー/見出しで flush される
            idx += 1
            continue

        # 通常本文 → 段落結合
        buf.append(s)
        idx += 1

    flush()

    # 過剰な空行を圧縮
    text = "\n".join(md)
    text = re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"wrote {out_path}: {len(toc)} toc-headings, {len(text)} chars")


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "out.md"
    main(out)
