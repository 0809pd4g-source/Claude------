"""
skeleton.py — 人が作ったスライドの「配置の骨格」（grammar/skeletons.json）に中身を流し込んで描く。

骨格は、図形の種類・相対位置・大きさ・線・色の役割・文字枠（役割と容量）・繰り返し単位だけを持つ。
描くときに:
  - 本文領域（box）に合わせて拡大縮小する（円・アイコン・画像は縦横比を保つ）
  - 繰り返し単位は中身の個数に合わせて並べ直す（単位の大きさを詰め、間隔は保つ）
  - 色の役割はテーマの色に置き換える（他社色は紫系に寄せる）。角丸は角のある形にする
  - 文字は許可サイズに丸め、枠に収まるサイズまで下げる

使い方:
    import skeleton
    sk = skeleton.get("K-012")
    skeleton.fields(sk)                  # 埋める項目の一覧（units / 固定項目）
    skeleton.render(ctx, sk, content, box)
content の形（項目名は fields() の結果）:
    {"units": [{"num": "1", "head": "…", "body": ["…", "…"], "icon": {"asset": "1234"}}, …],
     "band1": "…", "body1": ["…"], "table1": {"columns": [...], "rows": [[...]]}, "chart1": {...}, "img1": {...}}
"""

import copy
import json
import math
import os

from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE as S
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

import helpers as _h
import paths as _paths

_GRAMMAR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "grammar")
_CACHE = {}

ALLOWED_SIZES = (44, 40, 36, 28, 18, 16, 14, 12)

GEOM = {
    "rect": S.RECTANGLE, "ellipse": S.OVAL, "homePlate": S.PENTAGON, "chevron": S.CHEVRON,
    "triangle": S.ISOSCELES_TRIANGLE, "rtTriangle": S.RIGHT_TRIANGLE, "rightArrow": S.RIGHT_ARROW,
    "leftArrow": S.LEFT_ARROW, "downArrow": S.DOWN_ARROW, "upArrow": S.UP_ARROW,
    "leftRightArrow": S.LEFT_RIGHT_ARROW, "upDownArrow": S.UP_DOWN_ARROW, "notchedRightArrow": S.NOTCHED_RIGHT_ARROW,
    "pentagon": S.REGULAR_PENTAGON, "flowChartDocument": S.FLOWCHART_DOCUMENT, "foldedCorner": S.FOLDED_CORNER,
    "can": S.CAN, "flowChartMagneticDisk": S.FLOWCHART_MAGNETIC_DISK, "diamond": S.DIAMOND,
    "flowChartDecision": S.FLOWCHART_DECISION, "parallelogram": S.PARALLELOGRAM, "trapezoid": S.TRAPEZOID,
    "hexagon": S.HEXAGON, "octagon": S.OCTAGON, "donut": S.DONUT, "blockArc": S.BLOCK_ARC, "arc": S.ARC,
    "leftBracket": S.LEFT_BRACKET, "rightBracket": S.RIGHT_BRACKET, "leftBrace": S.LEFT_BRACE,
    "rightBrace": S.RIGHT_BRACE, "wedgeRectCallout": S.RECTANGULAR_CALLOUT, "borderCallout1": S.LINE_CALLOUT_1,
    "callout1": S.LINE_CALLOUT_1_NO_BORDER, "mathPlus": S.MATH_PLUS, "mathMultiply": S.MATH_MULTIPLY,
    "mathEqual": S.MATH_EQUAL, "mathMinus": S.MATH_MINUS, "plus": S.CROSS, "star5": S.STAR_5_POINT,
    "flowChartPredefinedProcess": S.FLOWCHART_PREDEFINED_PROCESS, "frame": S.FRAME, "halfFrame": S.HALF_FRAME,
    "corner": S.CORNER, "chord": S.CHORD, "pie": S.PIE, "curvedRightArrow": S.CURVED_RIGHT_ARROW,
    "curvedDownArrow": S.CURVED_DOWN_ARROW, "circularArrow": S.CIRCULAR_ARROW, "uturnArrow": S.U_TURN_ARROW,
    "stripedRightArrow": S.STRIPED_RIGHT_ARROW, "flowChartOffpageConnector": S.FLOWCHART_OFFPAGE_CONNECTOR,
    "flowChartDelay": S.FLOWCHART_DELAY, "cube": S.CUBE, "cloud": S.CLOUD,
}
ROUND_GEOMS = {"ellipse", "donut", "blockArc", "arc", "pie", "chord", "circularArrow"}


