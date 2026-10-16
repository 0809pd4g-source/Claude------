"""
master_to_theme.py — スライドコンテンツからカラーテーマ JSON を自動生成

PowerPoint ファイルの実際のスライド要素（図形塗り・テキスト色・線色・表セル）を
スキャンし、使用頻度と輝度・彩度から 9 つのデザイントークンにマッピングする。
テーマ XML ではなくコンテンツベースで抽出するため、実際に使われている色と一致する。

使い方:
  # コマンドライン
  python master_to_theme.py path/to/client.pptx "Client XYZ"

  # Python API
  from master_to_theme import extract_and_save
  extract_and_save("client.pptx", "Client XYZ")

トークンマッピングロジック（コンテンツベース）:
  primary      : 最も頻出する中輝度・高彩度の塗り色（バッジ・ヘッダー等）
  primary_dark : primary と同系色の暗い変種（primary の -50% 輝度）
  primary_light: primary と同系色の薄い変種（高輝度帯で発見 or 計算値）
  background   : #FFFFFF（固定）
  surface      : ごく薄い有彩色の塗り（カード背景等）
  text_heading : 最も暗いテキスト色
  text_body    : 2 番目に暗いテキスト色（または text_heading を薄めた色）
  text_muted   : 中間輝度のテキスト色（注釈・副次ラベル）
  border       : 薄いグレー系の線・塗り

フォント抽出ロジック:
  font_heading : <a:majorFont> から取得。システムフォントの場合はタイトルプレースホルダーの
                 使用頻度から推定
  font_body    : <a:minorFont> から取得。システムフォントの場合は本文ランの使用頻度から推定
"""

import os
import sys
import json
import colorsys
from collections import Counter

_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)
import paths as _paths

_SKILL_DIR   = _paths.SKILL_DIR
# 追加テーマはユーザーデータ側（~/.acnpptx/themes）に保存する。スキル本体は読み取り専用
_THEMES_DIR  = _paths.USER_THEMES_DIR


# ── 色ユーティリティ ──────────────────────────────────────────────────────────

def _parse_hex(hex_str: str) -> tuple:
    h = hex_str.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _to_hex(r: int, g: int, b: int) -> str:
    return f"#{r:02X}{g:02X}{b:02X}"


def _darken(hex_str: str, factor: float) -> str:
    """factor=0.5 → 50% の明るさに暗くする"""
    r, g, b = _parse_hex(hex_str)
    return _to_hex(int(r * factor), int(g * factor), int(b * factor))


def _lighten(hex_str: str, factor: float) -> str:
    """factor=0.85 → white に 85% 近づける"""
    r, g, b = _parse_hex(hex_str)
    return _to_hex(
        int(r + (255 - r) * factor),
        int(g + (255 - g) * factor),
        int(b + (255 - b) * factor),
    )


def _luminance(hex_str: str) -> float:
    r, g, b = [c / 255 for c in _parse_hex(hex_str)]
    return 0.299 * r + 0.587 * g + 0.114 * b


def _saturation(hex_str: str) -> float:
    """HLS 彩度（0〜1）"""
    r, g, b = [c / 255 for c in _parse_hex(hex_str)]
    _, _, s = colorsys.rgb_to_hls(r, g, b)
    return s


def _hue(hex_str: str) -> float:
    """色相（0〜360°）"""
    r, g, b = [c / 255 for c in _parse_hex(hex_str)]
    h, _, _ = colorsys.rgb_to_hls(r, g, b)
    return h * 360


def _hue_diff(h1: str, h2: str) -> float:
    """2色の色相差（0〜180°）"""
    d = abs(_hue(h1) - _hue(h2))
    return min(d, 360 - d)


def _contrast_text(hex_bg: str) -> str:
    return "#FFFFFF" if _luminance(hex_bg) < 0.5 else "#000000"


def _is_near_white(hex_str: str, threshold: float = 0.92) -> bool:
    return _luminance(hex_str) >= threshold


