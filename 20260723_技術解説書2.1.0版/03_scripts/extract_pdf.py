# -*- coding: utf-8 -*-
"""技術解説書 v2.1.0 PDF からテキストを抽出する。
PyMuPDF(fitz) を使用。UTF-8 でページ区切り付きに書き出す。
"""
import sys
import fitz  # PyMuPDF

SRC = "01_入力/電子カルテ情報共有サービスの導入に関するシステムベンダ向け技術解説書_v2.1.0.pdf"


def main(out_path: str) -> None:
    doc = fitz.open(SRC)
    parts = []
    for i, page in enumerate(doc):
        text = page.get_text("text")
        parts.append(f"\n\n<<<PAGE {i + 1}>>>\n{text}")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("".join(parts))
    print(f"wrote {out_path}: {doc.page_count} pages")


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "raw_dump.txt"
    main(out)
