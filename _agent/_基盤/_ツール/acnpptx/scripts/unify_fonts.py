"""デッキのフォントを 1 つにそろえる（既存の PPTX の編集・Restyle の後に使う）。

    python scripts/unify_fonts.py deck.pptx [--lang ja|en] [--out out.pptx]

全体が日本語なら、和文の中の英数字・コード・表・グラフも含めてすべて Meiryo UI（マスター・レイアウト・テーマの既定も）。
全体が英語なら Graphik。--lang を省くと文字から判定する（かな・漢字が 10% 以上なら日本語）。
build_deck は保存の直前に同じ処理を行うので、compose で作ったデッキに改めて掛ける必要はない。
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pptx import Presentation  # noqa: E402

import helpers as _h  # noqa: E402
import paths as _paths  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pptx")
    ap.add_argument("--lang", choices=("ja", "en"))
    ap.add_argument("--out", help="保存先（省略時は <入力名>_fonts.pptx。入力と同じパスを指定すれば上書き）")
    a = ap.parse_args()
    a.pptx = _paths.check_path(a.pptx)
    prs = Presentation(a.pptx)
    lang = a.lang or _h.deck_lang(prs)
    n = _h.unify_fonts(prs, lang)
    out = _paths.check_path(a.out or os.path.splitext(a.pptx)[0] + "_fonts.pptx", write=True)
    prs.save(out)
    print(f"{lang}: {n} か所を {_h.FONT_JA if lang == 'ja' else _h.FONT_EN} にそろえた → {out}")


if __name__ == "__main__":
    main()