# ── データ ────────────────────────────────────────────────────
def load_all():
    if "all" not in _CACHE:
        p = os.path.join(_GRAMMAR, "skeletons.json")
        data = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {"skeletons": []}
        _CACHE["all"] = {s["id"]: s for s in data["skeletons"]}
    return _CACHE["all"]


def get(sid):
    sk = load_all().get(sid)
    if sk is None:
        raise KeyError(f"骨格 {sid} が grammar/skeletons.json に無い")
    return sk


def fields(sk):
    """埋める項目: {"units": [項目名…] / repeat ごと, "fixed": {項目名: 役割}}。"""
    out = {"repeat": [], "fixed": {}}
    for i, rp in enumerate(sk.get("repeat", [])):
        key = "units" if i == 0 else f"units{i + 1}"
        out["repeat"].append({"key": key, "n": rp["n"], "min": rp["min"], "max": rp["max"],
                              "fields": list(rp.get("unit_fields", {}).keys())})
    for name, f in sk.get("fixed", {}).items():
        out["fixed"][name] = f.get("role")
    return out


# ── 色 ────────────────────────────────────────────────────────
def color(role, kind="fill"):
    """色の役割 → テーマ色。他社色は明度で紫系に寄せる。"""
    if role in (None, "none", "inh"):
        return None
    if role == "white":
        return _h.WHITE
    if role == "black":
        return _h.BLACK if kind == "text" else _h.TEXT_BODY if kind == "line" else _h.BLACK
    if role == "gray_light":
        return _h.OFF_WHITE if kind == "fill" else _h.LIGHT_GRAY
    if role == "gray_mid":
        return _h.LIGHT_GRAY if kind == "fill" else _h.MID_GRAY
    if role == "gray_dark":
        return _h.MID_GRAY if kind != "text" else _h.TEXT_SUB
    if role == "purple_dark":
        return _h.DARKEST_PURPLE
    if role == "purple":
        return _h.CORE_PURPLE if kind == "fill" else _h.DARK_PURPLE
    if role == "purple_light" or role.endswith("_light"):
        return _h.LIGHTEST_PURPLE if kind == "fill" else _h.LIGHT_PURPLE
    # 他社色（青・緑・橙・赤など）: 濃い紫に寄せる
    return _h.DARK_PURPLE


def _is_dark(rgb):
    if rgb is None:
        return False
    r, g, b = rgb[0], rgb[1], rgb[2]
    return (0.299 * r + 0.587 * g + 0.114 * b) < 140


# ── 文字 ──────────────────────────────────────────────────────
def snap_size(pt):
    pt = pt or 14
    if pt >= 34:
        return 36
    if pt >= 25:
        return 28
    if pt >= 19:
        return 18
    if pt >= 17:
        return 16
    if pt >= 15:
        return 14
    if pt >= 13.5:
        return 14
    return 12


def _paras(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(v) for v in value]
    return str(value).split("\n")


