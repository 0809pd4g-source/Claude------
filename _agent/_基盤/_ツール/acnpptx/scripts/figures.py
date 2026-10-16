"""
figures.py — アイコンで描く概念図（v6.4、v6.5 で面の箱＋短い直角線に作り直し）。人の資料で多いのに、箱と文字だけでは描けなかった図。

  M-DIAGRAM-FLOW style="icon"  アイコン＋ラベルを矢印でつなぐ概念図（ソリューション概要・処理の流れ）。
                               戻り矢印（loop）、担い手の札（by: "AI" / "人"）、強調する段（highlight）。
  M-HUB        中央の主体と、周りの関係者・機能（3〜8）。関係の線にラベル（rel）。提案書の「全体像」で最も多い型。
  M-EQUATION   「A ＋ B × C ＝ 成果」の式。最後の項が結論（濃い紫の地）。
  M-ICONROW    アイコン＋見出し＋短い説明を横に並べる軽い部品（要旨・強み・提供価値）。箱で囲まない。

アイコンは item["icon"]（素材 ID / "q:英語の概念語" / {"q": ...}）か、pane の icons: "auto"（icon_q かラベルで検索）。
色の意味: 線・矢印は濃い紫か灰、明るい紫は強調する 1 か所だけ（結論・選んだ段）。
"""

import math

from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE as S
from pptx.enum.text import PP_ALIGN

import helpers as _h


def _c():
    import compose
    return compose


def _label_paras(it, size=14, sub=12, color=None, align=PP_ALIGN.CENTER, text_color=None):
    paras = []
    if it.get("label"):
        paras.append((it["label"], {"bold": True, "color": color or _h.DARKEST_PURPLE, "align": align, "size": size,
                                    "space_after": 2}))
    if it.get("text"):
        paras.append((it["text"], {"align": align, "size": sub, "color": text_color or _h.TEXT_BODY}))
    for t in it.get("items") or []:     # v6.8: 段・箱に箇条書きを足せる（名前と一言だけの中身の無い図にしない）
        paras.append((t, {"align": PP_ALIGN.LEFT, "size": sub, "bullet": "•", "color": text_color or _h.TEXT_BODY,
                          "space_after": 2}))
    return paras


def _fit_pair(c, items, w, h, sizes=(16, 14, 12), align=PP_ALIGN.CENTER):
    """全項目が高さ h に収まる最大の (見出しの大きさ, 説明の大きさ)。説明は見出しより 2pt 小さく、12pt 未満にしない。"""
    for ls in sizes:
        ts = max(12, ls - 2)
        if all(c.est_height(_label_paras(it, ls, ts, align=align), w, ls, 2) <= h for it in items):
            return ls, ts
    return sizes[-1], 12


def _icon_color(on):
    """アイコンの色。通常は濃い紫（構造の色）、強調する 1 つだけブランドの明るい紫のまま（紫の意味を固定する）。"""
    return None if on else _h.DARKEST_PURPLE


def _norm(items):
    """文字列だけの項目は見出しとして扱う。"""
    return [{"label": i["text"]} if set(i) == {"text"} else i for i in items]


def _tag(c, s, cx, top, text, dark=False):
    """担い手の札（AI / 人 など）。"""
    w = 0.3 + sum(c._char_w(ch, 12) for ch in text)
    t = c._rect(s, cx - w / 2, top, w, 0.24, fill=_h.DARK_PURPLE if dark else _h.WHITE,
                line=None if dark else _h.MID_GRAY, line_w=0.75)
    c._shape_text(t, text, 12, _h.WHITE if dark else _h.TEXT_SUB, False, inset=(0.02, 0, 0.02, 0), wrap=False)
    return 0.28


# ═══════════════════════════════════════════════════════════════
#  共通: 線の太さ・ノードの箱
# ═══════════════════════════════════════════════════════════════
# 線の太さは役割で決める（人の資料の実測）: 枠 0.75 / 組織図 1.0 / 図中の関係線 1.5 / 強調 2.25 / 主な流れ 2.25〜6。
# 細い線が成り立つのは、面（灰・淡紫の箱）が要素を区切っているとき。線だけを主役にして余白を横切らせない。
LINE_W = {"frame": 0.75, "tree": 1.0, "link": 1.5, "emph": 2.25, "flow": 2.25, "hub": 2.0, "hub_emph": 3.0}
# 強調する箱: 面（淡紫）と枠（濃い紫 2.25pt を箱にぴったり）の両方で兄弟の灰の箱と違える。
# 人の資料の強調の囲みは 2.25pt に固定で、枠と面の色の差をはっきり付ける（明るい紫の枠を灰の箱の外に置くと目立たない）
EMPH = {"fill": _h.LIGHTEST_PURPLE, "line": _h.DARKEST_PURPLE, "w": 2.25}
ICON_IN = 0.45      # 箱の中のアイコン（人の資料の中央値 0.47in）
ICON_TOP = 0.6      # 箱の上に置くアイコン


def _gray():
    return _h.MID_GRAY          # 向きの三角（人の資料は 969696。ブランドの灰で最も近い MID_GRAY）


def _node_paras(nd, size, tsz, on, align=PP_ALIGN.LEFT):
    return _label_paras(nd, size, tsz, _h.WHITE if on else _h.DARKEST_PURPLE, align,
                        text_color=_h.WHITE if on else None)