def _is_near_black(hex_str: str, threshold: float = 0.12) -> bool:
    return _luminance(hex_str) <= threshold


# ── フォント抽出 ─────────────────────────────────────────────────────────────

# Office/OS デフォルトフォント（ブランドフォントではない）
_SYSTEM_FONTS = frozenset({
    "Calibri", "Calibri Light", "Arial", "Arial Narrow", "Arial Black",
    "Times New Roman", "Helvetica", "Helvetica Neue", "Georgia", "Verdana",
    "Tahoma", "Trebuchet MS", "Symbol", "Wingdings", "Courier New",
    "Comic Sans MS", "Segoe UI", "Segoe UI Light", "Segoe UI Semibold",
    "Century Gothic", "Garamond", "Palatino Linotype", "Franklin Gothic Medium",
})
_OFFICE_PLACEHOLDERS = frozenset({"+mj-lt", "+mn-lt", "+mj-ea", "+mn-ea",
                                   "+mj-cs", "+mn-cs"})


def _is_system_font(name: str | None) -> bool:
    """システム/Office デフォルトフォントかどうか判定"""
    return (name is None
            or name in _SYSTEM_FONTS
            or name in _OFFICE_PLACEHOLDERS
            or name.startswith("+"))


# ── スライドコンテンツから色を収集 ───────────────────────────────────────────

_NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
_NS   = {"a": _NS_A}


def _font_scheme_from_master(prs) -> tuple:
    """
    スライドマスターのテーマ XML から <a:fontScheme> を読み取る。

    Returns:
        (heading_font, body_font) — 見つからない場合やシステムフォントの場合は None
    """
    for master in prs.slide_masters:
        for rel in master.part.rels.values():
            if "theme" not in rel.reltype.lower():
                continue
            import safexml
            tree = safexml.fromstring(rel.target_part.blob)
            scheme = tree.find(".//a:fontScheme", _NS)
            if scheme is None:
                continue
            major = scheme.find("a:majorFont/a:latin", _NS)
            minor = scheme.find("a:minorFont/a:latin", _NS)
            heading = (major.get("typeface") or None) if major is not None else None
            body    = (minor.get("typeface") or None) if minor is not None else None
            return heading, body
    return None, None


def _count_fonts_in_slides(prs, max_slides: int = 15) -> tuple:
    """
    スライド内のタイトル vs 本文の <a:latin typeface> 使用頻度をカウント。

    Returns:
        (title_counter, body_counter)
    """
    title_c: Counter = Counter()
    body_c:  Counter = Counter()

    _TITLE_TYPES = {1, 3, 13}   # TITLE, CENTER_TITLE, VERTICAL_TITLE

    for slide in list(prs.slides)[:max_slides]:
        title_phs = {ph.placeholder_format.idx
                     for ph in slide.placeholders
                     if ph.placeholder_format.type.value in _TITLE_TYPES}

        for shape in slide.shapes:
            if not shape.has_text_frame:
                continue
            is_title = (hasattr(shape, "placeholder_format")
                        and shape.placeholder_format is not None
                        and shape.placeholder_format.idx in title_phs)
            target = title_c if is_title else body_c

            for rpr in shape._element.iter(f"{{{_NS_A}}}rPr"):
                latin = rpr.find(f"{{{_NS_A}}}latin")
                if latin is not None:
                    tf = latin.get("typeface")
                    if tf:
                        target[tf] += 1

    return title_c, body_c