# ── 配置の計算 ────────────────────────────────────────────────
def _relayout(sk, counts):
    """繰り返しの個数を counts に合わせた図形リスト（骨格座標系）と、単位ごとの項目対応を返す。"""
    shapes = copy.deepcopy(sk["shapes"])
    unit_maps = []          # repeat ごとに [ {field: shape_index}, … ]
    removed = set()
    added = []
    for ri, rp in enumerate(sk.get("repeat", [])):
        n0, n1 = rp["n"], counts[ri] if ri < len(counts) and counts[ri] else rp["n"]
        units = rp["units"]
        axis = rp["axis"]
        fmap = rp.get("unit_fields", {})          # field → 単位 0 の中での位置（units[0] の何番目か）
        lo = min(shapes[i]["x" if axis == "row" else "y"] for i in units[0])
        hi = max(shapes[i]["x" if axis == "row" else "y"] + shapes[i]["w" if axis == "row" else "h"] for i in units[-1])
        u_ext = max(shapes[i]["x" if axis == "row" else "y"] + shapes[i]["w" if axis == "row" else "h"] for i in units[0]) - lo
        gap = rp.get("gap", 0.1)
        between = rp.get("between", [])            # 単位の間に置く図形（矢印など）の index（単位 0 と 1 の間のもの）
        if n1 == n0:
            unit_maps.append([{f: u[pos] for f, pos in fmap.items() if pos < len(u)} for u in units])
            continue
        new_ext = (hi - lo - (n1 - 1) * gap) / n1
        f = new_ext / u_ext if u_ext else 1
        template = units[0]
        for u in units:
            removed.update(u)
        for b in rp.get("between_all", []):
            removed.add(b)
        maps = []
        k0 = "x" if axis == "row" else "y"
        s0 = "w" if axis == "row" else "h"
        for j in range(n1):
            start = lo + j * (new_ext + gap)
            m = {}
            for pos, i in enumerate(template):
                d = copy.deepcopy(shapes[i])
                off = d[k0] - lo
                keep_aspect = d.get("t") in ROUND_GEOMS or d.get("t") == "image"
                if keep_aspect and d[s0] <= new_ext:
                    center = lo + off + d[s0] / 2
                    rel = (center - lo) / u_ext if u_ext else 0.5
                    d[k0] = start + rel * new_ext - d[s0] / 2
                else:
                    d[k0] = start + off * f
                    d[s0] = d[s0] * f
                added.append(d)
                for fld, p in fmap.items():
                    if p == pos:
                        m[fld] = len(shapes) + len(added) - 1
            maps.append(m)
            if j < n1 - 1:
                for bi in between:
                    d = copy.deepcopy(shapes[bi])
                    gap_center = start + new_ext + gap / 2
                    d[k0] = gap_center - d[s0] / 2
                    added.append(d)
        unit_maps.append(maps)
    out = [s for i, s in enumerate(shapes) if i not in removed] + added
    # 消した図形の index を詰めた新しい index に付け替える
    remap, k = {}, 0
    for i in range(len(shapes)):
        if i not in removed:
            remap[i] = k
            k += 1
    for i in range(len(added)):
        remap[len(shapes) + i] = k + i
    unit_maps = [[{f: remap[i] for f, i in m.items() if i in remap} for m in maps] for maps in unit_maps]
    fixed = {name: remap[f["shape"]] for name, f in sk.get("fixed", {}).items() if f["shape"] in remap}
    return out, unit_maps, fixed


def _map(d, sx, sy, ox, oy):
    x, y, w, h = d["x"] * sx + ox, d["y"] * sy + oy, d["w"] * sx, d["h"] * sy
    if d.get("t") in ROUND_GEOMS or d.get("t") == "image":
        s = min(sx, sy)
        cx, cy = x + w / 2, y + h / 2
        w, h = d["w"] * s, d["h"] * s
        x, y = cx - w / 2, cy - h / 2
    return x, y, w, h


