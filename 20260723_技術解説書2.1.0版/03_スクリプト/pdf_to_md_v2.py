# -*- coding: utf-8 -*-
"""技術解説書 v2.1.0 PDF → Markdown 変換（v2：表をMarkdown表として復元）。

方針（Q&A/ナレッジベース用途に最適化）:
  - 本文・表は pymupdf4llm で抽出（表を正しいMarkdown表として復元）
  - 見出しレベルはフォント依存でバラつくため、目次(TOC)基準で章(##)/節(###)に補正
  - 図キャプション（図N.）は見出しから降格し太字化＋画像プレースホルダ（テキスト中心）
  - 表キャプション（表N.）は見出しから降格し太字化
  - 目次ブロック・ページ番号・<u>タグ・章番号のバッククォートを除去

使い方:
  python pdf_to_md_v2.py <出力md> [キャッシュmd]
    キャッシュmd を渡すと pymupdf4llm 抽出結果を再利用（生成は約2〜3分かかるため）。
"""
import os
import re
import sys
import fitz  # PyMuPDF

SRC = "01_入力/電子カルテ情報共有サービスの導入に関するシステムベンダ向け技術解説書_v2.1.0.pdf"

DOC_TITLE = "電子カルテ情報共有サービスの導入に関するシステムベンダ向け技術解説書（記録条件仕様含む）"
DOC_SUBTITLE = "令和8年6月 2.1.0版　厚生労働省医政局"

TOC_RE = re.compile(r"^(\d+(?:\.\d+)?)\.?\s+(.+?)\s*[.…・]{3,}\s*(\d+)\s*$")
FIG_RE = re.compile(r"^図\s*[0-9０-９]")
TBL_RE = re.compile(r"^表\s*[0-9０-９]")
# キャプション判定（番号の直後にドット区切りがある＝「図1.…」）。参照文「図6 は…」は除外
CAP_FIG_RE = re.compile(r"^図\s*[0-9０-９]+\s*[.．]\s*\S")
CAP_TBL_RE = re.compile(r"^表\s*[0-9０-９]+\s*[.．]\s*\S")
# 見出し行の中身から番号+タイトルを取り出す（バッククォート・記号を許容）
HEAD_NUM_RE = re.compile(r"^`?(\d+(?:\.\d+)?)`?\.?\s+(\S.*)$")


def norm(s: str) -> str:
    return re.sub(r"\s+", "", s)


def build_toc():
    """目次を解析して {正規化(番号+タイトル): (番号, タイトル, level)} を返す。"""
    doc = fitz.open(SRC)
    toc = {}
    for page in doc[:8]:
        for ln in page.get_text("text").split("\n"):
            m = TOC_RE.match(ln.strip())
            if not m:
                continue
            num, title = m.group(1), m.group(2).strip()
            level = 1 if "." not in num else 2
            toc[norm(num + title)] = (num, title, level)
    return toc


def get_source_md(cache_path: str | None) -> str:
    if cache_path and os.path.exists(cache_path):
        with open(cache_path, encoding="utf-8") as f:
            return f.read()
    import pymupdf4llm
    md = pymupdf4llm.to_markdown(SRC)
    if cache_path:
        with open(cache_path, "w", encoding="utf-8") as f:
            f.write(md)
    return md


