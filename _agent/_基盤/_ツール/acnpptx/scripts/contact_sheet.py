"""
コンタクトシート（ID ラベル付きの画像一覧）を作る。

用途:
  - イラスト・アイコンの意味タグ付け（Claude が画像として読む）
  - asset_search.py の候補一覧（Claude が見て最終選択する）
  - 完成デッキのサムネイル一覧（最終報告で SendUserFile する）

CLI:
  python contact_sheet.py --images a.png b.png ... --out sheet.png [--cols 5] [--cell 200] [--labels 0054 0055 ...]
  python contact_sheet.py --dir slides/ --out deck_overview.jpg --cols 4 --cell 360 --aspect 16:9
  python contact_sheet.py --dir illustrations/ --out-prefix sheets/sheet --cols 5 --rows 5   # 25 枚ごとに分割
"""

import argparse
import glob
import os
import sys

from PIL import Image, ImageDraw, ImageFont

import paths as _paths


def _font(size):
    for name in ("meiryo.ttc", "YuGothM.ttc", "msgothic.ttc", "arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def make_sheet(images, labels=None, cols=5, cell=200, aspect=None, label_h=None, bg="#FFFFFF"):
    """images: パスのリスト。labels: 同数のラベル（None ならファイル名）。PIL Image を返す。"""
    labels = labels or [os.path.splitext(os.path.basename(p))[0] for p in images]
    cw = cell
    ch = int(cell * aspect[1] / aspect[0]) if aspect else cell
    lh = label_h if label_h is not None else max(18, cell // 9)
    rows = (len(images) + cols - 1) // cols
    pad = 6
    sheet = Image.new("RGB", (cols * (cw + pad) + pad, rows * (ch + lh + pad) + pad), bg)
    draw = ImageDraw.Draw(sheet)
    font = _font(max(12, lh - 4))
    for i, (path, lab) in enumerate(zip(images, labels)):
        r, c = divmod(i, cols)
        x0 = pad + c * (cw + pad)
        y0 = pad + r * (ch + lh + pad)
        # セル枠（透過画像の境界がわかるよう薄いグレー）
        draw.rectangle([x0, y0, x0 + cw - 1, y0 + ch - 1], outline="#DDDDDD", fill="#FFFFFF")
        try:
            im = Image.open(path)
            if im.mode in ("RGBA", "LA", "P"):
                im = im.convert("RGBA")
                base = Image.new("RGBA", im.size, (255, 255, 255, 255))
                base.alpha_composite(im)
                im = base.convert("RGB")
            else:
                im = im.convert("RGB")
            im.thumbnail((cw - 8, ch - 8))
            sheet.paste(im, (x0 + (cw - im.width) // 2, y0 + (ch - im.height) // 2))
        except Exception as e:  # 壊れた画像は × 表示
            draw.line([x0, y0, x0 + cw, y0 + ch], fill="#CC0000", width=2)
            print(f"WARN: {path}: {e}", file=sys.stderr)
        draw.text((x0 + 2, y0 + ch + 1), str(lab), fill="#000000", font=font)
    return sheet


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", nargs="*")
    ap.add_argument("--dir")
    ap.add_argument("--glob", default="*.png")
    ap.add_argument("--labels", nargs="*")
    ap.add_argument("--out")
    ap.add_argument("--out-prefix", help="rows 指定時に分割出力するファイル名の接頭辞")
    ap.add_argument("--cols", type=int, default=5)
    ap.add_argument("--rows", type=int, help="1 枚あたりの行数（分割出力）")
    ap.add_argument("--cell", type=int, default=200)
    ap.add_argument("--aspect", help="セルの縦横比 例 16:9（省略時は正方形）")
    ap.add_argument("--quality", type=int, default=80)
    a = ap.parse_args()

    imgs = list(a.images or [])
    if a.dir:
        imgs += sorted(glob.glob(os.path.join(a.dir, a.glob)))
    if not imgs:
        sys.exit("ERROR: no images")
    imgs = [_paths.check_path(p) for p in imgs]
    aspect = tuple(int(x) for x in a.aspect.split(":")) if a.aspect else None
    labels = a.labels if a.labels and len(a.labels) == len(imgs) else None

    def save(im, path):
        path = _paths.check_path(path, write=True)
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        if path.lower().endswith((".jpg", ".jpeg")):
            im.save(path, quality=a.quality)
        else:
            im.save(path)
        print(path)

    if a.rows:
        per = a.cols * a.rows
        prefix = a.out_prefix or os.path.splitext(a.out)[0]
        for k in range(0, len(imgs), per):
            chunk = imgs[k:k + per]
            labs = labels[k:k + per] if labels else None
            save(make_sheet(chunk, labs, a.cols, a.cell, aspect), f"{prefix}_{k // per + 1:03d}.png")
    else:
        save(make_sheet(imgs, labels, a.cols, a.cell, aspect), a.out)


if __name__ == "__main__":
    main()