# ── 描画 ──────────────────────────────────────────────────────
def render(ctx, sk, content, box):
    """骨格 sk に content を流し込んで、box=(x, y, w, h) に描く。描いた図形のリストを返す。"""
    import compose as _c
    content = content or {}
    reps = sk.get("repeat", [])
    counts = []
    for i, rp in enumerate(reps):
        key = "units" if i == 0 else f"units{i + 1}"
        n = len(content.get(key) or []) or rp["n"]
        if not (rp["min"] <= n <= rp["max"]):
            ctx.warn(f"骨格 {sk['id']}: {key} の個数 {n} は推奨範囲 {rp['min']}〜{rp['max']} の外")
        counts.append(n)
    shapes, unit_maps, fixed = _relayout(sk, counts)
    W0, H0 = sk["size"]
    bx, by, bw, bh = box
    sx, sy = bw / W0, bh / H0
    # 値を図形 index に対応づける
    values = {}
    for ri, maps in enumerate(unit_maps):
        key = "units" if ri == 0 else f"units{ri + 1}"
        items = content.get(key) or []
        for j, m in enumerate(maps):
            it = items[j] if j < len(items) else {}
            for fld, idx in m.items():
                values[idx] = it.get(fld)
    for name, idx in fixed.items():
        if name in content:
            values[idx] = content[name]
        else:
            values.setdefault(idx, None)
    slide = ctx.slide
    drawn = []
    filled = []     # (x, y, w, h, rgb) … 文字枠の下にある塗りを探すため
    for i, d in enumerate(shapes):
        x, y, w, h = _map(d, sx, sy, bx, by)
        t = d.get("t")
        val = values.get(i)
        if t == "line":
            ln = d.get("line", {})
            fl = d.get("flip", [False, False])
            x1, y1, x2, y2 = x, y, x + w, y + h
            if fl[0]:
                x1, x2 = x2, x1
            if fl[1]:
                y1, y2 = y2, y1
            c = _c._connector(slide, x1, y1, x2, y2, color=color(ln.get("role"), "line") or _h.MID_GRAY,
                              width=max(0.75, min(2.25, ln.get("w", 0.75))), arrow=ln.get("tail") or ln.get("head"),
                              dash=ln.get("dash", "solid") != "solid",
                              elbow=bool(d.get("elbow") and "bent" in d["elbow"]))
            drawn.append(c)
            continue
        if t == "image":
            v = val if isinstance(val, dict) else {}
            if v:
                _c._place_visual(ctx, v, (x, y, w, h))
            else:
                ctx.warn(f"骨格 {sk['id']}: 画像枠（{d.get('img')}）が空")
            continue
        if t == "table":
            v = val if isinstance(val, dict) else {}
            if v:
                _c.m_table(ctx, (x, y, w, h), v)
            else:
                ctx.warn(f"骨格 {sk['id']}: 表の中身が無い")
            continue
        if t == "chart":
            v = val if isinstance(val, dict) else {}
            if v:
                _c.m_chart(ctx, (x, y, w, h), v)
            else:
                ctx.warn(f"骨格 {sk['id']}: グラフの中身が無い")
            continue
        slot = sk["slots"].get(d.get("slot")) if d.get("slot") else None
        if t == "text":
            if slot is None or val in (None, "", []):
                if slot is not None:
                    ctx.warn(f"骨格 {sk['id']}: 文字枠 {d.get('slot')}（{slot['role']}）が空")
                continue
            shp = None
        else:
            fill = color(d.get("fill"), "fill")
            ln = d.get("line")
            shp = _c._rect(slide, x, y, w, h, fill=fill, line=color(ln["role"], "line") if ln else None,
                           line_w=max(0.5, min(2.25, ln.get("w", 0.75))) if ln else 0.75,
                           dash=bool(ln and ln.get("dash", "solid") != "solid"),
                           shape=GEOM.get(t, S.RECTANGLE))
            if d.get("rot"):
                shp.rotation = d["rot"]
            drawn.append(shp)
            if fill is not None:
                filled.append((x, y, w, h, fill))
        if slot is None:
            continue
        if val in (None, "", []):
            ctx.warn(f"骨格 {sk['id']}: 文字枠 {d.get('slot')}（{slot['role']}）が空")
            continue
        paras = _paras(val)
        base = snap_size(slot.get("size"))
        sizes = [s for s in ALLOWED_SIZES if s <= base] or [12]
        bullet = "•" if (slot.get("bullets") or (isinstance(val, (list, tuple)) and len(val) > 1 and slot["role"] == "body")) else None
        # 小さな枠の短い文字は、余白分（+0.08in）を見込まずに判定する
        size, ok = _c.fit_size([(p, {}) for p in paras], max(0.2, w - (0.3 if bullet else 0.1)), h + 0.1, tuple(sizes),
                               4 if len(paras) > 1 else 0)
        if not ok:
            ctx.warn(f"骨格 {sk['id']}: 文字枠 {d.get('slot')} に収まらない（{sum(len(p) for p in paras)}字 / 目安 {slot.get('fit', slot.get('cap'))}字）")
        fill_rgb = color(d.get("fill"), "fill") if t != "text" else None
        if t == "text":   # 文字だけの枠: 真下にある塗り（最後に描いたもの）を背景とみなす
            cx_, cy_ = x + w / 2, y + h / 2
            for fx, fy, fw, fh, rgb in reversed(filled):
                if fx <= cx_ <= fx + fw and fy <= cy_ <= fy + fh:
                    fill_rgb = rgb
                    break
        tcol = _h.WHITE if _is_dark(fill_rgb) else (color(slot.get("color"), "text") or _h.TEXT_BODY)
        if tcol == _h.WHITE and not _is_dark(fill_rgb):
            tcol = _h.TEXT_BODY
        align = {"l": PP_ALIGN.LEFT, "ctr": PP_ALIGN.CENTER, "r": PP_ALIGN.RIGHT}.get(slot.get("align"), PP_ALIGN.LEFT)
        if bullet:
            align = PP_ALIGN.LEFT
        anchor = {"t": "t", "ctr": "m", "b": "b"}.get(slot.get("anchor"), "t")
        vert = slot.get("vert") and len("".join(paras)) <= 12
        if shp is None:
            tb = _c._textbox(slide, x, y, w, h, [(p, {"bullet": bullet}) if bullet else p for p in paras], size=size,
                             color=tcol, anchor=anchor, align=align, bold=slot.get("bold", False), space_after=4,
                             emphasis=ctx.emphasis)
            if vert:
                _set_vert(tb)
            drawn.append(tb)
        else:
            tf = shp.text_frame
            _c._bodypr(tf, anchor, (0.06, 0.03, 0.06, 0.03))
            for k, ptxt in enumerate(paras):
                p = tf.paragraphs[0] if k == 0 else tf.add_paragraph()
                p.alignment = align
                p.space_after = Pt(4)
                if bullet:
                    _c._bullet(p, bullet)
                _c._runs(p, ptxt, size, tcol, slot.get("bold", False), ctx.emphasis)
            if vert:
                _set_vert(shp)
    return drawn


