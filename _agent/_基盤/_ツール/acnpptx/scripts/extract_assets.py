#!/usr/bin/env python3
"""
extract_assets.py — PPTX 内の図形（アイコン・イラスト・画像）を透過 PNG として取り出し、索引を作る。

方式（PowerPoint COM、Windows 専用）:
  1. 各スライドを高解像度で 2 回書き出す（背景=白 / 背景=黒、マスター図形は非表示）
  2. 2 枚の差からアルファを復元する（alpha = 1 - (白版 - 黒版)、色 = 黒版 / alpha）
     → 白い塗りもアンチエイリアスも正しく透過になる
  3. 抽出対象の図形ごとに、その外接矩形で切り出し → 透明余白をトリム → 長辺 --max-px に縮小

旧版（一時スライドに貼って Slide.Export）は、PowerPoint のスライド最小サイズ（約 1in）のせいで
小さいアイコンが左上に寄った低解像度画像になっていた。本版はその問題を解消している。

抽出対象: グループ(6) / 画像(13) / フリーフォーム(14・文字なし) / グラフィック(17・文字なし)。
プレースホルダー・極小図形（--min-size pt 未満）・文字だけの図形は除外。

Usage:
    python extract_assets.py --input deck.pptx [deck2.pptx ...] \
        [--output-dir DIR] [--index-path DIR/asset_index.json] \
        [--id-map existing_index.json] [--start-id 1] [--scale-px 8000] [--max-px 512]

    既定の出力先: ~/.acnpptx/extracted/<pptxファイル名>/（images/ と asset_index.json）
    --id-map を渡すと、(source, slide, shape 名) が一致する図形は既存 ID を引き継ぐ。
"""

import argparse
import json
import os
import re
import sys
import tempfile

_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)
import paths as _paths  # noqa: E402

_MSO_GROUP, _MSO_PICTURE, _MSO_FREEFORM, _MSO_GRAPHIC = 6, 13, 14, 17
_VISUAL_TYPES = {_MSO_GROUP, _MSO_PICTURE, _MSO_FREEFORM, _MSO_GRAPHIC}


def _should_extract(shape_com, min_size_pt: float) -> bool:
    try:
        stype = shape_com.Type
        if stype not in _VISUAL_TYPES:
            return False
        try:
            pf = shape_com.PlaceholderFormat
            if pf is not None and pf.Type != 0:
                return False
        except Exception:
            pass
        if shape_com.Width < min_size_pt or shape_com.Height < min_size_pt:
            return False
        if stype in (_MSO_GRAPHIC, _MSO_FREEFORM):
            try:
                if shape_com.HasTextFrame and shape_com.TextFrame.TextRange.Text.strip():
                    return False
            except Exception:
                pass
        return True
    except Exception:
        return False


def _keywords_from_name(shape_name: str) -> list:
    """図形名（"calendar; date; schedule" 形式）からキーワードを取る。"Group 82" のような既定名は捨てる。"""
    if not shape_name:
        return []
    out = []
    for p in re.split(r"[;,]", shape_name):
        p = re.sub(r"\s+\d+$", "", p.strip().lower())
        if p in ("group", "picture", "freeform", "graphic", "グラフィックス", "グループ化", "図", "?"):
            continue
        if 2 <= len(p) <= 50:
            out.append(p)
    return list(dict.fromkeys(out))


def _alpha_from_pair(white_rgb, black_rgb):
    """白背景版・黒背景版（同サイズ RGB）から RGBA を復元する。"""
    import numpy as np
    from PIL import Image
    w = np.asarray(white_rgb, dtype=np.float32)
    b = np.asarray(black_rgb, dtype=np.float32)
    alpha = 1.0 - (w - b).mean(axis=2) / 255.0
    alpha = np.clip(alpha, 0.0, 1.0)
    safe = np.where(alpha > 1e-3, alpha, 1.0)[..., None]
    color = np.clip(b / safe, 0, 255)
    rgba = np.dstack([color, alpha * 255.0]).astype(np.uint8)
    return Image.fromarray(rgba, "RGBA")


def _finish(img, max_px: int, pad: int = 4):
    """透明余白をトリムし、長辺 max_px 以下に縮小。"""
    from PIL import Image
    bbox = img.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox()
    if bbox is None:
        return None
    x0, y0 = max(0, bbox[0] - pad), max(0, bbox[1] - pad)
    x1, y1 = min(img.width, bbox[2] + pad), min(img.height, bbox[3] + pad)
    img = img.crop((x0, y0, x1, y1))
    if max(img.size) > max_px:
        img.thumbnail((max_px, max_px), Image.LANCZOS)
    return img


