"""
build_settings_widget.py — 最初の設定 Widget（mcp__visualize__show_widget に渡す HTML）を組み立てる。

テンプレート assets/widget/settings.html に、テーマ一覧（プレビュー帯は小さい JPEG の data URI）と
依頼文から読み取った初期値を埋め込む。Claude は出力ファイルを Read し、その内容をそのまま show_widget に渡す。

CLI:
  python build_settings_widget.py --out widget.html [--defaults '{"theme":"acn-technology-graphik","count":"本文15枚以上"}']
                                  [--from-request theme count] [--existing-pptx] [--no-images]
  defaults のキー: theme, tone, deck_type, variation, count, lang, density, chapters, images, image_pptx, existing
  --from-request: 依頼文から読み取ったキー（「依頼文から反映」バッジを付ける）
  --existing-pptx: 既存 PPTX の扱い（編集 / Restyle / Retheme / 素材登録）の質問を出す（依頼文から判断できないときだけ）
  --no-images: プレビュー画像を埋め込まない（出力トークン節約・表示不可の環境向け）

プレビューが無いテーマは build_master_previews.py で作ってから実行すること。
"""

import argparse
import base64
import io
import json
import os
import sys

_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)
import paths as _paths  # noqa: E402

TONES = ["おまかせ", "経営層向け簡潔", "実務者向け詳細", "営業・訴求", "研修・解説", "社内共有"]
COUNTS = ["おまかせ", "5", "10", "15", "20+"]


def _story_options():
    with open(os.path.join(_paths.GRAMMAR_DIR, "compositions.json"), encoding="utf-8") as f:
        st = json.load(f)["story_templates"]
    return ["おまかせ"] + [f"{t['id']} {t['name_ja']}" for t in st]


PAGES = ("cover", "section", "content")   # マスターごとに見せる 3 ページ


def _tiles(path):
    """build_master_previews.py の帯画像（1 コマ 160×90＋余白 4）をコマに分ける。"""
    from PIL import Image
    im = Image.open(path).convert("RGB")
    n = max(1, round(im.width / 164))
    return [im.crop((4 + k * 164, 4, 4 + k * 164 + 160, 94)) for k in range(n)]


PX_W, PX_H, PX_COLORS = 56, 32, 12   # Widget 内プレビューの解像度と色数
_SYM = "abcdefghijklmnopqrstuvwxyz"


