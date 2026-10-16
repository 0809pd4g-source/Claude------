"""
PPTX Skill — Post-generation verification script.

Run after saving a PPTX to check for common issues:
    python scripts/verify_pptx.py output.pptx

Checks performed:
  1. Font size (nothing below 11pt, excluding footer/slidenum。11pt は補足・注記・図中ラベル・密なページだけ: TYPE-01)
  2. Overflow (shapes within slide bounds)
  3. Overlap detection (significant shape overlaps)
  4. Footer verification (idx=20 + idx=21 on content slides)
  5. Text clipping detection (text overflows text box height)
  6. Horizontal text overflow (word_wrap=False width + textbox exceeds card boundary)
  7. Layout density (content fills 75%+ of available height)
  8. Per-slide audit summary (font range, shape count)

Approved fonts: Graphik, Meiryo UI, Arial, Meiryo, MS Gothic, MS PGothic,
                Yu Gothic, Yu Gothic UI, 游ゴシック, GT Sectra Fine
"""

import os
import sys
import io

# Handle encoding on Windows terminals
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from pptx import Presentation
from pptx.util import Inches, Emu
from lxml import etree

_ns = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main",
       "p": "http://schemas.openxmlformats.org/presentationml/2006/main"}
NSMAP_ASVG = "http://schemas.microsoft.com/office/drawing/2016/SVG/main"
_footer_idxs = {20, 21}

# Approved font names (case-insensitive prefix match)
_APPROVED_FONTS = {
    "graphik", "meiryo ui", "meiryo", "arial",
    "ms gothic", "ms pgothic", "yu gothic", "yu gothic ui",
    "游ゴシック", "游明朝", "gt sectra fine",
    "calibri", "times new roman",  # system fallbacks
}


import re as _re

# Placeholder hint text patterns (case-insensitive)
_HINT_PATTERNS = [
    _re.compile(r"タイトルを入力", _re.IGNORECASE),
    _re.compile(r"テキストを入力", _re.IGNORECASE),
    _re.compile(r"サブタイトルを入力", _re.IGNORECASE),
    _re.compile(r"ここにテキスト", _re.IGNORECASE),
    _re.compile(r"マスター\s*テキストの書式", _re.IGNORECASE),
    _re.compile(r"マスター\s*タイトルの書式", _re.IGNORECASE),
    _re.compile(r"Place\s+subtitle\s+here", _re.IGNORECASE),
    _re.compile(r"Click\s+to\s+add", _re.IGNORECASE),
    _re.compile(r"Enter\s+text\s+here", _re.IGNORECASE),
    _re.compile(r"Add\s+title", _re.IGNORECASE),
    _re.compile(r"Add\s+text", _re.IGNORECASE),
    _re.compile(r"日付を入力", _re.IGNORECASE),
    _re.compile(r"フッター", _re.IGNORECASE),
]

# Exclude footer/page-number placeholders from hint check
_HINT_SKIP_IDXS = {20, 21}