def _extract_fonts_from_prs(prs) -> dict:
    """
    Presentation オブジェクトから見出し・本文フォント名を抽出する。

    戦略:
      1. スライドマスターの <a:fontScheme> から読み取り（意図されたブランドフォント）
      2. システムフォントの場合、タイトル/本文プレースホルダーの使用頻度でフォールバック
      3. システムフォントをフィルタしてブランドフォントを浮上させる

    Returns:
        {"font_heading": str|None, "font_body": str|None}
    """
    heading, body = _font_scheme_from_master(prs)

    if _is_system_font(heading) or _is_system_font(body):
        title_c, body_c = _count_fonts_in_slides(prs)
        brand_title = [f for f, _ in title_c.most_common() if not _is_system_font(f)]
        brand_body  = [f for f, _ in body_c.most_common()  if not _is_system_font(f)]

        if _is_system_font(heading):
            heading = brand_title[0] if brand_title else (brand_body[0] if brand_body else None)
        if _is_system_font(body):
            body = brand_body[0] if brand_body else (brand_title[0] if brand_title else None)

    if _is_system_font(heading):
        heading = None
    if _is_system_font(body):
        body = None

    return {"font_heading": heading, "font_body": body}


def _build_theme_map(prs) -> dict:
    """
    スライドマスターのテーマ XML から schemeClr 名 → hex の辞書を構築する。
    WINDOW/WINDOWTEXT は OS 依存なので黒/白に置換。
    """
    theme_map: dict = {}
    for master in prs.slide_masters:
        for rel in master.part.rels.values():
            if "theme" not in rel.reltype.lower():
                continue
            import safexml
            tree = safexml.fromstring(rel.target_part.blob)
            clr_el = tree.find(".//a:clrScheme", _NS)
            if clr_el is None:
                continue
            for child in clr_el:
                tag = child.tag.split("}")[1]
                for sub in child:
                    val = sub.get("val") or sub.get("lastClr", "")
                    if not val:
                        continue
                    if val.upper() in ("WINDOWTEXT", "WINDOW"):
                        theme_map[tag] = "#000000" if "dk" in tag.lower() or tag == "tx1" else "#FFFFFF"
                    else:
                        theme_map[tag] = "#" + val.upper()
            break  # 最初のマスターだけ使用
    # bg1/tx1 エイリアス
    if "bg1" not in theme_map:
        theme_map["bg1"] = theme_map.get("lt1", "#FFFFFF")
    if "tx1" not in theme_map:
        theme_map["tx1"] = theme_map.get("dk1", "#000000")
    return theme_map


def _resolve_color_el(el, theme_map: dict) -> str | None:
    """
    <a:solidFill> 直下の色要素（srgbClr / schemeClr / sysClr）を hex に解決する。
    schemeClr の lumMod / lumOff / shade / tint も計算する。
    """
    for child in el:
        tag = child.tag.split("}")[1]

        if tag == "srgbClr":
            val = child.get("val", "")
            if len(val) == 6:
                return "#" + val.upper()

        elif tag == "sysClr":
            last = child.get("lastClr", "")
            if len(last) == 6:
                return "#" + last.upper()

        elif tag == "schemeClr":
            base = theme_map.get(child.get("val", ""))
            if not base:
                continue
            r0, g0, b0 = _parse_hex(base)
            h, l, s = colorsys.rgb_to_hls(r0 / 255, g0 / 255, b0 / 255)

            for mod in child:
                mod_tag = mod.tag.split("}")[1]
                v = int(mod.get("val", "100000")) / 100000
                if mod_tag == "lumMod":
                    l = max(0.0, min(1.0, l * v))
                elif mod_tag == "lumOff":
                    l = max(0.0, min(1.0, l + v))
                elif mod_tag == "shade":
                    l = max(0.0, min(1.0, l * v))
                elif mod_tag == "tint":
                    l = max(0.0, min(1.0, l + (1 - l) * v))

            r1, g1, b1 = colorsys.hls_to_rgb(h, l, s)
            return _to_hex(int(r1 * 255), int(g1 * 255), int(b1 * 255))

    return None