def _node_box(ctx, bx, by, bw, bh, nd, size, tsz, on, icon=True, accent=True, emph=False):
    """面の箱（灰。on は濃い紫の地に白抜き、emph は淡紫の面＋濃い紫の枠）に、左にアイコン（0.45in）、右に見出し＋説明。
    箱の図形を返す（コネクタの接続先）。"""
    c = _c()
    s = ctx.slide
    if emph and not on:
        box = c._rect(s, bx, by, bw, bh, fill=EMPH["fill"], line=EMPH["line"], line_w=EMPH["w"])
    else:
        box = c._rect(s, bx, by, bw, bh, fill=_h.DARKEST_PURPLE if on else _h.OFF_WHITE)
    if accent and not on:
        c._rect(s, bx, by, 0.06, bh, fill=_h.DARKEST_PURPLE if emph else _h.DARK_PURPLE)
    tx, tw = bx + 0.16, bw - 0.26
    if icon and nd.get("icon"):
        isz = min(ICON_IN, bh - 0.12)
        if c._place_visual(ctx, nd["icon"], (tx, by + (bh - isz) / 2, isz, isz),
                           color=_h.WHITE if on else _h.DARKEST_PURPLE) is not None:
            tx, tw = tx + isz + 0.14, tw - isz - 0.14
    c._textbox(s, tx, by, tw, bh, _node_paras(nd, size, tsz, on), size, anchor="m", space_after=2,
               emphasis=None if on else ctx.emphasis)
    return box


def _box_need(c, nodes, tw, sizes=(14, 12)):
    size, tsz = _fit_pair(c, nodes, tw, 9.0, sizes, align=PP_ALIGN.LEFT)
    need = max(c.est_height(_label_paras(nd, size, tsz, align=PP_ALIGN.LEFT), tw, size, 2) for nd in nodes)
    return size, tsz, need


# ═══════════════════════════════════════════════════════════════
#  M-DIAGRAM-FLOW style="icon"
# ═══════════════════════════════════════════════════════════════
def m_iconflow(ctx, r, d):
    """{"style": "icon", "nodes": [{"label": "会議動画", "text": "Teams の録画", "icon": "q:video meeting", "by": "人"},
                                   {"label": "議事録", "icon": "q:document", "by": "AI", "highlight": true}, ...],
        "loop": {"from": 3, "to": 1, "label": "ナレッジを追記"}}
    … 各段 = 上にアイコン（0.6in）＋担い手の札＋面の箱（見出し＋説明）。段の間は灰の三角。戻りは 2.25pt の線。"""
    c = _c()
    x, y, w, h = r
    s = ctx.slide
    nodes = _norm(c._items(d, "nodes"))
    n = len(nodes)
    if not n:
        return
    if n > 6:
        ctx.warn("M-DIAGRAM-FLOW(icon): ノードが 6 を超える（段をまとめるか、M-PIPELINE にする）")
    agap = 0.42
    cw = (w - agap * (n - 1)) / n
    loop = d.get("loop")
    loop_h = 0.6 if loop else 0
    isz = min(ICON_TOP, cw * 0.32)
    has_icon = any(nd.get("icon") for nd in nodes)
    has_by = any(nd.get("by") for nd in nodes)
    head = (isz + 0.12 if has_icon else 0) + (0.32 if has_by else 0)
    size, tsz = _fit_pair(c, nodes, cw - 0.24, h - head - loop_h - 0.2, (16, 14, 12))
    need = max(c.est_height(_label_paras(nd, size, tsz), cw - 0.24, size, 2) for nd in nodes) + 0.2
    bh = min(h - head - loop_h, max(need, min(need * 1.5, (h - head - loop_h) * 0.6)))
    block = head + bh + loop_h
    top = y + max(0, (h - block) / 2)
    by = top + head
    xs, boxes = [], []
    for i, nd in enumerate(nodes):
        bx = x + i * (cw + agap)
        cx = bx + cw / 2
        hl = nd.get("highlight")
        if has_icon:
            if hl:
                pad = isz * 0.2
                c._rect(s, cx - isz / 2 - pad, top - pad, isz + 2 * pad, isz + 2 * pad, fill=_h.LIGHTEST_PURPLE, shape=S.OVAL)
            if nd.get("icon"):
                c._place_visual(ctx, nd["icon"], (cx - isz / 2, top, isz, isz), color=_icon_color(hl))
        if has_by and nd.get("by"):
            _tag(c, s, cx, top + (isz + 0.12 if has_icon else 0), str(nd["by"]), dark=str(nd["by"]).upper().startswith("AI"))
        boxes.append(c._rect(s, bx, by, cw, bh, fill=_h.DARKEST_PURPLE if hl else _h.OFF_WHITE))
        c._textbox(s, bx + 0.08, by, cw - 0.16, bh, _label_paras(nd, size, tsz, _h.WHITE if hl else None,
                                                                   text_color=_h.WHITE if hl else None),
                   size, anchor="m", space_after=2, emphasis=None if hl else ctx.emphasis)
        xs.append(cx)
        if i < n - 1:       # 段の間の灰の三角（高さは箱の 35%、文字は入れない）
            import dense
            dense.tri(ctx, bx + cw + agap / 2, by + bh / 2, 0.2, min(0.42, bh * 0.35), "right", _gray())
    if loop:
        a, b = loop.get("from", n - 1), loop.get("to", 0)
        if 0 <= a < n and 0 <= b < n and a != b:
            yb = by + bh + loop_h * 0.62
            xa, xb = xs[a], xs[b]
            import connect      # 下辺 → 下辺の U 字のカギ線（接続付き。直線を継いで描かない）
            connect.link(s, boxes[a], boxes[b], "b", "b", _h.DARK_PURPLE, LINE_W["flow"], arrow=True, mid=yb)
            if loop.get("label"):       # ラベルは U 字の底の線の上の空き（箱の下端と線の間）に置く。線の上に重ねない
                lw_ = min(abs(xa - xb) - 0.3, 0.3 + sum(c._char_w(ch, 12) for ch in loop["label"]) * 1.08)
                ly_ = max(by + bh + 0.03, yb - 0.05 - 0.26)
                c._textbox(s, (xa + xb) / 2 - lw_ / 2, ly_, lw_, min(0.26, yb - 0.04 - ly_), [loop["label"]], 12,
                           _h.DARK_PURPLE, bold=True, anchor="m", align=PP_ALIGN.CENTER, space_after=0, inset=(0, 0, 0, 0))