def verify_pptx(filepath):
    """Comprehensive PPTX verification.

    Returns:
        tuple: (prs, errors, warnings, footer_slides, svg_total)
    """
    prs = Presentation(filepath)
    errors = []
    warnings = []

    # ── 0. Placeholder hint text residue check ────────────────
    for i, sl in enumerate(prs.slides, 1):
        for sh in sl.shapes:
            if sh.is_placeholder and sh.placeholder_format.idx in _HINT_SKIP_IDXS:
                continue
            if not sh.has_text_frame:
                continue
            text = sh.text_frame.text.strip()
            if not text:
                continue
            for pat in _HINT_PATTERNS:
                if pat.search(text):
                    snippet = text[:50] + ("..." if len(text) > 50 else "")
                    errors.append(
                        f"Slide {i}: '{sh.name}' にプレースホルダーのヒントテキストが残留 "
                        f"— 「{snippet}」"
                    )
                    break  # one match per shape is enough

    # ── 0b. フォントの統一（全体が日本語なら英数字・コード・グラフも Meiryo UI、英語なら Graphik）──
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import helpers as _hp
        lang, face, bad = _hp.font_mismatches(prs)
        by_slide = {}
        for no, txt, faces in bad:
            by_slide.setdefault(no, []).append((txt, faces))
        for no, items in by_slide.items():
            txt, faces = items[0]
            errors.append(f"Slide {no}: FONT-01 {face} 以外のフォントが {len(items)} か所（例「{txt}」{faces}）"
                          f" — scripts/unify_fonts.py でそろえる")
    except Exception as e:  # noqa: BLE001
        warnings.append(f"フォントの統一を確かめられない: {e!r}")

    # ── 1. Font size check ───────────────────────────────────
    for i, sl in enumerate(prs.slides, 1):
        for sh in sl.shapes:
            if sh.is_placeholder and sh.placeholder_format.idx in _footer_idxs:
                continue
            for rp in sh._element.findall(".//a:rPr", _ns):
                sz = rp.get("sz")
                if sz and int(float(sz)) < 1100:
                    errors.append(
                        f"Slide {i}: font {int(float(sz))/100}pt < 11pt in '{sh.name}'"
                    )

    # ── 2. Overflow check ────────────────────────────────────
    sw = prs.slide_width
    sh_val = prs.slide_height
    tolerance = Emu(50000)  # ~0.05"
    for i, sl in enumerate(prs.slides, 1):
        for shp in sl.shapes:
            r, b = _vis_rb(shp)
            if r > sw + tolerance:
                errors.append(
                    f"Slide {i}: '{shp.name}' overflows RIGHT "
                    f"by {(r-sw)/914400:.2f}\""
                )
            if b > sh_val + tolerance:
                errors.append(
                    f"Slide {i}: '{shp.name}' overflows BOTTOM "
                    f"by {(b-sh_val)/914400:.2f}\""
                )

    # ── 3. Overlap detection ─────────────────────────────────
    margin = Emu(30000)
    for i, sl in enumerate(prs.slides, 1):
        shapes_bounds = []
        for shp in sl.shapes:
            if shp.width < Emu(50000) or shp.height < Emu(50000):
                continue
            shapes_bounds.append(
                (shp.name, shp.left, shp.top,
                 shp.left + shp.width, shp.top + shp.height)
            )
        for a_idx in range(len(shapes_bounds)):
            for b_idx in range(a_idx + 1, len(shapes_bounds)):
                a_name, a_l, a_t, a_r, a_b = shapes_bounds[a_idx]
                b_name, b_l, b_t, b_r, b_b = shapes_bounds[b_idx]
                a_contains_b = (
                    a_l - margin <= b_l and a_t - margin <= b_t
                    and a_r + margin >= b_r and a_b + margin >= b_b
                )
                b_contains_a = (
                    b_l - margin <= a_l and b_t - margin <= a_t
                    and b_r + margin >= a_r and b_b + margin >= a_b
                )
                if a_contains_b or b_contains_a:
                    continue
                ol = max(a_l, b_l)
                ot = max(a_t, b_t)
                orr = min(a_r, b_r)
                ob = min(a_b, b_b)
                if ol < orr and ot < ob:
                    ow = (orr - ol) / 914400
                    oh = (ob - ot) / 914400
                    area = ow * oh
                    a_area = (a_r - a_l) * (a_b - a_t) / (914400 * 914400)
                    b_area = (b_r - b_l) * (b_b - b_t) / (914400 * 914400)
                    min_area = min(a_area, b_area)
                    if min_area > 0 and area > 0.3 and area / min_area > 0.2:
                        warnings.append(
                            f"Slide {i}: '{a_name}' & '{b_name}' "
                            f"overlap {area:.1f} sq\""
                        )

    # ── 4. Footer verification ───────────────────────────────
    footer_slides = 0
    for i, sl in enumerate(prs.slides, 1):
        has_footer = any(
            ph.placeholder_format.idx == 20 for ph in sl.placeholders
        )
        has_num = any(
            ph.placeholder_format.idx == 21 for ph in sl.placeholders
        )
        if has_footer and has_num:
            footer_slides += 1

    # ── 5. Text clipping detection ───────────────────────────
    # Estimates required height including word-wrap line folding.
    # Single-paragraph textboxes are also checked (common clipping source).
    import math as _math

    def _get_font_size_emu(para):
        """Return font size in EMU for the first run in a paragraph, default 14pt."""
        for run in para.runs:
            if run.font.size:
                return int(run.font.size)
        for rp in para._p.findall(".//a:rPr", _ns):
            sz = rp.get("sz")
            if sz:
                return int(sz) * 127  # hundredths-of-pt → EMU
        return 14 * 12700  # 14pt default

    def _estimate_lines(text, fsz_emu, box_w_emu, word_wrap):
        """Estimate number of rendered lines accounting for word wrap."""
        if not text.strip():
            return 0
        if not word_wrap or box_w_emu <= 0:
            return 1
        # 字幅は Meiryo UI の実測（漢字 1.0・かな 0.75・和文の約物 0.7・英字 0.55・数字 0.62 × 文字サイズ）。
        # 段落ごとに数える（改行で分かれた行を 1 本につなげて数えない）
        def _w(c):
            o = ord(c)
            if 0x3040 <= o <= 0x30FF:
                return 0.75
            if 0x3000 <= o <= 0x303F or 0xFF01 <= o <= 0xFF0F:
                return 0.7
            return 1.0 if o > 0x2E80 else 0.62 if c.isdigit() else 0.55
        total = 0
        usable = max(box_w_emu - int(0.12 * 914400), int(0.2 * 914400))      # 左右の内余白を除く
        for para in text.replace("\v", "\n").split("\n"):
            width = sum(_w(c) for c in para) * fsz_emu
            total += max(1, _math.ceil(width / usable)) if para else 1
        return total

    for i, sl in enumerate(prs.slides, 1):
        for sh in sl.shapes:
            if sh.is_placeholder and sh.placeholder_format.idx in _footer_idxs:
                continue
            if not sh.has_text_frame:
                continue
            if sh.shape_type is not None and sh.shape_type == 19:  # table
                continue
            tf = sh.text_frame
            # Skip shapes with no visible text (decorative bars, empty containers)
            if not tf.text.strip():
                continue
            bp = tf._txBody.find("{http://schemas.openxmlformats.org/drawingml/2006/main}bodyPr")
            if bp is not None and bp.get("vert") in ("eaVert", "vert", "vert270", "wordArtVert"):
                continue      # 縦書きは横書きの見積もりでは測れない
            # 文字を箱に直接書いた図形（v6.8）は余白（inset）が大きいことがある: 既定（左右 0.2・上下 0.1in）を超える分を引く
            _ins = {k: int(bp.get(k, d)) if bp is not None else d
                    for k, d in (("lIns", 91440), ("rIns", 91440), ("tIns", 45720), ("bIns", 45720))}
            box_w_emu = sh.width - max(0, _ins["lIns"] + _ins["rIns"] - 182880)
            word_wrap = tf.word_wrap  # True / False / None (None = default wrap)
            use_wrap = (word_wrap is None) or word_wrap

            # Estimate required height across all paragraphs
            est_h_emu = 0
            for p in tf.paragraphs:
                text = p.text
                fsz = _get_font_size_emu(p)
                line_h = int(fsz * 1.35)  # 1.35× line spacing
                n_lines = max(1, _estimate_lines(text, fsz, box_w_emu, use_wrap))
                space = int(p.space_before) if p.space_before else 0
                est_h_emu += line_h * n_lines + space

            shape_h = sh.height - max(0, _ins["tIns"] + _ins["bIns"] - 91440)
            if est_h_emu > 0 and shape_h > 0 and est_h_emu > shape_h * 1.05:
                clip_pct = (est_h_emu - shape_h) / shape_h * 100
                level = "WARN" if clip_pct <= 20 else "CLIP"
                if clip_pct > 8:
                    msg = (
                        f"Slide {i}: '{sh.name}' text may be clipped "
                        f"(est={est_h_emu/914400:.2f}\" vs "
                        f"box={shape_h/914400:.2f}\", +{clip_pct:.0f}%)"
                    )
                    if level == "CLIP":
                        errors.append(msg)
                    else:
                        warnings.append(msg)

    # ── 6. Horizontal text overflow check ───────────────────
    # Detects two cases:
    #   (a) word_wrap=False textbox: estimated text width > box width
    #   (b) Any textbox whose RIGHT edge exceeds the right edge of a
    #       larger "container" shape that surrounds it (card overflow)
    for i, sl in enumerate(prs.slides, 1):
        # Build list of large background shapes (likely containers/cards)
        containers = []
        for sh in sl.shapes:
            # 線（コネクタ）の外接矩形は入れ物ではない（斜めの線が大きな矩形に見えて誤検知する）
            if sh._element.tag.endswith("cxnSp"):
                continue
            if not sh.has_text_frame and sh.width >= Inches(0.80) and sh.height >= Inches(0.50):
                containers.append((sh.left, sh.top,
                                   sh.left + sh.width, sh.top + sh.height))

        for sh in sl.shapes:
            if sh.is_placeholder and sh.placeholder_format.idx in _footer_idxs:
                continue
            if not sh.has_text_frame:
                continue
            tf = sh.text_frame
            if not tf.text.strip():
                continue

            sh_r = sh.left + sh.width
            sh_b = sh.top + sh.height

            # (a) word_wrap=False: estimate text width
            if tf.word_wrap is False:
                for p in tf.paragraphs:
                    text = p.text
                    if not text.strip():
                        continue
                    fsz = _get_font_size_emu(p)
                    cjk = sum(1 for c in text if ord(c) > 0x3000)
                    asc = len(text) - cjk
                    est_w = int(cjk * fsz + asc * fsz * 0.60)
                    if est_w > sh.width * 1.10:
                        errors.append(
                            f"Slide {i}: '{sh.name}' text may overflow RIGHT "
                            f"(word_wrap=False, est={est_w/914400:.2f}\" "
                            f"vs box={sh.width/914400:.2f}\")"
                        )
                        break

            # (b) textbox right edge exceeds its surrounding container
            for c_l, c_t, c_r, c_b in containers:
                # Check if this textbox is positioned inside the container
                inside_x = c_l - Emu(36000) <= sh.left <= c_r
                inside_y = c_t - Emu(36000) <= sh.top <= c_b
                if inside_x and inside_y and sh_r > c_r + Emu(36000):
                    errors.append(
                        f"Slide {i}: '{sh.name}' right edge ({sh_r/914400:.2f}\") "
                        f"exceeds container right ({c_r/914400:.2f}\") "
                        f"by {(sh_r - c_r)/914400:.2f}\""
                    )
                    break  # report once per shape

    # ── 7. Layout density check ──────────────────────────────
    CY_emu = Inches(1.50)
    BY_emu = Inches(6.85)
    sparse_threshold = Inches(5.85)
    for i, sl in enumerate(prs.slides, 1):
        if i == 1:
            continue
        max_bottom = 0
        for sh in sl.shapes:
            if sh.is_placeholder and sh.placeholder_format.idx in _footer_idxs:
                continue
            bottom = sh.top + sh.height
            if sh.top >= CY_emu and bottom > max_bottom:
                max_bottom = bottom
        if max_bottom > 0 and max_bottom < sparse_threshold:
            fill_pct = (max_bottom - CY_emu) / (BY_emu - CY_emu) * 100
            warnings.append(
                f"Slide {i}: layout sparse -- content fills {fill_pct:.0f}% "
                f"of AH (bottom={max_bottom/914400:.2f}\", "
                f"target>={sparse_threshold/914400:.2f}\")"
            )

    # ── 8. Horizontal fill / centering check ────────────────
    # Content area should use most of the available width (CW).
    # Tables and charts should always be full-width.
    ML_emu = Inches(0.42)
    CW_emu = Inches(12.50)
    content_right_target = ML_emu + CW_emu  # expected right edge

    for i, sl in enumerate(prs.slides, 1):
        if i == 1 or i == len(prs.slides):
            continue  # skip cover/closing
        # Collect content-area shapes (below CY)
        content_shapes = []
        has_table_or_chart = False
        for sh in sl.shapes:
            if sh.is_placeholder and sh.placeholder_format.idx in _footer_idxs:
                continue
            if sh.top < CY_emu:
                continue
            content_shapes.append(sh)

        if not content_shapes:
            continue

        # Find bounding box of all content shapes
        min_left = min(sh.left for sh in content_shapes)
        max_right = max(sh.left + sh.width for sh in content_shapes)
        content_width = max_right - min_left

        # Check individual tables and charts
        for sh in content_shapes:
            is_tbl = sh.has_table if hasattr(sh, 'has_table') else False
            is_chart = sh.has_chart if hasattr(sh, 'has_chart') else False
            if is_tbl or is_chart:
                has_table_or_chart = True
                sh_w = sh.width
                kind = "テーブル" if is_tbl else "チャート"
                # 単独なら全幅、他の部品と並べるなら最低 4.5in（grammar L-01）
                alone = len(content_shapes) <= 3
                if (alone and sh_w < CW_emu * 0.80) or sh_w < Emu(Inches(4.5)):
                    fill_pct = sh_w / CW_emu * 100
                    warnings.append(
                        f"Slide {i}: '{sh.name}' {kind}の幅が狭い "
                        f"({sh_w/914400:.1f}\" = CW の {fill_pct:.0f}%) — "
                        f"単独なら w=CW、並べるなら 4.5\" 以上にすること"
                    )

        # Check overall content horizontal fill
        if content_width < CW_emu * 0.70:
            fill_pct = content_width / CW_emu * 100
            warnings.append(
                f"Slide {i}: コンテンツ幅が狭い "
                f"({content_width/914400:.1f}\" = CW の {fill_pct:.0f}%) — "
                f"右側に大きな空白。幅を拡大するかセンタリングすること"
            )

    # ── 9b. v6.4 見た目の検査（番号の視線順・出典の行数・縦棒の長いラベル） ──
    warnings.extend(_visual_checks(prs))

    # ── 9. Per-slide audit ───────────────────────────────────
    print("\n── Per-Slide Audit ──")
    svg_total = 0
    for i, sl in enumerate(prs.slides, 1):
        min_font, max_font = 9999, 0
        svg_n = 0
        for sh in sl.shapes:
            if sh.is_placeholder and sh.placeholder_format.idx in _footer_idxs:
                continue
            for rp in sh._element.findall(".//a:rPr", _ns):
                sz = rp.get("sz")
                if sz:
                    fsz = int(sz) / 100
                    min_font = min(min_font, fsz)
                    max_font = max(max_font, fsz)
            if sh._element.findall(
                ".//" + f"{{{NSMAP_ASVG}}}svgBlip"
            ):
                svg_n += 1
        svg_total += svg_n
        font_str = (
            f"fonts={min_font:.0f}-{max_font:.0f}pt"
            if max_font > 0
            else "no-text"
        )
        print(f"  Slide {i:2d}: {len(sl.shapes):3d} shapes, {font_str}")

    return prs, errors, warnings, footer_slides, svg_total


_CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫"


def _num_of(text):
    """番号札の文字（"1" "02" "①" "STEP 3"）なら番号、違えば None。"""
    import re
    t = text.strip()
    if len(t) == 1 and t in _CIRCLED:
        return _CIRCLED.index(t) + 1
    m = re.fullmatch(r"(?:STEP\s*)?0?(\d{1,2})", t, re.I)
    return int(m.group(1)) if m else None


def _text_w_in(text, size_pt):
    return sum((0.55 if ord(ch) < 0x2E80 else 1.0) for ch in text) * size_pt / 72


def _vis_rb(shp):
    """見た目の右端・下端（EMU）。90°/270° 回した図形（縦向きのカギ線コネクタなど）は幅と高さが入れ替わる。"""
    try:
        rot = round(shp.rotation or 0) % 180
    except Exception:
        rot = 0
    w, h = (shp.height, shp.width) if rot == 90 else (shp.width, shp.height)
    cx, cy = shp.left + shp.width / 2, shp.top + shp.height / 2
    return cx + w / 2, cy + h / 2


def _cxn_ends(el):
    """コネクタの始点・終点（インチ）。局所座標の (0,0)→(w,h) を反転してから中心まわりに回す。"""
    import math
    xf = el.find(".//a:xfrm", _ns)
    if xf is None or xf.find("a:off", _ns) is None:
        return None
    o, e = xf.find("a:off", _ns), xf.find("a:ext", _ns)
    x, y, w, h = (int(o.get("x")) / 914400, int(o.get("y")) / 914400, int(e.get("cx")) / 914400, int(e.get("cy")) / 914400)
    rot = math.radians(int(xf.get("rot", 0)) / 60000)
    pts = []
    for lx, ly in ((0, 0), (w, h)):
        if xf.get("flipH") == "1":
            lx = w - lx
        if xf.get("flipV") == "1":
            ly = h - ly
        dx, dy = lx - w / 2, ly - h / 2
        pts.append((x + w / 2 + dx * math.cos(rot) - dy * math.sin(rot), y + h / 2 + dx * math.sin(rot) + dy * math.cos(rot)))
    return pts