def _set_vert(shape):
    """縦書き（東アジアの縦書き）にする。細い縦長の見出しセル用。"""
    from pptx.oxml.ns import qn
    bp = shape.text_frame._txBody.find(qn("a:bodyPr"))
    bp.set("vert", "eaVert")


# ── 見本の中身・検索・CLI ─────────────────────────────────────
_PHRASES = ["業務プロセスを標準化し", "現場の判断を早める", "データを一元管理する", "属人化した作業をなくす",
            "部門横断で効果を出す", "段階的に展開する", "運用ルールを定める", "品質とコストを両立する"]


def _dummy(role, cap, paras, k):
    cap = max(2, int(cap or 10))
    if role == "num":
        return str(k + 1)
    if role == "kpi":
        return f"{(k + 3) * 7}%"
    if role == "band":
        return ("見出し帯" + "テキスト" * 3)[:max(4, min(cap, 16))]
    if role in ("head", "label"):
        return (_PHRASES[k % len(_PHRASES)])[:max(3, cap)]
    if role == "note":
        return ("※ 前提や出典を書く" * 3)[:max(6, min(cap, 50))]
    n = max(1, min(int(paras or 1), 5))
    per = max(6, cap // n)
    out = []
    for i in range(n):
        s, j = "", k + i
        while len(s) < per:
            s += _PHRASES[j % len(_PHRASES)] + "、"
            j += 1
        out.append(s[:per].rstrip("、"))
    return out if n > 1 else out[0]


def where(sk, idx):
    """図形 idx の位置を「横 1〜5 / 縦 1〜4」で表す（content を書くときの目安）。"""
    W0, H0 = sk["size"]
    d = sk["shapes"][idx]
    cx, cy = (d["x"] + d["w"] / 2) / W0, (d["y"] + d["h"] / 2) / H0
    return f"横{min(5, int(cx * 5) + 1)}/縦{min(4, int(cy * 4) + 1)}"


def template(sk, sample=True):
    """content の雛形。sample=True なら見本の文字を、False なら文字枠の役割と目安字数を入れる。"""
    def val(slot, k):
        if sample:
            return _dummy(slot["role"], slot.get("fit", slot.get("cap")), slot.get("paras"), k)
        return f"<{slot['role']} {slot.get('fit', slot.get('cap'))}字 @{where(sk, slot['_idx'])}>"
    for i_, sh_ in enumerate(sk["shapes"]):
        if sh_.get("slot"):
            sk["slots"][sh_["slot"]]["_idx"] = i_
    c = {}
    for i, rp in enumerate(sk.get("repeat", [])):
        key = "units" if i == 0 else f"units{i + 1}"
        items = []
        for k in range(rp["n"]):
            u = {}
            for fld, pos in rp.get("unit_fields", {}).items():
                sh = sk["shapes"][rp["units"][0][pos]]
                if sh["t"] == "image":
                    u[fld] = {"asset": "<素材ID>"} if not sample else {"asset": ["0378", "0877", "1745", "1090", "1546", "1635"][k % 6]}
                elif sh.get("slot"):
                    u[fld] = val(sk["slots"][sh["slot"]], k)
            items.append(u)
        c[key] = items
    for name, f in sk.get("fixed", {}).items():
        sh = sk["shapes"][f["shape"]]
        if sh["t"] == "image":
            if sh.get("img") == "icon":
                c[name] = {"asset": "1635"} if sample else {"asset": f"<素材ID @{where(sk, f['shape'])}>"}
            else:
                c[name] = {"image": f"<画像パス @{where(sk, f['shape'])}>"}
        elif sh["t"] == "table":
            r_, c_ = sh["table"]["rows"], sh["table"]["cols"]
            c[name] = {"columns": [f"列{j + 1}" for j in range(c_)],
                       "rows": [["行見出し" if j == 0 else "内容" for j in range(c_)] for _ in range(max(1, r_ - 1))]}
        elif sh["t"] == "chart":
            c[name] = {"chart_type": "bar", "categories": ["A", "B", "C", "D"],
                       "series": [{"name": "値", "values": [3, 5, 4, 6]}], "title": "グラフ", "unit": "件"}
        elif sh.get("slot"):
            c[name] = val(sk["slots"][sh["slot"]], int("".join(ch for ch in name if ch.isdigit()) or 1) - 1)
    return c


def search(intent=None, relation=None, n_items=None, density=None, top=8):
    """意図・関係・項目数・密度で骨格を探す（点数の高い順）。"""
    res = []
    for sk in load_all().values():
        s = sk.get("score", 12) / 15
        if intent and sk.get("intent") == intent:
            s += 2
        if relation and sk.get("relation") == relation:
            s += 1.5
        if density and sk.get("density") == density:
            s += 0.5
        if n_items and sk.get("repeat"):
            rp = sk["repeat"][0]
            s += 1 if rp["min"] <= n_items <= rp["max"] else -1
        res.append((round(s, 2), sk))
    res.sort(key=lambda x: -x[0])
    return res[:top]


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="骨格（grammar/skeletons.json）を探す・雛形を出す")
    ap.add_argument("id", nargs="?", help="K-001 など。指定すると content の雛形を出す")
    ap.add_argument("--intent")
    ap.add_argument("--relation")
    ap.add_argument("--n", type=int, help="並べる項目の数")
    ap.add_argument("--density")
    ap.add_argument("--top", type=int, default=8)
    ap.add_argument("--sample", action="store_true", help="雛形に見本の文字を入れる")
    ap.add_argument("--map", help="項目名をその位置に書いた画像を作る（PowerPoint が必要）。例: --map k027.png")
    a = ap.parse_args()
    if a.id and a.map:
        _h.set_lang("ja")
        _h.load_theme("accenture")
        import compose
        sk = get(a.id)
        names = {}
        for i, rp in enumerate(sk.get("repeat", [])):
            key = "units" if i == 0 else f"units{i + 1}"
            names[key] = [{f: f"{key}[{k}].{f}" for f in rp.get("unit_fields", {})} for k in range(rp["n"])]
        for name in sk.get("fixed", {}):
            names[name] = name
        prs = compose.new_presentation()
        slide = compose.new_content_slide(prs, title=f"{sk['id']} 項目の位置", message="メッセージ")
        render(compose.Ctx(slide, prs, {}), sk, names, compose.body_box(slide))
        out = _paths.check_path(a.map, write=True)
        tmp = out + ".pptx"
        prs.save(tmp)
        import win32com.client
        app = win32com.client.Dispatch("PowerPoint.Application")
        app.AutomationSecurity = 3  # msoAutomationSecurityForceDisable
        p_ = app.Presentations.Open(tmp, ReadOnly=True, Untitled=False, WithWindow=False)
        try:
            p_.Slides(1).Export(out, "PNG", 1600, 900)
        finally:
            p_.Close()
        os.remove(tmp)
        print("map ->", out)
        raise SystemExit(0)
    if a.id:
        sk = get(a.id)
        print(f"{sk['id']}  {sk.get('name', '')}  [{sk.get('intent')}/{sk.get('relation')}/{sk.get('density')}]")
        print("  使う場面:", sk.get("use_when", ""))
        f = fields(sk)
        for r in f["repeat"]:
            print(f"  {r['key']}: {r['min']}〜{r['max']} 個（元 {r['n']} 個）, 項目 {r['fields']}")
        print("  固定項目:", ", ".join(f"{k}({v})" for k, v in f["fixed"].items()))
        print(json.dumps({"skeleton": sk["id"], "content": template(sk, a.sample)}, ensure_ascii=False, indent=1))
    else:
        for s, sk in search(a.intent, a.relation, a.n, a.density, a.top):
            rp = sk.get("repeat") or []
            rep = f"繰り返し {rp[0]['min']}〜{rp[0]['max']}" if rp else "固定"
            print(f"{sk['id']}  {s:>5}  {sk.get('intent', ''):<16} {str(sk.get('relation')):<10} {rep:<12} {sk.get('name', '')}")
            if sk.get("use_when"):
                print(f"         {sk['use_when']}")