def _pages_px(pdir):
    """1 マスターの 表紙・中扉・本文 を、減色＋行ごとのランレングス文字列にする。

    data URI（base64）は同じ文字の繰り返しが多く、Claude が Widget に書き写すときに崩れやすい。
    この形式は「色記号＋連続数」の短い行の並びなので書き写しに強く、1 か所の誤りもその行に留まる。
    Widget 側の JS が canvas に描き戻す。返り値: [{"p": "rrggbb,…", "r": "a12b3…/…"}, …]
    """
    from PIL import Image
    out = []
    for n in PAGES:
        path = os.path.join(pdir, f"{n}.jpg")
        if not os.path.isfile(path):
            continue
        im = Image.open(path).convert("RGB").resize((PX_W, PX_H), Image.LANCZOS)
        q = im.quantize(colors=PX_COLORS, method=Image.MEDIANCUT)
        raw = q.getpalette()[:PX_COLORS * 3]
        pal = ["%02x%02x%02x" % tuple(raw[i * 3:i * 3 + 3]) for i in range(len(raw) // 3)]
        px = list(q.get_flattened_data() if hasattr(q, "get_flattened_data") else q.getdata())
        rows = []
        for y in range(PX_H):
            r, i, row = px[y * PX_W:(y + 1) * PX_W], 0, ""
            while i < PX_W:
                j = i
                while j < PX_W and r[j] == r[i]:
                    j += 1
                row += _SYM[r[i]] + (str(j - i) if j - i > 1 else "")
                i = j
            rows.append(row)
        out.append({"p": ",".join(pal), "r": "/".join(rows)})
    return out or None


def build_overview(out_path):
    """全テーマの 表紙・目次・中扉・本文・締め を並べた比較画像（SendUserFile 用）。"""
    from PIL import Image, ImageDraw
    from contact_sheet import _font
    blocks = []
    for t in _paths.list_themes():
        pdir = _paths.preview_dir(t["name"])
        if not os.path.isfile(os.path.join(pdir, "strip.jpg")):
            continue
        meta = json.load(open(os.path.join(pdir, "meta.json"), encoding="utf-8"))
        rows = [("基本", _tiles(os.path.join(pdir, "strip.jpg")), ["表紙", "目次", "中扉", "本文", "締め"])]
        blocks.append((meta.get("name", t["name"]) + f"（{t['name']}）", rows))
    tw, th, pad, lab = 240, 135, 8, 22
    cols = max(len(r[1]) for _, rows in blocks for r in rows)
    W = pad + cols * (tw + pad)
    H = sum(32 + len(rows) * (th + lab + pad) for _, rows in blocks) + pad
    im = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(im)
    f1, f2 = _font(20), _font(15)
    y = pad
    for title, rows in blocks:
        d.text((pad, y + 4), title, fill="#460073", font=f1)
        y += 32
        for _, tiles, labels in rows:
            for k, (t, l) in enumerate(zip(tiles, labels)):
                x = pad + k * (tw + pad)
                im.paste(t.resize((tw, th), Image.LANCZOS), (x, y))
                d.rectangle([x, y, x + tw - 1, y + th - 1], outline="#CFCFCF")
                d.text((x, y + th + 2), l, fill="#333333", font=f2)
            y += th + lab + pad
    im.save(out_path, quality=82)
    return out_path


def build(defaults, from_request, existing=False, images=True):
    themes = []
    for t in _paths.list_themes():
        pdir = _paths.preview_dir(t["name"])
        meta_p = os.path.join(pdir, "meta.json")
        meta = json.load(open(meta_p, encoding="utf-8")) if os.path.isfile(meta_p) else {}
        if not meta:
            with open(t["path"], encoding="utf-8") as f:
                tj = json.load(f)
            meta = {"name": tj.get("name", t["name"]), "primary": tj.get("tokens", {}).get("primary"),
                    "cover_keys": [k for k in tj.get("layout_indices", {}) if k.startswith("cover")] or ["cover"]}
        entry = {"theme": t["name"], "name": meta.get("name", t["name"]), "primary": meta.get("primary"),
                 "builtin": t["builtin"]}
        if images:
            px = _pages_px(pdir)
            if px:
                entry["px"] = px
        themes.append(entry)
    groups = [
        {"key": "tone", "label": "トーン", "q": "誰に向けた、どんなトーンの資料ですか？", "options": TONES},
        {"key": "deck_type", "label": "デッキ種類", "q": "資料の種類はどれに近いですか？", "options": _story_options()},
        {"key": "variation", "label": "バリエーション", "q": "スライドの見た目はどこまで変化をつけますか？",
         "options": ["バランス", "統一感重視", "多彩"]},
        {"key": "count", "label": "枚数", "q": "何枚くらいにしますか？（表紙・締めを除く本文）", "options": COUNTS,
         "free": "自由入力（例: 本文15枚以上）"},
        {"key": "lang", "label": "言語", "q": "言語は？", "options": ["日本語", "English"]},
        {"key": "density", "label": "情報密度", "q": "1枚あたりの情報量は？", "options": ["おまかせ", "少なめ（要点のみ）", "標準", "多め（詳細）"]},
        {"key": "chapters", "label": "中扉", "q": "章ごとに中扉を入れますか？", "options": ["おまかせ", "入れる", "入れない"]},
        {"key": "images", "label": "画像", "q": "画像はどう使いますか？",
         "options": ["おまかせ", "アイコン中心", "イラスト・写真も使う", "図形のみ"]},
    ]
    if existing:
        groups.insert(0, {"key": "existing", "label": "既存PPTXの扱い", "q": "渡された PPTX をどう扱いますか？",
                          "options": ["編集する", "Restyle（構成から作り直す）", "Retheme（色・マスターだけ変更）", "素材として使う"]})
    # 自由入力値（例「本文15枚以上」）は選択肢に無くてもそのまま初期値になる（入力欄に表示）
    data = {"themes": themes, "px_w": PX_W, "px_h": PX_H, "groups": groups, "defaults": dict(defaults), "from_request": list(from_request)}
    with open(os.path.join(_paths.ASSETS_DIR, "widget", "settings.html"), encoding="utf-8") as f:
        tpl = f.read()
    # <script> 内に埋め込むので、テーマ名などに含まれる </script> で抜け出せないよう < > & をエスケープする
    js = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    js = js.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    return tpl.replace("__DATA__", js)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--defaults", default="{}")
    ap.add_argument("--defaults-file", help="--defaults の代わりに JSON ファイルで渡す（依頼文由来の値をシェルに通さない）")
    ap.add_argument("--from-request", nargs="*", default=[])
    ap.add_argument("--existing-pptx", action="store_true")
    ap.add_argument("--no-images", action="store_true")
    ap.add_argument("--overview", help="マスター比較画像（JPEG）の出力先。Widget の前に SendUserFile で見せる")
    a = ap.parse_args()
    a.out = _paths.check_path(a.out, write=True)
    a.overview = a.overview and _paths.check_path(a.overview, write=True)
    a.defaults_file = a.defaults_file and _paths.check_path(a.defaults_file)
    if a.overview:
        print("overview:", build_overview(a.overview))
    if a.defaults_file:
        with open(a.defaults_file, encoding="utf-8") as f:
            defaults = json.load(f)
    else:
        defaults = json.loads(a.defaults)
    html = build(defaults, a.from_request, a.existing_pptx, not a.no_images)
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"{a.out}: {len(html):,} chars")


if __name__ == "__main__":
    main()
