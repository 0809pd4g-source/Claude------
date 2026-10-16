"""骨格（grammar/skeletons.json）を見本の文字で描き、一覧画像を作る（PowerPoint COM が必要）。

出力: ~/.acnpptx/skeleton_previews/sheet_01.jpg …（1 枚に 12 個、ID と名前のラベル付き）と index.json
（スキル本体は読み取り専用。同梱の assets/skeleton_previews/ を更新するときは、出力をメンテナーがコピーする）
生成時に Claude がこの一覧を見て、内容に合う骨格を選ぶ。
Usage: python build_skeleton_previews.py [--theme accenture]
"""
import argparse
import json
import os
import shutil
import sys

_SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _SCRIPTS)
import helpers as _h  # noqa: E402
import paths as _paths  # noqa: E402

OUT = os.path.join(_paths.DATA_DIR, "skeleton_previews")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--theme", default="accenture")
    ap.add_argument("--per", type=int, default=12)
    a = ap.parse_args()
    _paths.check_path(OUT, write=True)
    _h.set_lang("ja")
    _h.load_theme(a.theme)
    import compose
    import skeleton
    from contact_sheet import make_sheet
    sks = list(skeleton.load_all().values())
    prs = compose.new_presentation()
    for sk in sks:
        slide = compose.new_content_slide(prs, title=f"{sk['id']}  {sk.get('name', '')[:24]}",
                                          message="メッセージ：このスライドの結論を一文で書く")
        ctx = compose.Ctx(slide, prs, {})
        skeleton.render(ctx, sk, skeleton.template(sk, True), compose.body_box(slide))
    tmp = OUT + "_work"
    os.makedirs(tmp, exist_ok=True)
    pptx = os.path.join(tmp, "previews.pptx")
    prs.save(pptx)
    import win32com.client
    app = win32com.client.Dispatch("PowerPoint.Application")
    app.AutomationSecurity = 3  # msoAutomationSecurityForceDisable
    p = app.Presentations.Open(pptx, ReadOnly=True, Untitled=False, WithWindow=False)
    imgs = []
    try:
        for i in range(1, p.Slides.Count + 1):
            f = os.path.join(tmp, f"k{i:03d}.png")
            p.Slides(i).Export(f, "PNG", 800, 450)
            imgs.append(f)
    finally:
        p.Close()
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    index = []
    for n in range(0, len(imgs), a.per):
        chunk = list(zip(imgs[n:n + a.per], sks[n:n + a.per]))
        name = f"sheet_{n // a.per + 1:02d}.jpg"
        make_sheet([c[0] for c in chunk], [f"{s['id']} {s.get('intent', '').replace('new:', '')[:12]}" for _, s in chunk], 4, 400, (16, 9)) \
            .convert("RGB").save(os.path.join(OUT, name), quality=82)
        index += [{"id": s["id"], "sheet": name, "name": s.get("name"), "intent": s.get("intent"),
                   "relation": s.get("relation")} for _, s in chunk]
    json.dump(index, open(os.path.join(OUT, "index.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    shutil.rmtree(tmp, ignore_errors=True)
    print("previews", len(sks), "sheets", (len(sks) + a.per - 1) // a.per, "->", OUT)


if __name__ == "__main__":
    main()