# ═══════════════════════════════════════════════════════════════
#  M-HUB
# ═══════════════════════════════════════════════════════════════
def m_hub(ctx, r, d):
    """{"center": {"label": "共通データ基盤", "text": "設備・点検・部品", "icon": "q:database"},
        "nodes": [{"label": "保全計画", "text": "計画の自動作成", "icon": "q:calendar", "rel": "参照"}, ...]（3〜8）,
        "emph": ["保全計画"]}
    … 中央の円（濃い紫）の左右に、面の箱（アイコン＋見出し＋説明）を縦に揃えて並べ、直角の短い線でつなぐ。
    斜めの線で余白を横切らない。関係のラベル（rel）は箱と縦の束ね線の間の線の上。"""
    c = _c()
    x, y, w, h = r
    s = ctx.slide
    nodes = _norm(c._items(d, "nodes"))
    n = len(nodes)
    if n < 2:
        ctx.warn("M-HUB: ノードは 2 つ以上")
        return
    if n > 8:
        ctx.warn("M-HUB: ノードが 8 を超える（まとめるか、表にする）")
    cen = d.get("center") or {}
    cen = {"label": cen} if isinstance(cen, str) else cen
    emph = set(d.get("emph") or [])
    k_left = math.ceil(n / 2)
    sides = [nodes[:k_left], nodes[k_left:]]
    kmax = max(len(sd) for sd in sides)
    cd = min(2.6, h * 0.5, w * 0.2)
    rel_w = max([0.0] + [0.3 + sum(c._char_w(ch, 11) for ch in str(nd.get("rel", ""))) * 1.08 for nd in nodes])
    L = max(0.9, rel_w + 0.35)                 # 箱 → 束ね線 → 円 の距離
    box_w = min(4.2, (w - cd - 2 * L) / 2)
    gx0 = x + (w - (cd + 2 * L + 2 * box_w)) / 2
    cx, cy = gx0 + box_w + L + cd / 2, y + h / 2
    tw = box_w - 0.26 - (ICON_IN + 0.14 if any(nd.get("icon") for nd in nodes) else 0)
    size, tsz, need = _box_need(c, nodes, tw, (18, 16, 14))
    gap = 0.3
    per = (h - gap * (kmax - 1)) / kmax
    # 箱は中身＋余白。並び全体が本文の高さの 6〜7 割を使うまで大きくする（小さく縦中央に置いて上下を空けない）
    bh = min(per, max(need + 0.4, per * 0.62))
    if need + 0.1 > bh:
        ctx.warn("M-HUB: 箱の文字が多い（説明を 1 行に）")
    links = []
    for side, sd in enumerate(sides):
        k = len(sd)
        if not k:
            continue
        tot = bh * k + gap * (k - 1)
        y0 = cy - tot / 2
        bx = gx0 if side == 0 else gx0 + box_w + 2 * L + cd
        edge = bx + box_w if side == 0 else bx
        sgn = 1 if side == 0 else -1
        bus = edge + sgn * (L - 0.3)                 # 縦の束ね線の位置（円の手前 0.3in）
        ys = [y0 + i * (bh + gap) + bh / 2 for i in range(k)]
        for nd, yy in zip(sd, ys):
            on = nd.get("label") in emph
            box = _node_box(ctx, bx, yy - bh / 2, box_w, bh, nd, size, tsz, on and d.get("emph_fill"), emph=on)
            links.append((box, "r" if side == 0 else "l", bus, on))
            if nd.get("rel"):
                c._textbox(s, min(edge, bus) + 0.02, yy - 0.3, abs(bus - edge) - 0.04, 0.27, [nd["rel"]], 11,
                           _h.DARK_PURPLE, bold=True, align=PP_ALIGN.CENTER, anchor="b", space_after=0,
                           inset=(0, 0, 0, 0.01))
    # 中央
    circ = c._rect(s, cx - cd / 2, cy - cd / 2, cd, cd, fill=_h.DARKEST_PURPLE, shape=S.OVAL)
    import connect      # 箱 → 円を接続付きのカギ線 1 本で（縦の束ね線は線の重なりで見せる）
    for box, side_, bus, on in links:
        connect.link(s, box, circ, side_, "l" if side_ == "r" else "r", _h.DARK_PURPLE,
                     LINE_W["hub_emph"] if on else LINE_W["hub"], mid=bus)
    lab_c = cen.get("label", "")
    csz = 16 if sum(c._char_w(ch, 16) for ch in lab_c) * 1.08 <= cd * 0.8 else 14 if \
        sum(c._char_w(ch, 14) for ch in lab_c) * 1.08 <= cd * 0.82 else 12
    cp = [(lab_c, {"bold": True, "color": _h.WHITE, "align": PP_ALIGN.CENTER, "size": csz, "space_after": 0})]
    if cen.get("text"):
        cp.append((cen["text"], {"color": _h.WHITE, "align": PP_ALIGN.CENTER, "size": 12}))
    ci = cd * 0.26 if cen.get("icon") else 0
    txt_h = c.est_height([t for t, _ in cp], cd * 0.8, csz, 0)
    ty = cy - (ci + (0.06 if ci else 0) + txt_h) / 2
    if ci and c._place_visual(ctx, cen["icon"], (cx - ci / 2, ty, ci, ci), color=_h.WHITE) is not None:
        ty += ci + 0.06
    c._textbox(s, cx - cd * 0.42, ty, cd * 0.84, txt_h + 0.05, cp, csz, anchor="t", space_after=0, inset=(0, 0, 0, 0))


