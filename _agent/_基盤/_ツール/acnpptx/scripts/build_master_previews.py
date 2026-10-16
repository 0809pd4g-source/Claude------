"""
build_master_previews.py — 設定 Widget 用に、各テーマ（スライドマスター）の代表レイアウトのプレビュー画像を作る。

テーマ JSON の layout_indices から 表紙（全バリエーション）/ 目次 / 中扉 / 本文 / 締め を選び、
compose.py でサンプル文字を入れたデッキを作って PowerPoint COM で書き出す。

出力（組み込みテーマ → <SKILL_DIR>/assets/master_previews/<theme>/、ユーザー追加 → ~/.acnpptx/master_previews/<theme>/）:
  cover.jpg, agenda.jpg, section.jpg, content.jpg, closing.jpg   … 480×270
  strip.jpg   … 表紙・目次・中扉・本文・締めを横に並べた帯（Widget 用、各 160×90）
  meta.json   … {"theme", "name", "layouts": [{"role", "key", "file", "layout_name"}], "cover_keys": [...]}

CLI:
  python build_master_previews.py [theme ...]     # 省略時は全テーマ
"""

import json
import os
import sys
import tempfile

_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)
import paths as _paths  # noqa: E402

SAMPLE = {
    "ja": {"title": "デジタル変革の推進に向けた提言", "subtitle": "2026年度 中期計画", "author": "Accenture",
           "date": "2026年10月", "sections": ["現状と課題", "目指す姿", "実行計画"], "section": "現状と課題",
           "content_title": "3つの柱で変革を進める", "message": "拡張・自動化・統制の3本柱で、半年以内に成果を出す"},
    "en": {"title": "Accelerating Digital Transformation", "subtitle": "FY2026 Mid-term Plan", "author": "Accenture",
           "date": "October 2026", "sections": ["Where we are", "Where we go", "How we get there"],
           "section": "Where we are", "content_title": "Three pillars of change",
           "message": "Extend, automate and govern to deliver results within six months"},
}


def _cover_keys(theme):
    li = theme.get("layout_indices", {})
    seen, keys = set(), []
    for k, v in li.items():
        if k.startswith("cover") and v not in seen:
            seen.add(v)
            keys.append(k)
    return keys or ["cover"]


def build(theme_name, lang="ja", width=960):
    import helpers as h
    import compose as c
    from PIL import Image
    if not _paths.is_safe_theme_name(theme_name):
        raise SystemExit(f"invalid theme name: {theme_name!r}")
    h.set_lang(lang)
    h.load_theme(theme_name)
    theme = h.THEME
    if not theme:
        raise SystemExit(f"theme not found: {theme_name}")
    t = SAMPLE[lang]
    prs = c.new_presentation()
    plan = []   # (role, key)
    all_covers = _cover_keys(theme)     # 表紙の種類は meta に名前だけ残す（Widget では選ばせないので見本は既定の 1 枚だけ）
    covers = all_covers[:1]
    for k in covers:
        c.add_cover(prs, {"title": t["title"], "subtitle": t["subtitle"], "author": t["author"], "date": t["date"],
                          "cover_layout": k})
        plan.append(("cover", k))
    c.add_agenda(prs, t["sections"]); plan.append(("agenda", "agenda"))
    c.add_section(prs, t["section"], 1, t["subtitle"]); plan.append(("section", "section"))
    s = c.new_content_slide(prs, t["content_title"], t["message"], f"{t['section']} > {t['content_title']}")
    c.render_body(s, {"grid": "G-N3", "connectors": ["R-ADD"],
                      "panes": [{"module": "M-BADGECOL", "badge": i + 1, "title": x, "text": y} for i, (x, y) in enumerate(
                          [("拡張", "Skills で知識を共有"), ("自動化", "Hooks で処理を挟む"), ("統制", "権限で範囲を絞る")]
                          if lang == "ja" else [("Extend", "Share know-how"), ("Automate", "Run hooks"), ("Govern", "Scope access")])],
                      "closing": {"type": "C-CONCLUSION", "text": "小さく始めて、効果を測り、横展開する" if lang == "ja"
                                  else "Start small, measure, then scale"}})
    plan.append(("content", "content"))
    h.make_closing_slide(prs, "Thank You"); plan.append(("closing", "closing"))
    tmp = tempfile.mkdtemp(prefix="acnpptx_prev_")
    pptx = os.path.join(tmp, "preview.pptx")
    prs.save(pptx)
    from thumbnail import export_thumbnails
    export_thumbnails(pptx, tmp, width)

    # スキル本体は読み取り専用なので、組み込みテーマを作り直すときも DATA_DIR に書く（preview_dir がこちらを優先する）
    out_dir = _paths.check_path(os.path.join(_paths.USER_PREVIEWS_DIR, theme_name), write=True)
    os.makedirs(out_dir, exist_ok=True)
    layouts, thumbs = [], {}
    names = {l["idx"]: l["name"] for l in theme.get("all_layouts", [])}
    for i, (role, key) in enumerate(plan, start=1):
        im = Image.open(os.path.join(tmp, f"slide_{i:02d}.png")).convert("RGB")
        fn = "cover.jpg" if (role == "cover" and key == covers[0]) else (f"cover_{key}.jpg" if role == "cover" else f"{role}.jpg")
        big = im.resize((480, 270), Image.LANCZOS)
        big.save(os.path.join(out_dir, fn), quality=80)
        thumbs[(role, key)] = im.resize((160, 90), Image.LANCZOS)
        idx = h.layout_idx(key if role == "cover" else role, 0)
        layouts.append({"role": role, "key": key, "file": fn, "layout_name": names.get(idx, "")})

    def strip(items, path):
        pad = 4
        W = len(items) * (160 + pad) + pad
        canvas = Image.new("RGB", (W, 90 + 2 * pad), (255, 255, 255))
        for k, im in enumerate(items):
            canvas.paste(im, (pad + k * (160 + pad), pad))
        canvas.save(path, quality=70)

    strip([thumbs[("cover", covers[0])], thumbs[("agenda", "agenda")], thumbs[("section", "section")],
           thumbs[("content", "content")], thumbs[("closing", "closing")]], os.path.join(out_dir, "strip.jpg"))
    meta = {"theme": theme_name, "name": theme.get("name", theme_name), "description": theme.get("description", ""),
            "primary": theme.get("tokens", {}).get("primary"), "layouts": layouts, "cover_keys": all_covers}
    with open(os.path.join(out_dir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    print(f"{theme_name}: {len(layouts)} previews → {out_dir}")
    return out_dir


def main():
    names = sys.argv[1:] or [t["name"] for t in _paths.list_themes()]
    if len(names) == 1:
        build(names[0])
        return
    import subprocess   # テーマ間で helpers の色定数が混ざらないよう 1 テーマ 1 プロセス
    for n in names:
        subprocess.run([sys.executable, os.path.abspath(__file__), n], check=False)


if __name__ == "__main__":
    main()