def process(src_md: str, toc: dict) -> str:
    # 全体クレンジング
    src_md = src_md.replace("<u>", "").replace("</u>", "")

    lines = src_md.split("\n")
    out = []
    out.append(f"# {DOC_TITLE}")
    out.append("")
    out.append(f"> {DOC_SUBTITLE}")
    out.append("")

    in_toc = False
    skipped_pre_title = False  # 冒頭のPDF生タイトル行を捨てる

    for raw in lines:
        s = raw.rstrip()
        st = s.strip()

        # 冒頭のPDF生タイトル/サブタイトル行はH1で置換済みなので捨てる
        if not skipped_pre_title:
            if st == "" or st.startswith("電子カルテ情報共有サービスの導入") \
               or st.startswith("システムベンダ向け") or "厚生労働省医政局" in st \
               or re.fullmatch(r"\d{1,3}", st):
                continue
            skipped_pre_title = True  # 最初の実コンテンツ行に到達

        # 空行
        if st == "":
            out.append("")
            continue

        # ページ番号のみの行を除去
        if re.fullmatch(r"\d{1,3}", st):
            continue

        # 目次ブロックのスキップ（"目次" 見出し〜最初の章 "1. はじめに"）
        if re.match(r"^#+\s*目次\s*$", st):
            in_toc = True
            continue
        if in_toc:
            probe = re.sub(r"^#+\s*", "", st).replace("`", "").strip()
            m = HEAD_NUM_RE.match(probe)
            if m and m.group(1) == "1" and norm(m.group(1) + m.group(2)) in toc:
                in_toc = False  # 目次終了、この行は下で見出し処理
            else:
                continue
        # ドット罫線を含む目次残骸行の保険的除去
        if re.search(r"[.…]{5,}", st):
            continue

        # 見出し行の処理
        if st.startswith("#"):
            body = re.sub(r"^#+\s*", "", st).replace("`", "").strip()

            # 図キャプション → 太字＋プレースホルダ
            if FIG_RE.match(body):
                out.append(f"**{body}**")
                out.append("")
                out.append("> （図：画像は原典PDFを参照）")
                out.append("")
                continue
            # 表キャプション → 太字
            if TBL_RE.match(body):
                out.append(f"**{body}**")
                out.append("")
                continue

            # 番号付き見出し → 目次照合
            m = HEAD_NUM_RE.match(body)
            if m and norm(m.group(1) + m.group(2)) in toc:
                num, title, level = toc[norm(m.group(1) + m.group(2))]
                prefix = "##" if level == 1 else "###"
                out.append(f"{prefix} {num} {title}")
                out.append("")
                continue

            # 目次外の見出し
            plain = body.strip("`").strip()
            # 文らしい（長い/句点終わり）ものは本文へ降格
            if len(plain) > 30 or plain.endswith("。"):
                out.append(plain)
                continue
            # 短い小見出し（◼、（N）、小項目等）は #### で保持
            out.append(f"#### {plain}")
            out.append("")
            continue

        # 本文中に現れる図/表キャプション（"図N." で始まる短い独立行）を整形。
        # 「図6 は、…します。」のような参照文（番号直後にドット無し／句点終わり／長文）は本文のまま。
        if CAP_FIG_RE.match(st) and not st.endswith("。") and len(st) < 60:
            out.append(f"**{st}**")
            out.append("")
            out.append("> （図：画像は原典PDFを参照）")
            out.append("")
            continue
        if CAP_TBL_RE.match(st) and not st.endswith("。") and len(st) < 60:
            out.append(f"**{st}**")
            out.append("")
            continue

        # 通常行はそのまま（表・段落は pymupdf4llm 整形済み）
        out.append(s)

    text = "\n".join(out)
    text = re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"
    return text


FOOTER = """

---

## 変換メモ

本ファイルは原典PDF（`電子カルテ情報共有サービスの導入に関するシステムベンダ向け技術解説書_v2.1.0.pdf`, 全217ページ）から自動抽出・整形したMarkdownである。ナレッジベースとしての利用（内容へのQ&A）を想定し、表構造を保持する方針で作成した。

### やったこと

- 全217ページの本文・表を pymupdf4llm で抽出（表を**正しいMarkdown表**として復元）。
- 目次を解析し、全10章・全節の見出し階層（`##` 章 / `###` 節）に補正。
- 図キャプション（図N.）を太字化し、画像はプレースホルダ注記に置換。表キャプション（表N.）を太字化。
- 目次ブロック・ページ番号・`<u>`タグ・章番号の装飾を除去。

### やっていないこと・限界

- **図・画像は抽出していない**（テキスト中心方針）。原典PDFを参照のこと。
- 表は自動レイアウト解析のため、複雑な結合セル・多段レイアウトの表では列がずれる場合がある。重要な表は原典PDFとの突合を推奨。
- レイアウト依存の脚注・欄外注記等が本文と混在する場合がある。
"""


def main():
    out_path = sys.argv[1] if len(sys.argv) > 1 else "out_v2.md"
    cache = sys.argv[2] if len(sys.argv) > 2 else None
    toc = build_toc()
    src_md = get_source_md(cache)
    text = process(src_md, toc).rstrip("\n") + FOOTER
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"wrote {out_path}: {len(toc)} toc-headings, {len(text)} chars")


if __name__ == "__main__":
    main()