# ═══════════════════════════════════════════════════════════════
#  M-CYCLE（円弧の矢印 N 本の円）
# ═══════════════════════════════════════════════════════════════
# 人の資料の循環図: circularArrow を同じ正方形の外接枠で N 本重ね、開始角（adj4）・終了角（adj3）だけを変える。
# 帯の太さ adj1 は直径の 9%、矢じりの張り出し adj5 は 7.5%（帯の半分より大きくしないと矢じりが片側だけの旗の形になる）。
# 矢印の間は 18〜24° 空ける（7° では矢じりが次の矢印に食い込み、矢印どうしが重なって見える）。矢じりの角度は 12〜16°。
# 色は 1 色（交互の色は禁止）、強調する段だけ濃い紫。番号と段の名前は円の外、その段の矢印のすぐ脇に置く（帯の上に番号を載せない）。
CYCLE_GAP = {3: 24, 4: 22, 5: 20, 6: 18}
CYCLE_HEAD = {3: 16, 4: 14, 5: 13, 6: 12}
CYCLE_T, CYCLE_OVER = 0.09, 0.075


def _set_adj(shape, **vals):
    from lxml import etree
    from pptx.oxml.ns import qn
    geom = shape._element.spPr.find(qn("a:prstGeom"))
    av = geom.find(qn("a:avLst"))
    if av is None:
        av = etree.SubElement(geom, qn("a:avLst"))
    for gd in list(av):
        av.remove(gd)
    for k, v in vals.items():
        gd = etree.SubElement(av, qn("a:gd"))
        gd.set("name", k)
        gd.set("fmla", f"val {int(v)}")


def ring_arrows(ctx, cx, cy, D, n, emph=(), thick=CYCLE_T, color=None, gap=None, head=None, over=CYCLE_OVER):
    """円弧の矢印 n 本で 1 つの円を描く（12 時から時計回り）。矢印の帯の中心の半径と、各矢印の中央の角度を返す。"""
    c = _c()
    seg = 360.0 / n
    gap = CYCLE_GAP.get(n, 7) if gap is None else gap
    head = CYCLE_HEAD.get(n, 12) if head is None else head
    a1 = int(thick * 100000)
    a5 = a1 if over is None else int(over * 100000)
    mids = []
    for i in range(n):
        st = (-90 + i * seg + gap / 2) % 360
        en = (st + seg - gap) % 360
        sh = c._rect(ctx.slide, cx - D / 2, cy - D / 2, D, D,
                     fill=_h.DARK_PURPLE if i in emph else (color or _h.LIGHT_PURPLE), shape=S.CIRCULAR_ARROW)
        _set_adj(sh, adj1=a1, adj2=head * 60000, adj3=en * 60000, adj4=st * 60000, adj5=a5)
        mids.append(math.radians(-90 + i * seg + seg / 2))
    return D / 2 - D * (over if over is not None else thick), mids


def _cycle_center(ctx, cx, cy, r_in, cen):
    c = _c()
    if not cen:
        return
    cen = cen if isinstance(cen, dict) else {"label": cen}
    wd = r_in * 1.8
    lab = cen.get("label", "")
    # 中央の名前は 1 行に収まる大きさにする（狭い円の中で「保全改革人／材」と語の途中で切れないように）
    sz = next((z for z in (18, 16, 14, 12, 11) if sum(c._char_w(ch, z) for ch in lab) * 1.12 + 0.1 <= wd), 11)
    cp = [(lab, {"bold": True, "color": _h.DARKEST_PURPLE, "align": PP_ALIGN.CENTER, "size": sz, "space_after": 2})]
    if cen.get("text"):
        cp.append((cen["text"], {"align": PP_ALIGN.CENTER, "size": 12}))
    c._textbox(ctx.slide, cx - wd / 2, cy - r_in * 0.7, wd, r_in * 1.4, cp, sz, anchor="m", space_after=2,
               inset=(0, 0, 0, 0))