def _scan_xml_for_colors(element, theme_map: dict,
                          fill_c: Counter, text_c: Counter, line_c: Counter):
    """
    XML ツリー全体の solidFill 要素を走査し、親タグで用途（塗り/テキスト/線）を分類。
    DrawingML(a:) と PresentationML(p:) 両方のネームスペースに対応するため、
    ネームスペースに依存しない .iter() でまとめて取得する。
    """
    _FILL_PARENTS = {"spPr", "grpSpPr", "tcPr", "bgPr", "style"}
    _LINE_PARENTS = {"ln", "lnRef", "uFill", "lnStyleLst"}
    _TEXT_PARENTS = {"rPr", "endParaRPr", "defRPr", "pPr"}

    for sf in element.iter(f"{{{_NS_A}}}solidFill"):
        parent = sf.getparent()
        if parent is None:
            continue
        parent_tag = parent.tag.split("}")[1]
        c = _resolve_color_el(sf, theme_map)
        if not c:
            continue
        if parent_tag in _TEXT_PARENTS:
            text_c[c] += 1
        elif parent_tag in _LINE_PARENTS:
            line_c[c] += 1
        elif parent_tag in _FILL_PARENTS:
            fill_c[c] += 1
        # bgFillStyleLst, fmtScheme 等テーマ定義内は無視


def _collect_colors_from_prs(prs, max_slides: int = 10) -> tuple:
    """
    スライドの全図形・テキスト・表を XML レベルで走査し、
    schemeClr（テーマ参照色）を解決した上で
    (fill_counter, text_counter, line_counter) を返す。
    """
    fill_c: Counter = Counter()
    text_c: Counter = Counter()
    line_c: Counter = Counter()

    theme_map = _build_theme_map(prs)

    # スライドマスター + レイアウト
    for master in prs.slide_masters:
        _scan_xml_for_colors(master._element, theme_map, fill_c, text_c, line_c)
        for layout in master.slide_layouts:
            _scan_xml_for_colors(layout._element, theme_map, fill_c, text_c, line_c)

    # 通常スライド（最大 max_slides 枚）
    for slide in list(prs.slides)[:max_slides]:
        _scan_xml_for_colors(slide._element, theme_map, fill_c, text_c, line_c)

    return fill_c, text_c, line_c


# ── 色→トークン マッピング ───────────────────────────────────────────────────

def _map_tokens_from_colors(fill_c: Counter, text_c: Counter, line_c: Counter) -> dict:
    """使用頻度・輝度・彩度から 9 トークンに自動マッピング"""

    all_fills = fill_c.most_common()

    # ── primary 候補: 中輝度（0.15〜0.80）+ 高彩度（>0.18）の塗り色 ──
    primary_candidates = [
        c for c, _ in all_fills
        if _saturation(c) > 0.18
        and 0.15 < _luminance(c) < 0.80
        and not _is_near_white(c)
    ]
    primary = primary_candidates[0] if primary_candidates else "#4472C4"

    # ── primary と同系色（色相差 < 45°）のグループ ──
    family = [(c, n) for c, n in all_fills if _hue_diff(c, primary) < 45]

    # primary_dark: 同系色で primary より暗いもの
    darker = sorted(
        [c for c, _ in family if _luminance(c) < _luminance(primary) - 0.05],
        key=_luminance
    )
    primary_dark = darker[0] if darker else _darken(primary, 0.50)

    # primary_light: 同系色で高輝度（>0.80）かつ彩度がある
    lighter = sorted(
        [c for c, _ in family
         if _luminance(c) > 0.80 and _saturation(c) > 0.05 and not _is_near_white(c)],
        key=_luminance, reverse=True
    )
    primary_light = lighter[0] if lighter else _lighten(primary, 0.82)

    # ── background: 固定 #FFFFFF ──
    background = "#FFFFFF"

    # ── surface: 非常に薄い有彩色塗り（luminance > 0.90 かつ彩度 > 0.03）──
    surface_candidates = [
        c for c, _ in all_fills
        if _luminance(c) > 0.90 and _saturation(c) > 0.03 and not _is_near_white(c, 0.97)
    ]
    surface = surface_candidates[0] if surface_candidates else _lighten(primary, 0.93)

    # ── テキスト色 ──
    all_texts = text_c.most_common()

    # text_heading: 最も暗いテキスト（彩度問わず）
    dark_texts = sorted([c for c, _ in all_texts if _luminance(c) < 0.35], key=_luminance)
    text_heading = dark_texts[0] if dark_texts else "#000000"

    # text_body: 暗め（<0.40）かつグレー系（彩度 <0.20）のテキスト
    gray_body = [
        c for c, _ in all_texts
        if _luminance(c) < 0.40 and _saturation(c) < 0.20
        and _luminance(c) > _luminance(text_heading) + 0.02
    ]
    text_body = gray_body[0] if gray_body else _lighten(text_heading, 0.20)

    # text_muted: 中輝度（0.30〜0.70）かつグレー系（彩度 <0.20）のテキスト
    muted_candidates = [
        c for c, _ in all_texts
        if 0.30 < _luminance(c) < 0.70 and _saturation(c) < 0.20
    ]
    text_muted = muted_candidates[0] if muted_candidates else _lighten(text_heading, 0.50)

    # ── border: 薄いグレー系（線優先、なければ塗り）──
    border_from_lines = [
        c for c, _ in line_c.most_common()
        if 0.65 < _luminance(c) < 0.95 and _saturation(c) < 0.15
    ]
    border_from_fills = [
        c for c, _ in all_fills
        if 0.70 < _luminance(c) < 0.93 and _saturation(c) < 0.10
    ]
    border = (
        border_from_lines[0] if border_from_lines
        else border_from_fills[0] if border_from_fills
        else _lighten(text_heading, 0.80)
    )

    return {
        "primary":       primary,
        "primary_light": primary_light,
        "primary_dark":  primary_dark,
        "background":    background,
        "surface":       surface,
        "text_heading":  text_heading,
        "text_body":     text_body,
        "text_muted":    text_muted,
        "border":        border,
    }