def _cxn_path(el):
    """コネクタの通り道（インチの点の列）。直線は 2 点、bentConnector2 は 3 点、bentConnector3 は 4 点（adj1 の位置で曲がる）。"""
    import math
    xf = el.find(".//a:xfrm", _ns)
    if xf is None or xf.find("a:off", _ns) is None:
        return None
    o, e = xf.find("a:off", _ns), xf.find("a:ext", _ns)
    x, y, w, h = (int(o.get("x")) / 914400, int(o.get("y")) / 914400, int(e.get("cx")) / 914400, int(e.get("cy")) / 914400)
    g = el.find(".//a:prstGeom", _ns)
    prst = g.get("prst") if g is not None else "line"
    if prst == "bentConnector2":
        loc = [(0, 0), (w, 0), (w, h)]
    elif prst == "bentConnector3":
        gd = g.find("a:avLst/a:gd", _ns)
        a = int(gd.get("fmla").split()[-1]) / 100000 if gd is not None else 0.5
        loc = [(0, 0), (a * w, 0), (a * w, h), (w, h)]
    else:
        loc = [(0, 0), (w, h)]
    rot = math.radians(int(xf.get("rot", 0)) / 60000)
    pts = []
    for lx, ly in loc:
        if xf.get("flipH") == "1":
            lx = w - lx
        if xf.get("flipV") == "1":
            ly = h - ly
        dx, dy = lx - w / 2, ly - h / 2
        pts.append((x + w / 2 + dx * math.cos(rot) - dy * math.sin(rot), y + h / 2 + dx * math.sin(rot) + dy * math.cos(rot)))
    return pts