def _cycle_band(ctx, r, d, nodes, emph):
    """style "band": 太い帯の輪（blockArc を同じ外接枠で N 個、帯の太さ＝直径の 25%）の上に段の名前を載せる。
    継ぎ目に白い向きの印（時計回り）。説明（text）は輪の外。人の資料の「輪の上に文字を載せる」循環図の作り方。"""
    c = _c()
    x, y, w, h = r
    s = ctx.slide
    n = len(nodes)
    cx, cy = x + w / 2, y + h / 2
    has_txt = any(nd.get("text") for nd in nodes)
    D = min(h * (0.86 if has_txt else 0.96), w * (0.42 if has_txt else 0.6))
    seg = 360.0 / n
    th = 0.25
    for i in range(n):
        st, en = (270 + i * seg) % 360, (270 + (i + 1) * seg) % 360     # 段どうしは隙間なしで接する（継ぎ目は白い「>」だけ）
        # 帯は淡い紫（白い向きの印が見える濃さ）。強調の段だけ濃い紫
        sh = c._rect(s, cx - D / 2, cy - D / 2, D, D, fill=_h.DARK_PURPLE if i in emph else _h.LIGHT_PURPLE,
                     shape=S.BLOCK_ARC)
        _set_adj(sh, adj1=st * 60000, adj2=en * 60000, adj3=th * 100000)
    r_mid = D / 2 * (1 - th)
    t = D * th
    for i in range(n):              # 継ぎ目の白い向きの印「>」（白 2.25pt の線 2 本。時計回りの向き）
        a = math.radians(270 + i * seg)
        px, py = cx + r_mid * math.cos(a), cy + r_mid * math.sin(a)
        dx, dy = -math.sin(a), math.cos(a)          # 時計回りの接線
        nx, ny = math.cos(a), math.sin(a)           # 外向きの法線
        tx, ty = px + dx * t * 0.08, py + dy * t * 0.08
        for sgn in (1, -1):
            c._connector(s, tx - dx * t * 0.16 + sgn * nx * t * 0.2, ty - dy * t * 0.16 + sgn * ny * t * 0.2, tx, ty,
                         _h.WHITE, 3.0, glyph=True)
    lw = min(t * 1.7, D * 0.42)
    for i, nd in enumerate(nodes):
        a = math.radians(270 + i * seg + seg / 2)
        px, py = cx + r_mid * math.cos(a), cy + r_mid * math.sin(a)
        on = i in emph
        lab = nd.get("label", "")
        sz = 16 if c.est_lines(lab, lw, 16) <= 2 else 14
        c._textbox(s, px - lw / 2, py - t * 0.45, lw, t * 0.9, [lab], sz, _h.WHITE if on else _h.DARKEST_PURPLE, bold=True,
                   align=PP_ALIGN.CENTER, anchor="m", space_after=0, inset=(0, 0, 0, 0))
        if nd.get("text"):
            ro = D / 2 + 0.16
            co, si = math.cos(a), math.sin(a)
            tw_ = min(3.2, (w - D) / 2 - 0.3)
            lx = cx + ro * co if co > 0.3 else cx + ro * co - tw_ if co < -0.3 else cx + ro * co - tw_ / 2
            al = PP_ALIGN.LEFT if co > 0.3 else PP_ALIGN.RIGHT if co < -0.3 else PP_ALIGN.CENTER
            th_ = c.est_height([nd["text"]], tw_, 12, 0) + 0.05
            ly = cy + ro * si - th_ / 2 if abs(si) <= 0.5 else (cy + ro * si if si > 0 else cy + ro * si - th_)
            c._textbox(s, lx, ly, tw_, th_, [nd["text"]], 12, align=al, anchor="m", space_after=0, emphasis=ctx.emphasis,
                       inset=(0.02, 0, 0.02, 0))
    _cycle_center(ctx, cx, cy, D / 2 * (1 - 2 * th), d.get("center"))