# ── メイン抽出 API ────────────────────────────────────────────────────────────

def extract_colors_from_master(pptx_path: str) -> dict:
    """
    スライドコンテンツ（図形・テキスト・表・スライドマスター）から色を収集し、
    デザイントークンにマッピングして返す。

    Returns:
        {
          "scheme_name": str,
          "raw": {"fill": {...}, "text": {...}, "line": {...}},  # 頻度上位 10 色
          "tokens": {primary, primary_light, ...}
        }
    """
    from pptx import Presentation

    prs = Presentation(pptx_path)
    fill_c, text_c, line_c = _collect_colors_from_prs(prs)
    tokens = _map_tokens_from_colors(fill_c, text_c, line_c)
    fonts  = _extract_fonts_from_prs(prs)

    # raw: デバッグ用に頻度上位 10 色を記録
    raw = {
        "fill_top10":  dict(fill_c.most_common(10)),
        "text_top10":  dict(text_c.most_common(10)),
        "line_top10":  dict(line_c.most_common(10)),
    }

    return {
        "scheme_name": os.path.basename(pptx_path),
        "raw":    raw,
        "tokens": tokens,
        "fonts":  fonts,
    }


_TOKEN_LABELS = {
    "primary":       "メインアクション・強調",
    "primary_light": "背景ハイライト",
    "primary_dark":  "カバー背景・区切り",
    "background":    "スライド背景",
    "surface":       "カード・ボックス背景",
    "text_heading":  "見出しテキスト",
    "text_body":     "本文テキスト",
    "text_muted":    "注釈・補助テキスト",
    "border":        "枠線・区切り線",
}
_TOKEN_ORDER = list(_TOKEN_LABELS.keys())


def _print_token_preview(result: dict, theme_name: str):
    """抽出したトークンをターミナルに出力する（GUI なし）"""
    tokens = result["tokens"]
    fonts  = result.get("fonts", {})
    print(f"\n=== テーマカラー抽出結果: {theme_name} ===")
    print(f"元ファイル: {result['scheme_name']}\n")
    print(f"{'Token':<16}  {'HEX':<9}  用途")
    print("-" * 52)
    for token in _TOKEN_ORDER:
        label = _TOKEN_LABELS.get(token, "")
        print(f"{token:<16}  {tokens[token]:<9}  {label}")
    print()
    print(f"{'Font':<16}  Name")
    print("-" * 52)
    print(f"{'font_heading':<16}  {fonts.get('font_heading') or '(未検出)'}")
    print(f"{'font_body':<16}  {fonts.get('font_body') or '(未検出)'}")
    print()