def extract_assets(input_paths, output_dir, index_path, min_size_pt=15.0,
                   scale_px=8000, max_px=512, id_map=None, start_id=1):
    import win32com.client
    import pythoncom
    from PIL import Image

    pythoncom.CoInitialize()
    os.makedirs(output_dir, exist_ok=True)
    # (source, slide, shape 名) → 既存 ID のリスト（同名図形は出現順に対応させる）
    existing = {}
    if id_map:
        for k in sorted(id_map):
            v = id_map[k]
            existing.setdefault((v.get("source"), v.get("slide"), v.get("shape") or v.get("name")), []).append(k)
    used = {k for ids in existing.values() for k in ids}
    next_id = max([int(k) for k in used] + [start_id - 1]) + 1
    width = max(4, len(str(next_id + 9999)) - 1)   # 4 桁以上で 0 埋め
    index = {}
    tmpdir = tempfile.mkdtemp(prefix="acnpptx_extract_")

    app = win32com.client.Dispatch("PowerPoint.Application")
    app.AutomationSecurity = 3  # msoAutomationSecurityForceDisable: 開くファイルのマクロを実行しない
    try:
        for input_path in input_paths:
            abs_path = os.path.abspath(input_path)
            source = os.path.basename(abs_path)
            print(f"\nProcessing: {source}")
            prs = app.Presentations.Open(abs_path, ReadOnly=True, WithWindow=False)
            try:
                sw, sh_ = prs.PageSetup.SlideWidth, prs.PageSetup.SlideHeight
                px_per_pt = scale_px / sw
                for si in range(1, prs.Slides.Count + 1):
                    slide = prs.Slides(si)
                    targets = []
                    for i in range(1, slide.Shapes.Count + 1):
                        shp = slide.Shapes(i)
                        if _should_extract(shp, min_size_pt):
                            targets.append((shp.Name or f"Shape_{i}", shp.Left, shp.Top, shp.Width, shp.Height))
                    if not targets:
                        continue
                    slide.FollowMasterBackground = False
                    slide.DisplayMasterShapes = False
                    renders = {}
                    for tag, rgb in (("w", 0xFFFFFF), ("b", 0x000000)):
                        slide.Background.Fill.Solid()
                        slide.Background.Fill.ForeColor.RGB = rgb
                        p = os.path.join(tmpdir, f"s{si}_{tag}.png")
                        slide.Export(p, "PNG", scale_px, int(scale_px * sh_ / sw))
                        renders[tag] = Image.open(p).convert("RGB")
                    n = 0
                    seen = {}
                    for name, L, T, W, H in targets:
                        key = (source, si, name)
                        occ = seen.get(key, 0)
                        seen[key] = occ + 1
                        box = (max(0, int(L * px_per_pt) - 2), max(0, int(T * px_per_pt) - 2),
                               min(renders["w"].width, int((L + W) * px_per_pt) + 2),
                               min(renders["w"].height, int((T + H) * px_per_pt) + 2))
                        if box[2] <= box[0] or box[3] <= box[1]:
                            continue
                        img = _finish(_alpha_from_pair(renders["w"].crop(box), renders["b"].crop(box)), max_px)
                        if img is None:
                            continue
                        if occ < len(existing.get(key, [])):
                            aid = existing[key][occ]
                        else:
                            aid = f"{next_id:0{width}d}"
                            next_id += 1
                        img.save(os.path.join(output_dir, f"{aid}.png"), "PNG", optimize=True)
                        index[aid] = {
                            "name": name, "source": source, "slide": si, "shape": name,
                            "keywords": _keywords_from_name(name),
                            "width_px": img.width, "height_px": img.height,
                        }
                        n += 1
                    print(f"  slide {si}/{prs.Slides.Count}: {n} assets")
            finally:
                prs.Close()
    finally:
        try:
            if app.Presentations.Count == 0:
                app.Quit()
        except Exception:
            pass
        pythoncom.CoUninitialize()

    index = dict(sorted(index.items()))
    os.makedirs(os.path.dirname(os.path.abspath(index_path)), exist_ok=True)
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=1)
    print(f"\nDone. {len(index)} assets -> {output_dir}\nIndex: {index_path}")
    return index


def main():
    ap = argparse.ArgumentParser(description="PPTX の図形を透過 PNG として抽出し索引を作る")
    ap.add_argument("--input", nargs="+", required=True)
    ap.add_argument("--output-dir")
    ap.add_argument("--index-path")
    ap.add_argument("--id-map", help="既存の asset_index.json（ID を引き継ぐ）")
    ap.add_argument("--start-id", type=int, default=1)
    ap.add_argument("--min-size", type=float, default=15.0)
    ap.add_argument("--scale-px", type=int, default=8000, help="スライド全体の書き出し幅 px")
    ap.add_argument("--max-px", type=int, default=512, help="1 画像の長辺の上限 px")
    a = ap.parse_args()
    a.input = [_paths.check_path(p) for p in a.input]
    for p in a.input:
        if not os.path.isfile(p):
            sys.exit(f"ERROR: File not found: {p}")
        if p.lower().endswith((".pptm", ".potm", ".ppsm", ".ppam")):
            sys.exit(f"ERROR: macro-enabled file is not supported: {p}")
    if not a.output_dir:
        stem = re.sub(r"[^\w\-]+", "_", os.path.splitext(os.path.basename(a.input[0]))[0])
        base = os.path.join(_paths.EXTRACTED_DIR, stem)
        a.output_dir = os.path.join(base, "images")
        a.index_path = a.index_path or os.path.join(base, "asset_index.json")
    a.index_path = a.index_path or os.path.join(os.path.dirname(a.output_dir), "asset_index.json")
    a.output_dir = _paths.check_path(a.output_dir, write=True)
    a.index_path = _paths.check_path(a.index_path, write=True)
    id_map = None
    if a.id_map:
        with open(_paths.check_path(a.id_map), encoding="utf-8") as f:
            id_map = json.load(f)
    extract_assets(a.input, a.output_dir, a.index_path, a.min_size, a.scale_px, a.max_px, id_map, a.start_id)


if __name__ == "__main__":
    main()