def m_cycle(ctx, r, d):
    """{"nodes": [{"label": "計画", "text": "予測から原案を作る", "body": [リッチ本文], "highlight": false}, ...]（3〜6）,
        "center": "四半期ごと" | {"label":..,"text":..}, "style": "arrows|panels|band"}
    arrows … 円弧の矢印の円＋番号の丸＋円の外のラベル（見出し 14 太字＋説明 12）。v6.8: 段に body（説明＋箇条書き）を
             書くと、ラベルの塊を四隅の空きいっぱいに広げ、文字を 14→12 で合わせる（中身の無い循環図にしない）。
    panels … 中央に小さめの円、左右に同じ大きさのパネル（番号の丸＋見出し＋リッチ本文）。密なページ用。
    band   … 太い帯の輪（blockArc）の上に段の名前、説明は輪の外。段の名前を輪の上で読ませたいとき。"""
    c = _c()
    import dense
    x, y, w, h = r
    s = ctx.slide
    nodes = _norm(c._items(d, "nodes"))
    n = len(nodes)
    if n < 3:
        ctx.warn("M-CYCLE: ノードは 3 つ以上")
        return
    if n > 6:
        ctx.warn("M-CYCLE: ノードが 6 を超える（まとめる）")
        nodes, n = nodes[:6], 6
    emph = {i for i, nd in enumerate(nodes) if nd.get("highlight") or nd.get("emph")}
    style = d.get("style") or "arrows"
    rich_mode = style == "arrows" and any(nd.get("body") for nd in nodes)
    cx, cy = x + w / 2, y + h / 2
    nd_d = 0.36
    if style == "panels":
        kr = math.ceil(n / 2)
        kl = n - kr
        D = min(h * 0.62, w * 0.26)
        sgap = 0.35
        pw = (w - D - 2 * sgap) / 2
        gap = 0.14
        bodies = [([{"h": nd["label"]}] if nd.get("label") else []) + list(nd.get("body") or ([nd["text"]] if nd.get("text") else []))
                  for nd in nodes]
        avail = (h - gap * (kr - 1)) / kr
        tw = pw - nd_d - 0.3
        base = min(dense.fit(dense.rich(b), tw, avail - 0.2)[0] for b in bodies)
        need = max(dense.height(dense.sized(dense.rich(b), base), tw, base) for b in bodies) + 0.24
        ph = min(avail, max(need, 0.9))                 # パネルはすべて同じ大きさ
        for side, k in ((0, kr), (1, kl)):
            tot = ph * k + gap * (k - 1)
            y0 = cy - tot / 2
            for j in range(k):
                i = j if side == 0 else n - 1 - j       # 右列は上から 1, 2, …、左列は上から n, n-1, …（時計回り）
                yy = y0 + j * (ph + gap)
                px = x + w - pw if side == 0 else x
                on = i in emph
                c._rect(s, px, yy, pw, ph, fill=EMPH["fill"] if on else _h.OFF_WHITE,
                        line=EMPH["line"] if on else None, line_w=EMPH["w"])
                dense.num_circle(ctx, px + 0.12 + nd_d / 2, yy + 0.12 + nd_d / 2, nd_d, i + 1,
                                 _h.DARKEST_PURPLE if on else _h.DARK_PURPLE)
                dense.draw_text(ctx, px + nd_d + 0.2, yy + 0.08, tw, ph - 0.12, dense.sized(dense.rich(bodies[i]), base), base)
        r_mid, mids = ring_arrows(ctx, cx, cy, D, n, emph)
        for i, a in enumerate(mids):        # 番号は円の外、その段の矢印の脇（帯の上には載せない）
            ro_ = D / 2 + nd_d * 0.75
            dense.num_circle(ctx, cx + ro_ * math.cos(a), cy + ro_ * math.sin(a), nd_d, i + 1,
                             _h.DARKEST_PURPLE if i in emph else _h.DARK_PURPLE)
        _cycle_center(ctx, cx, cy, r_mid - D * CYCLE_T / 2 - 0.05, d.get("center"))
        return
    if style == "band":
        return _cycle_band(ctx, r, d, nodes, emph)
    # arrows: 番号の丸＋段の名前＋説明を、その段の矢印のすぐ外に置く。上下に来るラベルがあれば、その分だけ円を小さくする
    D = min(h * 0.9, w * (0.34 if w > 9 else 0.42))      # 図＋解説（M-FIGNOTE）の狭い枠では円を大きめに
    lw = min(3.2, (w - D) / 2 - 0.5)
    if rich_mode:                   # 説明＋箇条書きのある段: 円を少し小さくし、ラベルの塊を四隅の空きいっぱいに
        D = min(h * 0.8, w * 0.3)
        lw = min(4.4, (w - D) / 2 - 0.3)
        return _cycle_rich(ctx, r, d, nodes, emph, D, lw, nd_d)
    if lw < 1.5:                    # ラベルが 3 行以上に折れる狭さなら、円を少し小さくしてラベルの幅を取る
        D = max(min(D, 2.4), w - 2 * (1.5 + 0.5))
        lw = min(3.2, (w - D) / 2 - 0.5)
    mids = [math.radians(-90 + i * 360 / n + 180 / n) for i in range(n)]
    tw_ = lw - nd_d - 0.1
    paras = [_label_paras(nd, 14, 12, align=PP_ALIGN.LEFT) for nd in nodes]
    lab_h = [max(nd_d, c.est_height(p, tw_, 14, 2)) + 0.04 for p in paras]
    vert = [abs(math.cos(a)) < 0.35 for a in mids]
    if any(vert):
        D = min(D, h - 2 * (max(hh for hh, v in zip(lab_h, vert) if v) + 0.12))
    r_mid, mids = ring_arrows(ctx, cx, cy, D, n, emph)
    ro = D / 2 + 0.1
    for i, (nd, a, p, lh) in enumerate(zip(nodes, mids, paras, lab_h)):
        co, si = math.cos(a), math.sin(a)
        px, py = cx + ro * co, cy + ro * si
        # ラベルの塊の幅は中身に合わせる（左側のラベルが円から離れないように）
        tw_i = min(tw_, max(sum(c._char_w(ch, sz) for ch in t) * (1.08 if o.get("bold") else 1.0) for t, o in p
                            for sz in [o.get("size", 14)]) + 0.12)
        bw = nd_d + 0.1 + tw_i
        if co > 0.35:
            lx = px
        elif co < -0.35:
            lx = px - bw
        else:
            lx = px - bw / 2
        # 左右のラベルは弧の中点と同じ高さに横から添える（四隅に離さない）。真上・真下だけ上下に置く
        if abs(co) > 0.35:
            ly = py - lh / 2
            lx = px + 0.05 if co > 0 else px - bw - 0.05
        else:
            ly = py if si > 0 else py - lh
        on = i in emph
        dense.num_circle(ctx, lx + nd_d / 2, ly + nd_d / 2 + 0.02, nd_d, i + 1, _h.DARKEST_PURPLE if on else _h.DARK_PURPLE)
        if on:
            p = [(t, {**o, "color": _h.DARK_PURPLE}) if o.get("bold") else (t, o) for t, o in p]
        c._textbox(s, lx + nd_d + 0.1, ly, tw_i + 0.06, lh, p, 14, anchor="t", space_after=2, emphasis=ctx.emphasis,
                   inset=(0.02, 0.02, 0.02, 0))
    _cycle_center(ctx, cx, cy, r_mid - D * CYCLE_T / 2 - 0.05, d.get("center"))