def _text_rect(sh):
    """図形の中の文字が実際に占める矩形（インチ）の見積もり。余白（inset）・縦の揃え・段落の揃え・折り返しを見る。"""
    el = sh._element
    bp = el.find(".//a:bodyPr", _ns)
    if bp is None or not sh.has_text_frame or not sh.text_frame.text.strip():
        return None
    ins = [int(bp.get(k, d)) / 914400 for k, d in (("lIns", 91440), ("tIns", 45720), ("rIns", 91440), ("bIns", 45720))]
    bx, by = sh.left / 914400 + ins[0], sh.top / 914400 + ins[1]
    bw, bh = sh.width / 914400 - ins[0] - ins[2], sh.height / 914400 - ins[1] - ins[3]
    if bw <= 0.05 or bh <= 0.05:
        return None
    wrap = bp.get("wrap") != "none"
    lines, tw, th, algn = 0, 0.0, 0.0, None
    for p in el.findall(".//a:p", _ns):
        t = "".join(r.text or "" for r in p.findall(".//a:t", _ns))
        szs = [int(r.get("sz")) / 100 for r in p.findall(".//a:rPr", _ns) if r.get("sz")]
        sz = max(szs) if szs else 18
        pp = p.find("a:pPr", _ns)
        algn = algn or (pp.get("algn") if pp is not None else None)
        ind = int(pp.get("marL", 0)) / 914400 if pp is not None else 0
        wd = _text_w_in(t, sz) + ind
        n = max(1, -(-wd // bw)) if wrap and wd > bw else 1
        tw = max(tw, min(wd, bw) if wrap else wd)
        th += n * sz * 1.2 / 72
        lines += n
    th = min(th, bh)
    anc = bp.get("anchor", "t")
    ty = by if anc == "t" else by + bh - th if anc == "b" else by + (bh - th) / 2
    tx = bx if algn in (None, "l", "just") else bx + bw - tw if algn == "r" else bx + (bw - tw) / 2
    return (tx, ty, tw, th)


def _seg_in_rect(p, q, r, m=0.02):
    x0, y0, x1, y1 = r[0] + m, r[1] + m, r[0] + r[2] - m, r[1] + r[3] - m
    if x1 <= x0 or y1 <= y0:
        return False
    for k in range(61):
        t = k / 60
        px, py = p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t
        if x0 < px < x1 and y0 < py < y1:
            return True
    return False


def _v67_line_text(sl, i):
    """LINE-03: 線（コネクタ）が文字の上を通る（ラベル・箱の文字が線でつぶれる）。線で描く記号（Glyph）は対象外。"""
    paths, texts = [], []
    for sh in sl.shapes:
        el = sh._element
        if el.tag.endswith("}cxnSp"):
            if not sh.name.startswith("Glyph"):
                pts = _cxn_path(el)
                if pts:
                    paths.append(pts)
        elif el.tag.endswith("}sp") and not sh.is_placeholder and sh.has_text_frame:
            r = _text_rect(sh)
            if r:
                texts.append((" ".join(sh.text_frame.text.split())[:12], r))
    hits = []
    for t, r in texts:
        if any(_seg_in_rect(p, q, r) for pts in paths for p, q in zip(pts, pts[1:])):
            hits.append(t)
    if hits:
        return [f"Slide {i}: LINE-03 線が文字の上を通る（{'・'.join('「' + h + '」' for h in hits[:4])}）— "
                "ラベルは線の脇に置き、線は箱・文字を避けて通す（M-ARCH は自動で選ぶ。手で描くなら connect.route で確かめる）"]
    return []


def _v68_overlay(sl, i):
    """TEXT-02: 色の矩形の上にテキストボックスを重ねている（文字は箱に直接書く。人の資料は 95% が直接）。"""
    shs = [sh for sh in sl.shapes if not sh.is_placeholder]
    tol = 18288
    hits = []
    for k, t in enumerate(shs):
        if t.shape_type != 17 or not t.has_text_frame or not t.text_frame.text.strip():
            continue
        for o in shs[:k][::-1]:
            if not (o.left < t.left + t.width and t.left < o.left + o.width and o.top < t.top + t.height and t.top < o.top + o.height):
                continue
            g = o._element.find(".//a:prstGeom", _ns)
            if (o.shape_type == 1 and g is not None and g.get("prst") == "rect"
                    and o._element.find("./p:spPr/a:solidFill", _ns) is not None
                    and o.left <= t.left + tol and o.top <= t.top + tol and o.left + o.width >= t.left + t.width - tol
                    and o.top + o.height >= t.top + t.height - tol and not o.text_frame.text.strip()
                    and t.width * t.height >= o.width * o.height * 0.15):
                hits.append(" ".join(t.text_frame.text.split())[:10])
            break
    if hits:
        return [f"Slide {i}: TEXT-02 色の箱の上にテキストボックスを重ねている（{'・'.join('「' + h + '」' for h in hits[:3])}）— "
                "文字は箱に直接書く（compose は merge_text_into_boxes で自動。手で描くなら _shape_text か箱の text_frame に書く）"]
    return []


def _v66_lines_sizes(sl, i):
    """LINE-02: 接続していない線が端点で継がれている（直線を継いだカギ線）／図形の辺の中ほどに触れているのに接続していない。
    SIZE-01: 同じ形・同じ塗りで上端がそろう 3 個以上の並びの高さが違う（人の資料の 91% は同じ高さ）。"""
    out = []
    cx = []
    boxes = []
    for sh in sl.shapes:
        el = sh._element
        if el.tag.endswith("}cxnSp"):
            ends = _cxn_ends(el)
            if not ends or sh.name.startswith("Glyph"):      # 線で描く記号（ツリーの罫・座標軸）は対象外
                continue
            ln = el.find(".//a:ln", _ns)
            arrow = ln is not None and (ln.find("a:headEnd", _ns) is not None or ln.find("a:tailEnd", _ns) is not None)
            nv = el.find(".//p:cNvCxnSpPr", _ns)
            bound = [nv is not None and nv.find("a:stCxn", _ns) is not None,
                     nv is not None and nv.find("a:endCxn", _ns) is not None]
            cx.append((ends, bound, arrow))
        elif el.tag.endswith("}sp") and not sh.is_placeholder and sh.shape_type != 17:   # 17 = テキストボックス
            g = el.find(".//a:prstGeom", _ns)
            fill = el.find("./p:spPr/a:solidFill/a:srgbClr", _ns)
            boxes.append((g.get("prst") if g is not None else None, fill.get("val") if fill is not None else None,
                          sh.left / 914400, sh.top / 914400, sh.width / 914400, sh.height / 914400))
    stitched = touching = 0
    def touches(p):
        for prst, _, bx, by, bw, bh in boxes:
            if prst not in ("rect", "ellipse", "flowChartAlternateProcess", "can") or bw < 0.3 or bh < 0.25:
                continue
            on_v = (abs(p[0] - bx) < 0.03 or abs(p[0] - bx - bw) < 0.03) and by + bh * 0.25 < p[1] < by + bh * 0.75
            on_h = (abs(p[1] - by) < 0.03 or abs(p[1] - by - bh) < 0.03) and bx + bw * 0.25 < p[0] < bx + bw * 0.75
            if on_v or on_h:
                return True
        return False
    for k, (ends, bound, arrow) in enumerate(cx):
        # 図形をつなぐ線とみなすのは、矢印付きか、両端とも図形の辺に触れる線（下線・区切りの線は片端だけ触れる）
        joins = arrow or all(bound[j] or touches(p) for j, p in enumerate(ends))
        for j, p in enumerate(ends):
            if bound[j]:
                continue
            if any(m != k and not bd[q] and abs(p[0] - e2[q][0]) < 0.02 and abs(p[1] - e2[q][1]) < 0.02
                   for m, (e2, bd, _) in enumerate(cx) for q in (0, 1)):
                stitched += 1
                continue
            if not joins:
                continue
            for prst, _, bx, by, bw, bh in boxes:
                if prst not in ("rect", "ellipse", "flowChartAlternateProcess", "can") or bw < 0.3 or bh < 0.25:
                    continue
                on_v = (abs(p[0] - bx) < 0.03 or abs(p[0] - bx - bw) < 0.03) and by + bh * 0.25 < p[1] < by + bh * 0.75
                on_h = (abs(p[1] - by) < 0.03 or abs(p[1] - by - bh) < 0.03) and bx + bw * 0.25 < p[0] < bx + bw * 0.75
                if on_v or on_h:
                    touching += 1
                    break
    if stitched:
        out.append(f"Slide {i}: LINE-02 直線を継いで曲げた線（継ぎ目 {stitched // 2 or 1} か所）— 曲げる線はカギ線コネクタ 1 本で、"
                   "両端を図形の接続点につなぐ（connect.link）")
    if touching:
        out.append(f"Slide {i}: LINE-02 図形の辺に触れているのに接続していない線の端が {touching} か所 — "
                   "接続点につなぐ（PowerPoint で選ぶと端点が緑。箱を動かすと線が付いてくる）")
    rows = {}
    for prst, fill, bx, by, bw, bh in boxes:
        if prst in ("rect", "homePlate", "chevron", "ellipse") and fill and bw > 0.5 and bh > 0.3:
            rows.setdefault((prst, fill, round(by / 0.04)), []).append(bh)
    bad = [(k, v) for k, v in rows.items() if len(v) >= 3 and max(v) - min(v) > 0.03]
    if bad:
        k, v = bad[0]
        out.append(f"Slide {i}: SIZE-01 同じ物の並び（{len(v)} 個）の高さが違う（{min(v):.2f}〜{max(v):.2f}in）— "
                   "並べる物は同じ大きさにそろえる（中身の多い方に合わせる）")
    return out


def _v65_slide(sl, i, H):
    out = []
    by_size, total = {}, 0
    icons_big = 0
    for sh in sl.shapes:
        if sh.is_placeholder:
            continue
        st = sh.text_frame.text.strip() if sh.has_text_frame else ""
        is_note = sh.has_text_frame and sh.top > H * 0.8 and st.startswith(("出典", "Source", "※", "注", "（注", "(注"))
        if (sh.has_text_frame or sh.has_table) and sh.top < H * 0.9 and not is_note:   # 出典・注記は 11pt でよい（数えない）
            for r in sh._element.findall(".//a:r", _ns):
                rp = r.find("a:rPr", _ns)
                t = "".join(x.text or "" for x in r.findall("a:t", _ns)).strip()
                if not t or rp is None or rp.get("sz") is None:
                    continue
                sz = int(rp.get("sz")) / 100
                by_size[sz] = by_size.get(sz, 0) + len(t)
                total += len(t)
        if sh.shape_type == 13:        # 画像: ほぼ正方形の小さな画像をアイコンとみなす
            w_in, h_in = sh.width / 914400, sh.height / 914400
            if 0.6 < w_in / max(h_in, 0.01) < 1.6 and max(w_in, h_in) > 0.9 and max(w_in, h_in) < 1.8:
                icons_big += 1
        if sh._element.tag.endswith("}cxnSp"):
            geom = sh._element.find(".//a:prstGeom", _ns)
            ln = sh._element.find(".//a:ln", _ns)
            dash = ln is not None and ln.find("a:prstDash", _ns) is not None
            w_pt = int(ln.get("w", "12700")) / 12700 if ln is not None else 1.0
            dx, dy = sh.width / 914400, sh.height / 914400
            if geom is not None and geom.get("prst") == "straightConnector1" and dx > 0.3 and dy > 0.3 \
                    and (dx * dx + dy * dy) ** 0.5 > 1.5 and w_pt < 2.0 and not dash:
                out.append(f"Slide {i}: LINE-01 斜めの細い長い線（{(dx * dx + dy * dy) ** 0.5:.1f}in・{w_pt:.2f}pt）"
                           "— 余白を横切る線は細く見える。要素を近づけて直角の短い線にするか、面の箱で区切る")
    out += _v66_lines_sizes(sl, i)
    out += _v67_line_text(sl, i)
    out += _v68_overlay(sl, i)
    small = by_size.get(11.0, 0)
    if total >= 80 and small > total * 0.5:
        out.append(f"Slide {i}: TYPE-01 11pt が本文の {small * 100 // total}% — 11pt は補足・注記・図中ラベルだけ（本文は 12pt 以上）")
    elif small and total < 200 and small > 40:
        out.append(f"Slide {i}: TYPE-01 字数の少ないページ（{total} 字）で 11pt を使っている — 12pt 以上にする")
    if icons_big:
        out.append(f"Slide {i}: ICON-03 大きなアイコンが {icons_big} 個（0.9in 超）— アイコンは脇役（0.45〜0.8in）。見出しと中身を主役にする")
    return out


def _visual_checks(prs):
    """人の目で見て不自然な配置を拾う（はみ出し検査では見つからないもの）。
    ORDER-01: 番号札の位置が読む順（左→右、上→下）と食い違う
    SRC-01:   出典・注記（下端の灰色の小さい文字）が 2 行以上になり、本文と同じくらい目立つ
    CHART-03: 縦棒グラフの項目名が長く、縦に折れて読めない（横棒にする）
    TYPE-01:  11pt の文字が本文の半分を超える／字数の少ないページ（200 字未満）で 11pt を使う
    ICON-03:  アイコンが大きく主役になっている（0.9in 超。人の資料の中央値 0.47in、p75 0.81in）
    LINE-01:  斜めの細い長い線（1.5in 超・2pt 未満）が余白を横切る（直角の短い線か、面の箱で区切る）
    LINE-03:  線が文字（ラベル・箱の文字）の上を通る"""
    from pptx.enum.chart import XL_CHART_TYPE
    out = []
    H = prs.slide_height
    for i, sl in enumerate(prs.slides, 1):
        if i > 1:
            out += _v65_slide(sl, i, H)
        nums = []
        for sh in sl.shapes:
            if sh.is_placeholder or not sh.has_text_frame:
                continue
            t = sh.text_frame.text
            n = _num_of(t) if len(t.strip()) <= 7 else None
            if n is not None and sh.width < Inches(1.2):
                nums.append((n, sh.left + sh.width / 2, sh.top + sh.height / 2))
            # 出典・注記
            st = t.strip()
            if sh.top > H * 0.82 and (st.startswith(("出典", "Source", "※", "注")) or "出典:" in st) and sh.width > 0:
                sz = max([int(r.get("sz")) / 100 for r in sh._element.findall(".//a:rPr", _ns) if r.get("sz")] + [12])
                lines = sum(max(1, -(-_text_w_in(p, sz) // max(sh.width / 914400 - 0.1, 0.5))) for p in st.split("\n"))
                if lines >= 2:
                    out.append(f"Slide {i}: SRC-01 出典・注記が {int(lines)} 行になる — 1 行に縮める（出典は本文より目立たせない）")
        if len(nums) >= 3 and len({n for n, _, _ in nums}) == len(nums):
            nums.sort()
            row = Inches(0.35)
            for (n1, x1, y1), (n2, x2, y2) in zip(nums, nums[1:]):
                if n2 != n1 + 1:
                    continue
                back = (abs(y2 - y1) < row and x2 < x1) or (y2 < y1 - row and x2 <= x1 + Inches(0.3))
                if back:
                    out.append(f"Slide {i}: ORDER-01 番号 {n1}→{n2} の位置が読む順（左→右、上→下）と逆になっている")
                    break
        for sh in sl.shapes:
            if not getattr(sh, "has_chart", False) or not sh.has_chart:
                continue
            ch = sh.chart
            if ch.chart_type not in (XL_CHART_TYPE.COLUMN_CLUSTERED, XL_CHART_TYPE.COLUMN_STACKED,
                                     XL_CHART_TYPE.COLUMN_STACKED_100):
                continue
            try:
                cats = [str(c) for c in ch.plots[0].categories]
            except Exception:
                continue
            if not cats:
                continue
            slot = sh.width / 914400 * 0.85 / len(cats)
            if max(_text_w_in(c, 12) for c in cats) > slot * 2:
                out.append(f"Slide {i}: CHART-03 縦棒の項目名が長く、縦に折れて読みにくい — 横棒（add_bar_chart）にする")
    return out


def main():
    if len(sys.argv) < 2:
        print("Usage: python verify_pptx.py <file.pptx>")
        sys.exit(1)

    import paths as _paths
    filepath = _paths.check_path(sys.argv[1])
    prs, errors, warnings, footer_count, svg_total = verify_pptx(filepath)
    total_shapes = sum(len(sl.shapes) for sl in prs.slides)

    print(f"\nSlide count: {len(prs.slides)}")
    print(
        f"Slide dimensions: {prs.slide_width/914400:.3f}\" x "
        f"{prs.slide_height/914400:.3f}\""
    )
    print(f"Total shapes: {total_shapes}")
    print(f"SVG elements: {svg_total}")
    print(f"Footer/PageNum slides: {footer_count}/{len(prs.slides) - 1}")

    if errors:
        for e in errors:
            print(f"  FAIL: {e}")
    if warnings:
        for w in warnings:
            print(f"  WARN: {w}")
    if not errors and not warnings:
        print("\nALL CHECKS PASSED")
    elif not errors:
        print(f"\nWARNINGS ({len(warnings)}) — review above")
    else:
        print(f"\n{len(errors)} ERROR(S) FOUND — fix required")
        sys.exit(1)


if __name__ == "__main__":
    main()
