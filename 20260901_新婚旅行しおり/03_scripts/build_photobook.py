#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
フォトブック PDF ジェネレーター（Blurb Square 12"×12" 入稿対応）
==================================================================
Blurb の "PDF to Book" 入稿用 PDF を生成する汎用ビルダー。
旅行データは album_*.py に分離する（2ファイル構成）。

依存ライブラリ（初回のみ）:
    pip install reportlab Pillow

Usage:
    python album_egypt_greece.py
    # または
    from build_photobook import build
    from album_egypt_greece import ALBUM, OUTPUT_PATH
    build(ALBUM["meta"], ALBUM["pages"], OUTPUT_PATH)

ページタイプ一覧:
    "cover"   : 表紙（meta dict を使う）
    "full"    : 1枚フルブリード写真
    "grid_2"  : 2枚グリッド（横並び or 縦積み）
    "grid_4"  : 4枚グリッド（2×2）
    "divider" : セクション区切り（DAYタイトルページ）
    "blank"   : 白紙ページ
"""
from pathlib import Path
from reportlab.lib.units import mm
from reportlab.lib.colors import Color, white, HexColor
from reportlab.pdfgen.canvas import Canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader

# ══════════════════════════════════════════════════════
# Blurb Square 12"×12" 印刷仕様
# ══════════════════════════════════════════════════════
TRIM   = 304.8 * mm        # 12インチ
BLEED  = 3.175 * mm        # 0.125インチ 裁ち落とし
PAGE   = TRIM + 2 * BLEED  # PDF ページサイズ ≈ 311.15mm
SAFE_M = BLEED + 12.7 * mm # PDFエッジからのセーフマージン ≈ 15.875mm
SAFE_W = PAGE - 2 * SAFE_M # セーフ域の幅・高さ ≈ 279.4mm
CAP_H  = 9 * mm            # グリッド写真のキャプション高さ
GUTTER = 3 * mm            # 写真間の余白

# ══════════════════════════════════════════════════════
# カラーパレット（しおりと統一）
# ══════════════════════════════════════════════════════
C_AMBER    = HexColor("#B45309")
C_SKY      = HexColor("#0369A1")
C_AMBER_BG = HexColor("#FFFBEB")
C_SKY_BG   = HexColor("#F0F9FF")
C_SLATE    = HexColor("#334155")
C_GRAY     = HexColor("#94A3B8")
C_LIGHT    = HexColor("#E2E8F0")

_FONT = "Helvetica"  # 日本語フォント登録失敗時のフォールバック


# ══════════════════════════════════════════════════════
# フォント設定
# ══════════════════════════════════════════════════════
def _setup_font():
    global _FONT
    candidates = [
        ("C:/Windows/Fonts/YuGothM.ttc",  "YuGothic", 0),
        ("C:/Windows/Fonts/YuGothR.ttc",  "YuGothic", 0),
        ("C:/Windows/Fonts/yugothm.ttf",  "YuGothic", None),
        ("C:/Windows/Fonts/yugothic.ttf", "YuGothic", None),
        ("C:/Windows/Fonts/meiryo.ttc",   "Meiryo",   0),
        ("C:/Windows/Fonts/msgothic.ttc", "MSGothic", 0),
    ]
    for path, name, idx in candidates:
        if Path(path).exists():
            try:
                if idx is not None:
                    pdfmetrics.registerFont(TTFont(name, path, subfontIndex=idx))
                else:
                    pdfmetrics.registerFont(TTFont(name, path))
                _FONT = name
                print(f"  フォント: {name} ({path})")
                return
            except Exception:
                continue
    print(f"  ⚠️  日本語フォントが見つかりません。キャプションは英語推奨。")


# ══════════════════════════════════════════════════════
# 画像ヘルパー
# ══════════════════════════════════════════════════════
def _draw_image_crop(c, path, x, y, w, h):
    """写真をセンタークロップして x,y,w,h の矩形に填め込む"""
    if not path:
        _draw_placeholder(c, x, y, w, h, "（写真未設定）")
        return
    p = Path(path)
    if not p.exists():
        _draw_placeholder(c, x, y, w, h, p.name)
        print(f"  ⚠️  画像が見つかりません（スキップ）: {path}")
        return
    try:
        img = ImageReader(str(p))
        iw, ih = img.getSize()
        scale = max(w / iw, h / ih)
        sw, sh = iw * scale, ih * scale
        ix = x - (sw - w) / 2
        iy = y - (sh - h) / 2
        c.saveState()
        clip = c.beginPath()
        clip.rect(x, y, w, h)
        c.clipPath(clip, stroke=0, fill=0)
        c.drawImage(img, ix, iy, sw, sh)
        c.restoreState()
    except Exception as e:
        _draw_placeholder(c, x, y, w, h, p.name)
        print(f"  ⚠️  画像読み込みエラー: {path} ({e})")


def _draw_placeholder(c, x, y, w, h, label=""):
    c.saveState()
    c.setFillColor(C_LIGHT)
    c.rect(x, y, w, h, fill=1, stroke=0)
    c.setFillColor(C_GRAY)
    c.setFont(_FONT, 9)
    c.drawCentredString(x + w / 2, y + h / 2, label)
    c.restoreState()


# ══════════════════════════════════════════════════════
# キャプション描画
# ══════════════════════════════════════════════════════
def _caption_bar(c, caption, x, y, w):
    """フル写真用: 半透明バーに白文字キャプション"""
    if not caption:
        return
    bar_h = 11 * mm
    c.saveState()
    c.setFillColor(Color(0, 0, 0, 0.55))
    c.rect(x, y, w, bar_h, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont(_FONT, 9)
    c.drawString(x + 3 * mm, y + 3.5 * mm, caption)
    c.restoreState()


def _caption_text(c, caption, x, y, w):
    """グリッド用: 写真下のダーク文字キャプション"""
    if not caption:
        return
    c.saveState()
    c.setFillColor(C_SLATE)
    c.setFont(_FONT, 8)
    c.drawString(x, y + 2 * mm, caption)
    c.restoreState()


# ══════════════════════════════════════════════════════
# ページタイプ別描画
# ══════════════════════════════════════════════════════
def _page_cover(c, meta):
    """表紙ページ"""
    theme  = meta.get("theme", "a")
    bg_clr = C_AMBER_BG if theme == "a" else C_SKY_BG
    t_clr  = C_AMBER    if theme == "a" else C_SKY

    # 背景
    c.setFillColor(bg_clr)
    c.rect(0, 0, PAGE, PAGE, fill=1, stroke=0)

    cy = PAGE * 0.42  # タイトル縦位置（デフォルト：やや下寄り）

    # カバー写真（任意）
    if meta.get("image"):
        img_h = PAGE * 0.56
        _draw_image_crop(c, meta["image"], 0, PAGE - img_h, PAGE, img_h)
        # 下半分にオーバーレイ（可読性確保）
        c.saveState()
        c.setFillColor(Color(1.0, 0.98, 0.95, 0.82) if theme == "a"
                       else Color(0.94, 0.97, 1.0, 0.82))
        c.rect(0, 0, PAGE, PAGE * 0.48, fill=1, stroke=0)
        c.restoreState()
        cy = PAGE * 0.38

    # タイトル（英語/ASCII 推奨）
    c.setFillColor(t_clr)
    c.setFont(_FONT, 34)
    c.drawCentredString(PAGE / 2, cy, meta.get("title", ""))

    # サブタイトル
    if meta.get("subtitle"):
        c.setFillColor(C_SLATE)
        c.setFont(_FONT, 14)
        c.drawCentredString(PAGE / 2, cy - 18 * mm, meta["subtitle"])

    # 日付
    if meta.get("dates"):
        c.setFillColor(C_GRAY)
        c.setFont(_FONT, 10)
        c.drawCentredString(PAGE / 2, cy - 30 * mm, meta["dates"])


def _page_full(c, image, caption=""):
    """1枚フルブリード写真ページ"""
    _draw_image_crop(c, image, 0, 0, PAGE, PAGE)
    if caption:
        _caption_bar(c, caption, SAFE_M, SAFE_M, SAFE_W)


def _page_grid_2(c, images, orientation="h"):
    """2枚グリッド: 'h' 横並び(デフォルト), 'v' 縦積み"""
    bx, by = SAFE_M, SAFE_M

    if orientation == "v":
        # 縦積み: 上・下
        pw = SAFE_W
        ph = (SAFE_W - GUTTER - 2 * CAP_H) / 2
        row1_y = by + CAP_H
        row2_y = by + 2 * CAP_H + ph + GUTTER
        positions = [(bx, row2_y, pw, ph), (bx, row1_y, pw, ph)]
    else:
        # 横並び: 左・右
        pw = (SAFE_W - GUTTER) / 2
        ph = SAFE_W - CAP_H
        positions = [
            (bx,           by + CAP_H, pw, ph),
            (bx + pw + GUTTER, by + CAP_H, pw, ph),
        ]

    for i, (x, y, w, h) in enumerate(positions):
        if i < len(images):
            img = images[i]
            path = img.get("image", "") if isinstance(img, dict) else img
            cap  = img.get("caption", "") if isinstance(img, dict) else ""
            _draw_image_crop(c, path, x, y, w, h)
            _caption_text(c, cap, x, y - CAP_H, w)


def _page_grid_4(c, images):
    """4枚グリッド（2×2）"""
    pw = (SAFE_W - GUTTER) / 2
    ph = (SAFE_W - GUTTER - 2 * CAP_H) / 2
    bx, by = SAFE_M, SAFE_M
    row1_y = by + CAP_H
    row2_y = by + 2 * CAP_H + ph + GUTTER
    positions = [
        (bx,               row2_y, pw, ph),  # 左上
        (bx + pw + GUTTER, row2_y, pw, ph),  # 右上
        (bx,               row1_y, pw, ph),  # 左下
        (bx + pw + GUTTER, row1_y, pw, ph),  # 右下
    ]
    for i, (x, y, w, h) in enumerate(positions):
        if i < len(images):
            img = images[i]
            path = img.get("image", "") if isinstance(img, dict) else img
            cap  = img.get("caption", "") if isinstance(img, dict) else ""
            _draw_image_crop(c, path, x, y, w, h)
            _caption_text(c, cap, x, y - CAP_H, w)


def _page_divider(c, title, subtitle="", theme="a"):
    """セクション区切りページ（DAY タイトル）"""
    bg_clr = C_AMBER_BG if theme == "a" else C_SKY_BG
    t_clr  = C_AMBER    if theme == "a" else C_SKY
    bar    = HexColor("#B45309") if theme == "a" else HexColor("#0369A1")

    c.setFillColor(bg_clr)
    c.rect(0, 0, PAGE, PAGE, fill=1, stroke=0)

    # 中央アクセントライン
    c.setFillColor(bar)
    c.rect(SAFE_M, PAGE / 2 - 1 * mm, SAFE_W, 2 * mm, fill=1, stroke=0)

    c.setFillColor(t_clr)
    c.setFont(_FONT, 32)
    c.drawCentredString(PAGE / 2, PAGE / 2 + 14 * mm, title)

    if subtitle:
        c.setFillColor(C_SLATE)
        c.setFont(_FONT, 13)
        c.drawCentredString(PAGE / 2, PAGE / 2 - 10 * mm, subtitle)


def _page_blank(c):
    c.setFillColor(white)
    c.rect(0, 0, PAGE, PAGE, fill=1, stroke=0)


# ══════════════════════════════════════════════════════
# メインエントリーポイント
# ══════════════════════════════════════════════════════
_RENDERERS = {
    "full":    lambda c, p: _page_full(c, p.get("image",""), p.get("caption","")),
    "grid_2":  lambda c, p: _page_grid_2(c, p.get("images",[]), p.get("orientation","h")),
    "grid_4":  lambda c, p: _page_grid_4(c, p.get("images",[])),
    "divider": lambda c, p: _page_divider(c, p.get("title",""), p.get("subtitle",""), p.get("theme","a")),
    "blank":   lambda c, p: _page_blank(c),
}


def build(meta, pages, output_path):
    """
    meta:        ALBUM["meta"] dict（表紙情報）
    pages:       ALBUM["pages"] list（ページ定義）
    output_path: 出力 PDF パス (str or Path)
    """
    _setup_font()
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    c = Canvas(str(out), pagesize=(PAGE, PAGE))
    c.setTitle(meta.get("title", "Photo Book"))
    c.setSubject(meta.get("subtitle", ""))

    total = len(pages) + 1  # +1 は表紙
    print(f"\n📷 フォトブック生成: 全 {total} ページ")
    print(f"   サイズ: Blurb Square 12\"×12\"  /  出力: {out.name}")

    # 表紙
    print("  PAGE 01 (cover)...")
    _page_cover(c, meta)
    c.showPage()

    for i, page in enumerate(pages, 2):
        ptype = page.get("type", "full")
        print(f"  PAGE {i:02d} ({ptype})...")
        renderer = _RENDERERS.get(ptype)
        if renderer:
            renderer(c, page)
        else:
            print(f"  ⚠️  未知のページタイプ: {ptype}")
            _page_blank(c)
        c.showPage()

    c.save()
    size_kb = out.stat().st_size // 1024
    print(f"\n✅ 完成: {out}")
    print(f"   ページ数: {total}  /  ファイルサイズ: {size_kb} KB")
    print(f"\n📌 Blurb 入稿手順:")
    print(f"   1. blurb.com → 'Make a Book' → 'Upload PDF'")
    print(f"   2. ブックサイズ: Square 12×12 を選択")
    print(f"   3. このPDFをアップロード")
    return out