def _cycle_rich(ctx, r, d, nodes, emph, D, lw, nd_d):
    """arrows 型で、各段に見出し＋説明＋箇条書き（body）を書く。ラベルは段の矢印の中央の角度の外側、四隅の空きいっぱい。
    文字は全段で同じ大きさ（14→12→11 で収まる最大）。真上・真下に来る段は、その分だけ円を小さくする。"""
    c = _c()
    import dense
    x, y, w, h = r
    s = ctx.slide
    n = len(nodes)
    cx, cy = x + w / 2, y + h / 2
    tw = lw - nd_d - 0.12
    mids = [math.radians(-90 + i * 360 / n + 180 / n) for i in range(n)]
    vert = [abs(math.cos(a)) < 0.35 for a in mids]
    rows_per_side = max(1, math.ceil(sum(1 for v in vert if not v) / 2))
    cap = (h - 0.1) / rows_per_side - 0.12          # 横に添える段 1 つ分の高さ

    def body_of(nd):
        b = [{"h": nd.get("label", "")}]
        if nd.get("text"):
            b.append({"p": nd["text"]})
        return b + list(nd.get("body") or [])
    bodies = [body_of(nd) for nd in nodes]
    base = 11
    for sz in (14, 12, 11):
        hs = [dense.height(dense.sized(dense.rich(b), sz), tw, sz) for b in bodies]
        if all(hh <= cap for hh, v in zip(hs, vert) if not v):
            base = sz
            break
    paras = [dense.sized(dense.rich(b), base) for b in bodies]
    hs = [dense.height(p, tw, base) + 0.06 for p in paras]
    if any(vert):
        D = min(D, h - 2 * (max(hh for hh, v in zip(hs, vert) if v) + 0.1))
    D = max(D, 1.6)
    r_mid, mids = ring_arrows(ctx, cx, cy, D, n, emph)
    ro = D / 2 + 0.15
    for i, (nd, a, p, lh) in enumerate(zip(nodes, mids, paras, hs)):
        co, si = math.cos(a), math.sin(a)
        px, py = cx + ro * co, cy + ro * si
        bw = nd_d + 0.12 + tw
        if abs(co) > 0.35:
            lx = px + 0.05 if co > 0 else px - bw - 0.05
            ly = min(max(py - lh / 2, y), y + h - lh)
        else:
            lx = px - bw / 2
            ly = py if si > 0 else py - lh
        on = i in emph
        dense.num_circle(ctx, lx + nd_d / 2, ly + nd_d / 2 + 0.02, nd_d, i + 1, _h.DARKEST_PURPLE if on else _h.DARK_PURPLE)
        dense.draw_text(ctx, lx + nd_d + 0.1, ly, tw + 0.04, lh, p, base)
    _cycle_center(ctx, cx, cy, r_mid - D * CYCLE_T / 2 - 0.05, d.get("center"))


# ═══════════════════════════════════════════════════════════════
#  M-EQUATION
# ═══════════════════════════════════════════════════════════════
def m_equation(ctx, r, d):
    """{"terms": [{"label": "業務知見", "text": "...", "icon": "q:..."}, ..., {"label": "成果", "text": "..."}],
        "ops": ["＋", "×", "＝"]}   … ops は項の数 − 1。最後の項（＝ の右）が結論で、濃い紫の地に白抜き。"""
    c = _c()
    x, y, w, h = r
    s = ctx.slide
    terms = _norm(c._items(d, "terms"))
    n = len(terms)
    if n < 2:
        return
    ops = list(d.get("ops") or (["＋"] * (n - 2) + ["＝"]))
    ops += ["＋"] * (n - 1 - len(ops))
    og = 0.62
    weights = [1.0] * (n - 1) + [1.15]
    cw_tot = w - og * (n - 1)
    cws = [cw_tot * wt / sum(weights) for wt in weights]
    has_icon = any(t.get("icon") for t in terms)
    isz = min(0.8, h * 0.2) if has_icon else 0
    size = min(_fit_pair(c, [t], cw - 0.3, h * 0.6 - isz, (18, 16, 14, 12))[0] for t, cw in zip(terms, cws))
    need = max(c.est_height(_label_paras(t, size, max(12, size - 2)), cw - 0.3, size, 4) for t, cw in zip(terms, cws))
    bh = min(h, max(h * 0.62, isz + 0.25 + need + 0.35))   # 主図として枠の 6 割以上を使う
    by = y + (h - bh) / 2
    bx = x
    for i, (t, cw) in enumerate(zip(terms, cws)):
        last = i == n - 1
        if last:
            c._rect(s, bx, by, cw, bh, fill=_h.DARKEST_PURPLE)
        else:
            c._rect(s, bx, by, cw, bh, fill=_h.WHITE, line=_h.LIGHT_GRAY, line_w=1.0)
            c._rect(s, bx, by, cw, 0.06, fill=_h.DARK_PURPLE)
        ty = by + max(0.22, (bh - (isz + 0.12 if has_icon else 0) - need) / 2)   # 中身を箱の縦中央に
        if t.get("icon"):
            if c._place_visual(ctx, t["icon"], (bx + (cw - isz) / 2, ty, isz, isz),
                               color=_h.WHITE if last else _icon_color(False)) is not None:
                ty += isz + 0.12
        elif has_icon:
            ty += isz + 0.12
        c._textbox(s, bx + 0.15, ty, cw - 0.3, by + bh - ty - 0.12,
                   _label_paras(t, size, max(12, size - 2), _h.WHITE if last else None, text_color=_h.WHITE if last else None),
                   size, space_after=4, emphasis=None if last else ctx.emphasis)
        bx += cw
        if i < n - 1:
            op = ops[i]
            o = c._rect(s, bx + (og - 0.44) / 2, by + bh / 2 - 0.22, 0.44, 0.44,
                        fill=_h.DARK_PURPLE if op in ("＝", "=") else _h.MID_GRAY, shape=S.OVAL)
            c._shape_text(o, op, 20, _h.WHITE, True, inset=(0, 0, 0, 0), wrap=False)
            bx += og