# ── レイアウト解析 ────────────────────────────────────────────────────────────

_CATEGORY_RULES = [
    ("agenda", ("agenda", "contents", "目次", "アジェンダ")),
    ("closing", ("salutation", "thank", "closing", "終わり")),
    ("section", ("section", "divider", "title master", "中扉", "セクション")),
    ("cover", ("title:", "title slide", "cover", "表紙", "タイトル スライド")),
    ("blank", ("blank", "白紙")),
    ("quote", ("quote",)),
    ("stats", ("statistic", "stats")),
    ("team", ("team",)),
    ("key_message", ("key message",)),
]
_DARK_WORDS = ("black", "dark", "gradient", "purple", "core")


def _categorize_layout(name: str, has_title: bool = True) -> str:
    n = name.lower()
    for cat, words in _CATEGORY_RULES:
        if any(w in n for w in words):
            if cat == "blank" and has_title:
                return "content"   # "Blank - Light" でもタイトル枠があれば本文用
            return cat
    return "content"


def analyze_layouts(pptx_path: str) -> dict:
    """レイアウト名から all_layouts / layout_indices / cover_text_color / layout_notes を推定する。

    推定は名前ベースなので、プレビュー画像（build_master_previews.py）で目視確認すること。
    """
    from pptx import Presentation
    from pptx.util import Emu

    prs = Presentation(pptx_path)
    layouts = list(prs.slide_layouts)
    def _has(l, idx):
        return any(ph.placeholder_format.idx == idx for ph in l.placeholders)

    all_layouts = [{"idx": i, "name": l.name, "category": _categorize_layout(l.name, _has(l, 0))}
                   for i, l in enumerate(layouts)]

    def first(cat):
        return next((l["idx"] for l in all_layouts if l["category"] == cat), None)

    def ph_count(i):
        return sum(1 for ph in layouts[i].placeholders
                   if ph.placeholder_format.idx not in (10, 11, 12, 20, 21) or ph.placeholder_format.idx == 0)

    # 本文: タイトルがあり、本文プレースホルダーが少ない content レイアウトを優先
    content_cands = [l["idx"] for l in all_layouts if l["category"] == "content"]
    content = None
    # タイトル＋パンくず（idx 11）を持つ本文レイアウトを最優先
    with_bc = [i for i in content_cands if _has(layouts[i], 0) and _has(layouts[i], 11)]
    if with_bc:
        content = min(with_bc, key=ph_count)
    for i in ([] if content is not None else content_cands):
        n = layouts[i].name.lower()
        if "headline only" in n or "title only" in n or "タイトルのみ" in n:
            content = i
            break
    if content is None and content_cands:
        content = min(content_cands, key=ph_count)

    li = {}
    for role, idx in (("cover", first("cover")), ("content", content), ("section", first("section")),
                      ("agenda", first("agenda")), ("closing", first("closing")), ("blank", first("blank"))):
        if idx is not None:
            li[role] = idx
    # 表紙バリエーション（cover, cover_2, ...）
    covers = [l["idx"] for l in all_layouts if l["category"] == "cover"]
    for k, idx in enumerate(covers[1:], start=2):
        li[f"cover_{k}"] = idx

    cover_name = layouts[li["cover"]].name.lower() if "cover" in li else ""
    cover_text_color = "WHITE" if any(w in cover_name for w in _DARK_WORDS) else "BLACK"

    notes = {}
    if content is not None:
        title = next((ph for ph in layouts[content].placeholders if ph.placeholder_format.idx == 0), None)
        bc = next((ph for ph in layouts[content].placeholders if ph.placeholder_format.idx == 11), None)
        notes["content"] = {
            "title_idx": 0 if title is not None else None,
            "title_y": round(Emu(title.top).inches, 2) if title is not None else 0.42,
            "title_h": round(Emu(title.height).inches, 2) if title is not None else 0.48,
            "breadcrumb_idx": 11 if bc is not None else None,
            "message_line_idx": None,
            "content_area_y": 1.5,
            "note": f"Layout {content}: '{layouts[content].name}'（自動推定）",
        }
    for role in ("cover", "section"):
        if role in li:
            l = layouts[li[role]]
            notes[role] = {
                "background": "dark" if any(w in l.name.lower() for w in _DARK_WORDS) else "white",
                "note": f"Layout {li[role]}: '{l.name}'（自動推定）",
                "placeholders": {
                    f"idx_{ph.placeholder_format.idx}": {"role": str(ph.placeholder_format.type).split(".")[-1].split(" ")[0].lower(),
                                                         "note": ph.name}
                    for ph in l.placeholders if ph.placeholder_format.idx not in (20, 21)
                },
            }
    return {"all_layouts": all_layouts, "layout_indices": li,
            "cover_text_color": cover_text_color, "layout_notes": notes}