# ═══════════════════════════════════════════════════════════════
#  M-ICONROW
# ═══════════════════════════════════════════════════════════════
def m_iconrow(ctx, r, d):
    """{"head": "提供価値（帯の見出し・任意）",
        "items": [{"label": "計画を速く", "icon": "q:...", "value": "20h → 10h", "text": "…" | "body": [リッチ本文]}, ...],
        "layout": "stack|side"}
    … アイコンは脇役（0.6in、見出しの左）。見出し（16 太字）と中身（数字・説明 2〜3 行）を主役にする。"""
    c = _c()
    import dense
    x, y, w, h = r
    s = ctx.slide
    items = _norm(c._items(d))
    n = len(items)
    if not n:
        return
    if d.get("head"):
        band = c._rect(s, x, y, w, 0.42, fill=_h.DARKEST_PURPLE)
        c._shape_text(band, d["head"], 14, _h.WHITE, True)
        y, h = y + 0.56, h - 0.56
    layout = d.get("layout") or ("stack" if n <= 5 else "side")

    def body_of(it):
        b = list(it.get("body") or [])
        if not b:
            if it.get("text"):
                b.append({"p": it["text"]})
            if it.get("items"):
                b.append({"b": it["items"]})
        return b

    vsz = [28]

    def value_paras(it):
        return [(str(it["value"]), {"size": vsz[0], "bold": True, "color": _h.DARK_PURPLE, "space_after": 4})] \
            if it.get("value") else []
    if layout == "stack":
        gap = 0.36
        cw = (w - gap * (n - 1)) / n
        # 数字は 1 行に収める（「差し／戻し 25%」のように折り返さない）。並びで同じ大きさ（いちばん長い値に合わせる）
        vals = [str(it["value"]) for it in items if it.get("value")]
        vsz[0] = next((z for z in (28, 24, 20) if all(sum(c._char_w(ch, z) for ch in v) * 1.1 <= cw - 0.15 for v in vals)), 18)
        isz = min(ICON_TOP, cw * 0.22)
        hw = cw - (isz + 0.14 if any(it.get("icon") for it in items) else 0)
        ls = 16 if all(c.est_lines(it.get("label", ""), hw, 16) <= 2 for it in items) else 14
        head_h = max(isz, max(c.est_height([it.get("label", "")], hw, ls, 0) for it in items))
        avail = h - head_h - 0.22
        base = 12
        for sz in (16, 14, 12):
            if all(dense.height(value_paras(it) + dense.sized(dense.rich(body_of(it)), sz), cw, sz) <= avail * 0.8
                   for it in items):
                base = sz
                break
        bodies = [value_paras(it) + dense.sized(dense.rich(body_of(it)), base) for it in items]
        need = max(dense.height(p, cw, base) for p in bodies)
        block = head_h + 0.22 + need
        top = y + max(0, (h - block) / 2)
        for i, (it, ps) in enumerate(zip(items, bodies)):
            bx = x + i * (cw + gap)
            if i:
                c._connector(s, bx - gap / 2, top, bx - gap / 2, top + block, _h.LIGHT_GRAY, 0.75)
            tx = bx
            if it.get("icon"):
                c._place_visual(ctx, it["icon"], (bx, top + (head_h - isz) / 2, isz, isz), color=_icon_color(it.get("emph")))
                tx = bx + isz + 0.14
            c._textbox(s, tx, top, bx + cw - tx, head_h, [it.get("label", "")], ls, _h.DARKEST_PURPLE, bold=True,
                       anchor="m", space_after=0, inset=(0.02, 0, 0.02, 0))
            c._hline(s, bx, top + head_h + 0.1, cw, _h.DARK_PURPLE, 1.0)
            if ps:
                dense.draw_text(ctx, bx - 0.04, top + head_h + 0.2, cw + 0.08, need + 0.05, ps, base)
        return
    cols = 1 if n <= 3 else 2
    rows = math.ceil(n / cols)
    gx, gy = 0.4, 0.18
    cw = (w - gx * (cols - 1)) / cols
    rh = (h - gy * (rows - 1)) / rows
    isz = min(ICON_IN + 0.1, rh * 0.6)
    tw = cw - isz - 0.2
    size, tsz = _fit_pair(c, items, tw, rh, (16, 14, 12), align=PP_ALIGN.LEFT)
    for i, it in enumerate(items):
        rr, cc = divmod(i, cols)
        bx, by = x + cc * (cw + gx), y + rr * (rh + gy)
        if it.get("icon"):
            c._place_visual(ctx, it["icon"], (bx, by + (rh - isz) / 2, isz, isz), color=_icon_color(it.get("emph")))
        c._textbox(s, bx + isz + 0.2, by, tw, rh, _label_paras(it, size, tsz, align=PP_ALIGN.LEFT), size,
                   anchor="m", space_after=2, emphasis=ctx.emphasis)
        if rr < rows - 1:
            c._hline(s, bx, by + rh + gy / 2, cw, _h.LIGHT_GRAY, 0.75)


def register(modules):
    modules.update({"M-HUB": m_hub, "M-HUBSPOKE": m_hub, "M-EQUATION": m_equation, "M-ICONROW": m_iconrow,
                    "M-RING": m_cycle})