# ── メイン API ────────────────────────────────────────────────────────────────

def extract_and_save(
    pptx_path: str,
    theme_name: str | None = None,
    preview: bool = True,
) -> str | None:
    """
    スライドコンテンツから色を抽出し、JSON を保存する。
    GUI（Tkinter）は一切使用しない。

    Args:
        pptx_path : 解析する .pptx/.potx のパス
        theme_name: テーマ名（None の場合はファイル名から自動推定）
        preview   : True = 抽出結果をターミナルに表示してから保存

    Returns:
        保存した JSON のパス
    """
    if theme_name is None:
        theme_name = os.path.splitext(os.path.basename(pptx_path))[0]

    result = extract_colors_from_master(pptx_path)

    if preview:
        _print_token_preview(result, theme_name)

    os.makedirs(_THEMES_DIR, exist_ok=True)
    safe_name = _paths.safe_theme_name(theme_name)
    out_path  = os.path.join(_THEMES_DIR, f"{safe_name}.json")

    # スライドマスター pptx を ~/.acnpptx/masters/ にコピー（テンプレート再利用）
    masters_dir = _paths.USER_MASTERS_DIR
    os.makedirs(masters_dir, exist_ok=True)
    master_dst  = os.path.join(masters_dir, f"{safe_name}.pptx")
    import shutil as _shutil
    _shutil.copy2(pptx_path, master_dst)
    template_rel = f"masters/{safe_name}.pptx"   # DATA_DIR 基準（paths.resolve_theme_file）

    fonts = result.get("fonts", {})
    layout_info = analyze_layouts(pptx_path)
    payload = {
        "name":        theme_name,
        "description": f"Auto-extracted from {os.path.basename(pptx_path)}",
        "template":    template_rel,
        "cover_text_color": layout_info["cover_text_color"],
        "layout_indices": layout_info["layout_indices"],
        "layout_notes": layout_info["layout_notes"],
        "tokens":      result["tokens"],
        # フォント名 — 検出不可（システムフォントのみ）の場合は null
        "font_heading": fonts.get("font_heading"),
        "font_body":    fonts.get("font_body"),
        "all_layouts": layout_info["all_layouts"],
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    return out_path


# ── コマンドライン実行 ────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使い方: python master_to_theme.py <path/to/template.pptx> [theme_name]")
        print("例:     python master_to_theme.py client.pptx \"Client XYZ\"")
        sys.exit(1)

    pptx = _paths.check_path(sys.argv[1])
    name = sys.argv[2] if len(sys.argv) >= 3 else None

    saved = extract_and_save(pptx, name)
    if saved:
        print(f"Saved: {saved}")
    else:
        print("Failed.")
        sys.exit(1)
