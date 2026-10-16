"""
patterns.py — 人の提案書の型（v6.8）。人の資料（提案書・報告書 4 デッキ）から実測した寸法で描く。文言は持たない。

  M-CASELIST  実績一覧: 行＝案件。行ラベル＋背景・狙いの文＋観点ごとの ✓ 列＋着手時期
  M-COLCARDS  列×アクセント付きカード: 濃い紫の見出し帯（見出し＋副題）＋左に紫の帯のカード×N＋下にアイコン
  M-PROGRAM   五方向の大きな器: 器の中に題・リード・帯・番号付きの五方向のパネル、下に土台の帯、右に強みの一覧
  M-OUTPUTS   成果物のイメージ: 見出し帯＋画像（無ければ線画の見本）の格子
  M-GANTT の作業の流れ版（gantt_ws）: 工程の帯・作業の流れの行見出し・バーの中の作業名・担い手の凡例・▼ マイルストーン・範囲の枠
  M-TREE の KPI 版（kpi_tree）: 根 → 中分類 → 施策（値の列）← 具体例の箇条書き、行の間は点線

文字は箱に直接書く（_shape_text、または箱＋本文を描いて compose.merge_text_into_boxes が箱の文字にする）。
工程・段の見出しは五方向の矢印（compose.homeplate）を隙間を空けて並べる。
"""

import math

from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE as S
from pptx.enum.text import PP_ALIGN

import helpers as _h


def _c():
    import compose
    return compose


def _d():
    import dense
    return dense


# ═══════════════════════════════════════════════════════════════
#  M-CASELIST（実績一覧）
# ═══════════════════════════════════════════════════════════════
def m_caselist(ctx, r, d):
    """{"columns": ["プロジェクトの背景・狙い", "全社事業構造改革", "DX 推進", "経営基盤変革", "着手時期"],
        "rows": [{"label": "総合化学\\nA 社", "text": "…**要点**…" | [リッチ本文], "checks": [false, true, "partial"],
                  "date": "19 年 4 月"}], "partial_label": "（計画中）"}
    … 人の資料（実績一覧）: 行の高さはすべて同じ、行ラベルの箱 1.35in、文章の箱は行ラベルの 0.1in 右、
    ✓ の列は 1.2in ピッチで中央、時期の列は右端。✓ は 18pt 太字、計画中は灰の ✓＋小さな注記。"""
    c, dn = _c(), _d()
    x, y, w, h = r
    s = ctx.slide
    cols = list(d.get("columns") or [])
    rows = d.get("rows") or []
    if not rows:
        return
    nchk = max(len(rw.get("checks") or []) for rw in rows)
    has_date = any(rw.get("date") for rw in rows)
    lab_w, gap = min(1.5, w * 0.11), 0.1
    ck_w = 1.15 if nchk <= 3 else 0.95
    dt_w = 1.1 if has_date else 0
    tx = x + lab_w + gap
    tw = w - lab_w - gap - nchk * ck_w - dt_w - 0.1
    hdr = 0.5
    # 見出し: 文章の列は中央、観点・時期の列は下線付き（人の資料は ✓ の列の見出しに下線）
    heads = cols + [""] * (1 + nchk + (1 if has_date else 0) - len(cols))
    c._textbox(s, tx, y, tw, hdr, [heads[0]], 16, _h.TEXT_BODY, align=PP_ALIGN.CENTER, anchor="b", space_after=0,
               inset=(0.02, 0, 0.02, 0.04))
    ck_x = [tx + tw + 0.1 + k * ck_w for k in range(nchk)]
    for k in range(nchk):
        hs, _ = c.fit_size([heads[1 + k]], ck_w - 0.08, hdr, (14, 12))
        c._textbox(s, ck_x[k], y, ck_w, hdr, [heads[1 + k]], hs, _h.TEXT_BODY, align=PP_ALIGN.CENTER, anchor="b",
                   space_after=0, inset=(0.02, 0, 0.02, 0.04))
        c._hline(s, ck_x[k] + 0.1, y + hdr, ck_w - 0.2, _h.TEXT_BODY, 0.75)
    dx = x + w - dt_w
    if has_date:
        c._textbox(s, dx, y, dt_w, hdr, [heads[1 + nchk]], 14, _h.TEXT_BODY, align=PP_ALIGN.CENTER, anchor="b",
                   space_after=0, inset=(0.02, 0, 0.02, 0.04))
        c._hline(s, dx + 0.1, y + hdr, dt_w - 0.2, _h.TEXT_BODY, 0.75)
    y0 = y + hdr + 0.1
    n = len(rows)
    rg = 0.06
    rh = (y + h - y0 - rg * (n - 1)) / n
    bodies = [dn.rich(rw.get("text") or rw.get("body") or "") for rw in rows]
    base = 11
    for sz in (14, 12, 11):          # 全行で同じ大きさ（収まる最大）
        if all(dn.height(dn.sized(b, sz), tw - 0.12, sz) <= rh - 0.06 for b in bodies):
            base = sz
            break
    lab_sz = min(c.fit_size([str(rw.get("label", "")).replace("\\n", "\n")], lab_w - 0.12, rh, (16, 14, 12))[0] for rw in rows)
    partial = d.get("partial_label", "（計画中）")
    for i, (rw, b) in enumerate(zip(rows, bodies)):
        ry = y0 + i * (rh + rg)
        lb = c._rect(s, x, ry, lab_w, rh, fill=_h.WHITE, line=_h.TEXT_BODY, line_w=0.75)
        c._shape_text(lb, str(rw.get("label", "")).replace("\\n", "\n"), lab_sz, _h.TEXT_BODY, False,
                      inset=(0.04, 0.02, 0.04, 0.02))
        c._rect(s, tx, ry, tw, rh, fill=_h.WHITE, line=_h.TEXT_BODY, line_w=0.75)
        dn.draw_text(ctx, tx + 0.04, ry, tw - 0.08, rh, dn.sized(b, base), base, anchor="m")
        for k, v in enumerate((rw.get("checks") or [])[:nchk]):
            if not v:
                continue
            pv = v == "partial"
            cy = ry + rh / 2 - (0.12 if pv else 0)
            c._textbox(s, ck_x[k], cy - 0.2, ck_w, 0.4, ["✓"], 18, _h.MID_GRAY if pv else _h.DARK_PURPLE, bold=not pv,
                       align=PP_ALIGN.CENTER, anchor="m", space_after=0, inset=(0, 0, 0, 0))
            if pv:
                c._textbox(s, ck_x[k], cy + 0.16, ck_w, 0.26, [partial], 11, _h.MID_GRAY, align=PP_ALIGN.CENTER,
                           anchor="t", space_after=0, inset=(0, 0, 0, 0))
        if rw.get("date"):
            c._textbox(s, dx, ry, dt_w, rh, [str(rw["date"])], 14, _h.TEXT_BODY, align=PP_ALIGN.CENTER, anchor="m",
                       space_after=0, inset=(0, 0, 0, 0))


# ═══════════════════════════════════════════════════════════════
#  M-COLCARDS（列×アクセント付きカード）
# ═══════════════════════════════════════════════════════════════
def m_colcards(ctx, r, d):
    """{"columns": [{"head": "全社 AI 変革", "sub": "AI led Total Enterprise Reinvention",
                     "cards": [{"title": "AI ネイティブな変革設計", "text": "…" | "items": [..] | "body": [リッチ本文]}],
                     "icon": "q:building"}], "emph": 1}
    … 人の資料: 見出し帯（濃い紫・見出し 16 太字＋副題 12）、その下に淡い灰のカード（左に 0.07in の紫の帯、
    紫の太字の題＋本文）を 3 枚ほど。カードの高さは全列でそろえる。下に列ごとのアイコン（任意）。"""
    c, dn = _c(), _d()
    x, y, w, h = r
    s = ctx.slide
    cols = d.get("columns") or []
    nc = max(len(cols), 1)
    gap = 0.16
    cw = (w - gap * (nc - 1)) / nc
    has_icon = any(cl.get("icon") for cl in cols)
    icon_h = 0.85 if has_icon else 0
    hd_h = 0.95 if any(cl.get("sub") for cl in cols) else 0.6
    ncard = max(len(cl.get("cards") or []) for cl in cols) or 1
    cg = 0.1
    avail = h - hd_h - 0.12 - icon_h - cg * (ncard - 1)
    ch = avail / ncard
    tw = cw - 0.32

    def body_of(cd):
        b = [{"h": cd.get("title", "")}] if cd.get("title") else []
        if cd.get("body"):
            b += list(cd["body"])
        if cd.get("text"):
            b.append({"p": cd["text"]})
        if cd.get("items"):
            b.append({"b": cd["items"]})
        return b
    allb = [body_of(cd) for cl in cols for cd in cl.get("cards") or []]
    base = 11
    for sz in (14, 12, 11):
        if all(dn.height(dn.sized(dn.rich(b), sz, sub_color=_h.DARK_PURPLE), tw, sz) <= ch - 0.08 for b in allb):
            base = sz
            break
    emph = d.get("emph")
    for i, cl in enumerate(cols):
        cx = x + i * (cw + gap)
        hb = c._rect(s, cx, y, cw, hd_h, fill=_h.DARKEST_PURPLE if emph == i else _h.DARK_PURPLE)
        paras = [(cl.get("head", ""), {"size": 16, "bold": True, "color": _h.WHITE, "align": PP_ALIGN.CENTER, "space_after": 2})]
        if cl.get("sub"):
            paras.append((cl["sub"], {"size": 12, "color": _h.WHITE, "align": PP_ALIGN.CENTER}))
        c._textbox(s, cx + 0.06, y, cw - 0.12, hd_h, paras, 16, anchor="m", space_after=0)
        for k, cd in enumerate(cl.get("cards") or []):
            cy = y + hd_h + 0.12 + k * (ch + cg)
            c._rect(s, cx, cy, cw, ch, fill=_h.OFF_WHITE)
            c._rect(s, cx, cy, 0.07, ch, fill=_h.DARK_PURPLE)
            dn.draw_text(ctx, cx + 0.18, cy, tw + 0.08, ch, dn.sized(dn.rich(body_of(cd)), base, sub_color=_h.DARK_PURPLE),
                         base, anchor="m")
        if cl.get("icon"):
            isz = 0.7
            c._place_visual(ctx, cl["icon"], (cx + cw / 2 - isz / 2, y + h - icon_h + 0.1, isz, isz), color=_h.DARKEST_PURPLE)


# ═══════════════════════════════════════════════════════════════
#  M-PROGRAM（五方向の大きな器）
# ═══════════════════════════════════════════════════════════════
def m_program(ctx, r, d):
    """{"title": "中長期パートナーシップ", "lead": ["…", "…"],
        "band": {"label": "DX 支援", "text": "プロジェクト組成・方法論の知見を通じた実行支援"},
        "panels_label": "育成支援", "panels": [{"no": [1, 2], "title": "研修（Off-JT）", "items": [..]}, ...]（2〜4）,
        "under": [{"text": "育成プログラム", "span": [0, 1]}, {"text": "プロジェクトでの協働", "span": [2, 2]}],
        "foot": {"no": [5, 6], "text": "タレントマネジメント基盤による育成のデジタル化"},
        "strengths": {"head": "アクセンチュアの強みポイント", "items": ["…", ...]}}
    … 人の資料: 器は濃い紫の五方向の矢印（矢じり 0.4in）。中の帯・パネルも五方向の矢印、パネルの左上に黒の番号丸
    （0.35in・パネルの上に 0.2in はみ出す）。右の強みの一覧は灰の箱に番号丸を左の縁に載せる。"""
    c, dn = _c(), _d()
    x, y, w, h = r
    s = ctx.slide
    st = d.get("strengths")
    gw = w * (0.66 if st else 1.0)
    foot = d.get("foot")
    foot_h = 0.5 if foot else 0
    bh = h - (foot_h + 0.15 if foot else 0)
    tip = 0.45
    box = c.homeplate(s, x, y, gw, bh, fill=_h.DARK_PURPLE, tip=tip)
    iw = gw - tip - 0.3
    ix = x + 0.15
    yy = y + 0.12
    c._textbox(s, ix, yy, iw, 0.5, [d.get("title", "")], 24, _h.WHITE, bold=True, align=PP_ALIGN.CENTER, anchor="m",
               space_after=0)
    yy += 0.52
    lead = d.get("lead") or []
    if lead:
        ps = [(t, {"bullet": "●", "color": _h.WHITE}) for t in lead]
        lh = c.est_height(ps, iw - 0.3, 12, 2) + 0.05
        c._textbox(s, ix + 0.3, yy, iw - 0.3, lh, ps, 12, _h.WHITE, space_after=2, emphasis=ctx.emphasis)
        yy += lh + 0.08
    labs = [str((d.get("band") or {}).get("label", "")), str(d.get("panels_label") or "")]
    lab_w = min(1.1, max(0.75, max(sum(c._char_w(ch, 14) for ch in t) for t in labs) + 0.16))
    band = d.get("band")
    if band:
        lb = c._rect(s, ix, yy, lab_w, 0.6, fill=_h.WHITE, line=_h.TEXT_BODY, line_w=0.75)
        c._shape_text(lb, band.get("label", ""), 14, _h.TEXT_BODY, False, inset=(0.02, 0, 0.02, 0))
        bd = c.homeplate(s, ix + lab_w + 0.1, yy, iw - lab_w - 0.1, 0.6, fill=_h.LIGHTEST_PURPLE)
        c._shape_text(bd, band.get("text", ""), 16, _h.DARKEST_PURPLE, True, inset=(0.1, 0, 0.2, 0))
        yy += 0.6 + 0.2
    panels = d.get("panels") or []
    under = d.get("under") or []
    ph = y + bh - 0.15 - (0.32 if under else 0) - yy
    if panels:
        if d.get("panels_label"):
            lb = c._rect(s, ix, yy, lab_w, ph, fill=_h.WHITE, line=_h.TEXT_BODY, line_w=0.75)
            c._shape_text(lb, d["panels_label"], 14, _h.TEXT_BODY, False, inset=(0.02, 0, 0.02, 0))
        px0 = ix + lab_w + 0.1
        n = len(panels)
        pg = 0.08
        pw = (iw - lab_w - 0.1 - pg * (n - 1)) / n
        bodies = [[{"h": p.get("title", "")}] + ([{"p": p["text"]}] if p.get("text") else [])
                  + ([{"b": p["items"], "mark": "✓"}] if p.get("items") else []) for p in panels]
        tw = pw - 0.35
        base = 11
        for sz in (14, 12, 11):
            if all(dn.height(dn.sized(dn.rich(b), sz, sub_color=_h.DARK_PURPLE), tw, sz) <= ph - 0.3 for b in bodies):
                base = sz
                break
        for k, (p, b) in enumerate(zip(panels, bodies)):
            px = px0 + k * (pw + pg)
            c.homeplate(s, px, yy, pw, ph, fill=_h.LIGHTEST_PURPLE, line=_h.DARKEST_PURPLE, line_w=0.75, tip=0.18)
            dn.draw_text(ctx, px + 0.1, yy + 0.22, tw + 0.05, ph - 0.26, dn.sized(dn.rich(b), base, sub_color=_h.DARK_PURPLE),
                         base, anchor="t")
            nos = p.get("no") if isinstance(p.get("no"), list) else [p.get("no", k + 1)]
            for j, no in enumerate(nos):
                dn.num_circle(ctx, px + 0.18 + j * 0.36, yy - 0.02, 0.34, no, fill=_h.BLACK, size=14)
        for u in under:                 # パネルの下の両矢印の線（「育成プログラム」など、どのパネルの範囲かを示す）
            a, b_ = (u.get("span") or [0, n - 1])[:2]
            ux0, ux1 = px0 + a * (pw + pg), px0 + b_ * (pw + pg) + pw - 0.18
            uy = yy + ph + 0.08
            ln = c._connector(s, ux0, uy, ux1, uy, color=_h.WHITE, width=1.25, arrow=True)
            from lxml import etree
            from pptx.oxml.ns import qn
            he = etree.SubElement(ln.line._get_or_add_ln(), qn("a:headEnd"))
            he.set("type", "triangle"); he.set("w", "sm"); he.set("len", "sm")
            ln_ = ln.line._get_or_add_ln()
            ln_.remove(he); ln_.insert(list(ln_).index(ln_.find(qn("a:tailEnd"))), he)
            c._textbox(s, ux0, uy + 0.02, ux1 - ux0, 0.26, [u.get("text", "")], 12, _h.WHITE, bold=True,
                       align=PP_ALIGN.CENTER, space_after=0, inset=(0, 0, 0, 0))
    if foot:
        fy = y + bh + 0.15
        fb = c.homeplate(s, x, fy, gw - tip, foot_h, fill=_h.WHITE, line=_h.DARKEST_PURPLE, line_w=1.5, tip=0.2)
        c._shape_text(fb, foot.get("text", ""), 16, _h.DARKEST_PURPLE, True, inset=(0.9, 0, 0.2, 0))
        for j, no in enumerate(foot.get("no") or []):
            dn.num_circle(ctx, x + 0.3 + j * 0.36, fy, 0.34, no, fill=_h.BLACK, size=14)
    del box
    if st:
        sx = x + gw + 0.3
        sw = x + w - sx
        c._textbox(s, sx, y, sw, 0.36, [st.get("head", "")], 14, _h.TEXT_BODY, bold=True, align=PP_ALIGN.CENTER,
                   anchor="b", space_after=0, inset=(0, 0, 0, 0.03))
        c._hline(s, sx, y + 0.4, sw, _h.TEXT_BODY, 0.75)
        items = st.get("items") or []
        m = max(len(items), 1)
        g2 = 0.11
        ih = (h - 0.5 - g2 * (m - 1)) / m
        sz = min(c.fit_size([t], sw - 0.5, ih - 0.06, (16, 14, 12))[0] for t in items) if items else 14
        for k, t in enumerate(items):
            iy = y + 0.5 + k * (ih + g2)
            ib = c._rect(s, sx + 0.12, iy, sw - 0.12, ih, fill=_h.OFF_WHITE, line=_h.TEXT_BODY, line_w=0.75)
            c._shape_text(ib, t, sz, _h.TEXT_BODY, True, inset=(0.32, 0.02, 0.08, 0.02), emphasis=ctx.emphasis)
            dn.num_circle(ctx, sx + 0.12, iy + 0.2, 0.36, k + 1, fill=_h.BLACK, size=14)


# ═══════════════════════════════════════════════════════════════
#  M-OUTPUTS（成果物のイメージ）
# ═══════════════════════════════════════════════════════════════
def m_outputs(ctx, r, d):
    """{"items": [{"head": "DX ビジョン", "caption": "全社 DX ビジョン", "image": "path.png", "kind": "doc|table|chart|map|flow"}],
        "cols": 3}
    … 人の資料: 見出し帯（濃い紫・16 太字）の 0.02in 下に成果物の画像。画像が無いときは、kind に合わせた線画の見本
    （文書の行・表の格子・棒グラフ・マップの升目・流れの箱）を灰と紫で描く。"""
    c = _c()
    x, y, w, h = r
    s = ctx.slide
    items = d.get("items") or []
    n = len(items)
    if not n:
        return
    nc = d.get("cols") or (3 if n > 4 else n if n <= 3 else 2)
    nr = math.ceil(n / nc)
    gx, gy = 0.3, 0.25
    cw = (w - gx * (nc - 1)) / nc
    ch = (h - gy * (nr - 1)) / nr
    hd = 0.5
    for i, it in enumerate(items):
        cx, cy = x + (i % nc) * (cw + gx), y + (i // nc) * (ch + gy)
        hb = c._rect(s, cx, cy, cw, hd, fill=_h.DARK_PURPLE)
        c._shape_text(hb, it.get("head", ""), 16, _h.WHITE, True)
        iy = cy + hd + 0.04
        if it.get("caption"):
            c._textbox(s, cx, iy, cw, 0.3, [it["caption"]], 12, _h.TEXT_BODY, space_after=0, inset=(0.02, 0, 0.02, 0))
            iy += 0.32
        ih = cy + ch - iy
        if it.get("image") and c._place_visual(ctx, {"image": it["image"]}, (cx, iy, cw, ih)) is not None:
            continue
        _mock(c, s, cx, iy, cw, ih, it.get("kind", "doc"))


def _mock(c, s, x, y, w, h, kind):
    """成果物の線画の見本（画像が無いとき）。灰の枠の中に、種類ごとの形を描く。"""
    c._rect(s, x, y, w, h, fill=_h.WHITE, line=_h.LIGHT_GRAY, line_w=0.75)
    px, py, pw, ph = x + 0.15, y + 0.15, w - 0.3, h - 0.3
    c._rect(s, px, py, pw * 0.55, 0.12, fill=_h.DARK_PURPLE)          # 見出しの帯
    py += 0.25
    ph -= 0.25
    if kind == "table":
        nr, nc = 6, 5
        for i in range(nr + 1):
            c._hline(s, px, py + i * ph / nr, pw, _h.LIGHT_GRAY, 0.5)
        c._rect(s, px, py, pw, ph / nr, fill=_h.LIGHTEST_PURPLE)
        for j in range(nr - 1):
            c._rect(s, px + pw * 0.3, py + (j + 1.3) * ph / nr, pw * (0.15 + 0.1 * (j % 3)), ph / nr * 0.4, fill=_h.LIGHT_PURPLE)
    elif kind == "chart":
        nb = 8
        bw = pw / nb * 0.6
        for j in range(nb):
            bh_ = ph * (0.3 + 0.6 * ((j * 37) % 10) / 10)
            c._rect(s, px + j * pw / nb, py + ph - bh_, bw, bh_, fill=_h.DARK_PURPLE if j % 4 == 3 else _h.LIGHT_PURPLE)
        c._hline(s, px, py + ph, pw, _h.MID_GRAY, 0.75)
    elif kind == "map":
        nr, nc = 5, 8
        for i in range(nr):
            for j in range(nc):
                if (i * 3 + j * 5) % 7 < 2:
                    c._rect(s, px + j * pw / nc + 0.02, py + i * ph / nr + 0.04, pw / nc - 0.04, ph / nr * 0.4,
                            fill=_h.DARK_PURPLE if (i + j) % 3 == 0 else _h.LIGHT_PURPLE)
            c._hline(s, px, py + (i + 1) * ph / nr, pw, _h.LIGHT_GRAY, 0.5)
    elif kind == "flow":
        nb = 4
        bw = (pw - 0.15 * (nb - 1)) / nb
        for j in range(nb):
            c.homeplate(s, px + j * (bw + 0.15), py + ph * 0.3, bw, ph * 0.25, fill=_h.LIGHTEST_PURPLE if j else _h.LIGHT_PURPLE)
            c._rect(s, px + j * (bw + 0.15), py + ph * 0.65, bw, ph * 0.3, fill=_h.OFF_WHITE)
    else:                                   # doc: 文書の行
        for i in range(7):
            ww = pw * (0.95 if i % 3 else 0.7)
            c._rect(s, px, py + i * ph / 7, ww, min(0.07, ph / 14), fill=_h.LIGHT_GRAY if i % 3 else _h.LIGHT_PURPLE)


# ═══════════════════════════════════════════════════════════════
#  M-GANTT（作業の流れ版）
# ═══════════════════════════════════════════════════════════════
OWNER_FILL = {"acn": ("LIGHTEST_PURPLE", None), "client": ("WHITE", "DARK_PURPLE"), "joint": ("LIGHT_PURPLE", None),
              "out": ("OFF_WHITE", "MID_GRAY")}


def gantt_ws(ctx, r, d):
    """{"periods": ["1", "2", ..]（月）, "year": "2026"（任意）,
        "phases": [{"label": "構築", "start": 0, "end": 5}, ...]（上の段の工程の帯・任意）,
        "milestones": [{"at": 5.9, "label": "構築完了"}],
        "tasks": [{"group": "業務・アプリ", "lane": 0, "label": "機能構築", "start": 0, "end": 5, "owner": "acn"}],
        "legend": {"acn": "ACN（準委任）", "client": "貴社", "joint": "共同作業"},
        "scope": {"start": 0, "end": 5, "label": "本検討スコープ"}}
    … 人の資料: 行は作業の流れ（業務・データ・教育…）。同じ流れの作業は同じ行（lane）に横に並べ、作業名はバーの中。
    工程の帯は五方向の矢印、マイルストーンは ▼、担い手は塗りで分けて凡例を右上に置く。"""
    c = _c()
    x, y, w, h = r
    s = ctx.slide
    periods = d.get("periods") or []
    tasks = d.get("tasks") or []
    np_ = max(len(periods), 1)
    lab_w = min(1.9, w * 0.15)
    gx = x + lab_w + 0.06
    pw = (x + w - gx) / np_
    yy = y
    if d.get("legend"):              # 担い手の凡例（本文の右上。メッセージ行には重ねない）
        yy += 0.36
        lx = x + w
        for key in reversed(list(d["legend"])):
            label = d["legend"][key]
            lw = 0.5 + sum(c._char_w(ch, 11) for ch in label)
            lx -= lw + 0.12
            fl, ln = OWNER_FILL.get(key, ("OFF_WHITE", None))
            c._rect(s, lx, y + 0.06, 0.3, 0.2, fill=getattr(_h, fl), line=getattr(_h, ln) if ln else _h.DARK_PURPLE, line_w=0.75)
            c._textbox(s, lx + 0.34, y, lw - 0.3, 0.32, [label], 11, _h.TEXT_BODY, anchor="m", space_after=0,
                       inset=(0, 0, 0, 0))
    if d.get("year"):
        yb = c._rect(s, gx, yy, x + w - gx, 0.3, fill=_h.DARKEST_PURPLE)
        c._shape_text(yb, str(d["year"]), 12, _h.WHITE, True)
        yy += 0.3
    for j, p in enumerate(periods):
        cb = c._rect(s, gx + j * pw, yy, pw, 0.32, fill=_h.DARK_PURPLE, line=_h.WHITE, line_w=0.5)
        c._shape_text(cb, str(p), 12, _h.WHITE, True, inset=(0, 0, 0, 0), wrap=False)
    yy += 0.38
    if d.get("phases"):
        hb = c._rect(s, x, yy, lab_w, 0.4, fill=_h.OFF_WHITE)
        c._shape_text(hb, d.get("phase_label", "フェーズ"), 14, _h.TEXT_BODY, True)
        for ph in d["phases"]:
            a, b_ = float(ph.get("start", 0)), float(ph.get("end", 0))
            pb = c.homeplate(s, gx + a * pw + 0.02, yy + 0.04, (b_ - a + 1) * pw - 0.06, 0.32, fill=_h.LIGHTEST_PURPLE,
                             line=_h.DARKEST_PURPLE, line_w=1.0)
            c._shape_text(pb, ph.get("label", ""), 12, _h.DARKEST_PURPLE, True)
        yy += 0.44
    if d.get("milestones"):
        hb = c._rect(s, x, yy, lab_w, 0.32, fill=_h.OFF_WHITE)
        c._shape_text(hb, d.get("milestone_label", "マイルストーン"), 12, _h.TEXT_BODY, True)
        for m in d["milestones"]:
            mx = gx + float(m.get("at", 0)) * pw
            t = c._rect(s, mx - 0.08, yy + 0.09, 0.16, 0.13, fill=_h.DARK_PURPLE, shape=S.ISOSCELES_TRIANGLE)
            t.rotation = 180
            c._textbox(s, mx + 0.1, yy, 2.2, 0.32, [m.get("label", "")], 11, _h.DARK_PURPLE, bold=True, anchor="m",
                       space_after=0, inset=(0, 0, 0, 0))
        yy += 0.36
    groups = []
    for t in tasks:
        g = t.get("group", "")
        if not groups or groups[-1][0] != g:
            groups.append([g, set()])
        groups[-1][1].add(int(t.get("lane", 0)))
    nl = sum(len(lanes) for _, lanes in groups) or 1
    gg = 0.06
    lane_h = (y + h - yy - gg * (len(groups) - 1) - (0.34 if d.get("scope") else 0)) / nl
    lane_h = min(lane_h, 0.9)
    top_rows = yy
    gy = yy
    rows_end = yy + lane_h * nl + gg * (len(groups) - 1)
    for j in range(1, np_):          # 月の縦の点線（バーの下に描く。バーの塗りで文字の後ろは隠れる）
        ln = c._connector(s, gx + j * pw, top_rows, gx + j * pw, rows_end, color=_h.LIGHT_GRAY, width=0.5, dash=True)
        ln.name = f"Glyph Grid {ln.shape_id}"
    for g, lanes in groups:
        lanes = sorted(lanes)
        gh = lane_h * len(lanes)
        hb = c._rect(s, x, gy, lab_w, gh, fill=_h.OFF_WHITE)
        c._shape_text(hb, g, 14 if len(g) <= 8 else 12, _h.TEXT_BODY, True, inset=(0.05, 0, 0.05, 0))
        for li, ln in enumerate(lanes):
            ly = gy + li * lane_h
            for t in tasks:
                if t.get("group", "") != g or int(t.get("lane", 0)) != ln:
                    continue
                a, b_ = float(t.get("start", 0)), float(t.get("end", t.get("start", 0)))
                bx, bw = gx + a * pw + 0.02, (b_ - a + 1) * pw - 0.06
                fl, lc = OWNER_FILL.get(t.get("owner", "acn"), ("LIGHTEST_PURPLE", None))
                if t.get("highlight"):
                    fl, lc = "DARK_PURPLE", None
                bar = c.homeplate(s, bx, ly + lane_h * 0.12, bw, lane_h * 0.76, fill=getattr(_h, fl),
                                  line=getattr(_h, lc) if lc else _h.DARK_PURPLE, line_w=0.75, tip=min(0.2, lane_h * 0.25))
                sz = 12 if sum(c._char_w(ch, 12) for ch in t.get("label", "")) <= bw - 0.3 else 11
                c._shape_text(bar, t.get("label", ""), sz, _h.WHITE if t.get("highlight") else _h.TEXT_BODY,
                              bool(t.get("highlight")), inset=(0.04, 0, 0.12, 0))
        gy += gh + gg
        c._hline(s, gx, gy - gg / 2, x + w - gx, _h.LIGHT_GRAY, 0.75, dash=True)
    sc = d.get("scope")
    if sc:
        a, b_ = float(sc.get("start", 0)), float(sc.get("end", 0))
        fx0, fx1 = gx + a * pw - 0.02, gx + (b_ + 1) * pw + 0.02
        c._rect(s, fx0, top_rows - 0.06, fx1 - fx0, gy - gg - top_rows + 0.1, fill=None, line=_h.CORE_PURPLE, line_w=2.25)
        lab = sc.get("label", "本検討の範囲")
        tw_ = 0.3 + len(lab) * 0.17
        tag = c._rect(s, fx1 - tw_, gy - gg + 0.04, tw_, 0.28, fill=_h.CORE_PURPLE)
        c._shape_text(tag, lab, 12, _h.WHITE, True, inset=(0.03, 0, 0.03, 0), wrap=False)


# ═══════════════════════════════════════════════════════════════
#  M-TREE（KPI 版）
# ═══════════════════════════════════════════════════════════════
def kpi_tree(ctx, r, d):
    """{"style": "kpi", "root": "EBIT 改善", "heads": ["投資対効果", "施策の方向性と改善率", "施策の具体例"],
        "children": [{"label": "収益改善", "value": "3.0〜3.7%",
                      "children": [{"label": "データドリブン R&D", "value": "0.5〜1%", "details": ["…", "…"]}]}]}
    … 人の資料: 根（濃い紫）→ 中分類（紫・値を添える）→ 施策の箱（淡い紫）＋値のセル、右に具体例の箇条書きから
    施策へ向かう短い ← の矢印。施策の行の間は点線。枝は接続付きのカギ線（0.75pt）。"""
    c, dn = _c(), _d()
    import connect
    x, y, w, h = r
    s = ctx.slide
    mids = d.get("children") or []
    leaves = [(mi, lf) for mi, m in enumerate(mids) for lf in (m.get("children") or [])]
    if not leaves:
        return
    heads = d.get("heads")
    hh = 0.45 if heads else 0
    root_w, mid_w, leaf_w, val_w, arr_w = 1.25, 1.9, 2.5, 1.0, 0.45
    gap = 0.35
    xs = [x, x + root_w + gap, x + root_w + gap + mid_w + gap]
    vx = xs[2] + leaf_w + 0.06
    dx = vx + val_w + arr_w
    dw = x + w - dx
    if heads:
        spans = [(x, xs[1] - gap / 2), (xs[1], vx + val_w), (dx, x + w)] if len(heads) == 3 else []
        for (a, b_), t in zip(spans, heads):
            c._textbox(s, a, y, b_ - a, hh - 0.06, [t], 14, _h.TEXT_BODY, align=PP_ALIGN.CENTER, anchor="b",
                       space_after=0, inset=(0, 0, 0, 0.03))
            c._hline(s, a, y + hh - 0.03, b_ - a, _h.TEXT_BODY, 0.75)
    y0 = y + hh + 0.08
    n = len(leaves)
    rh = (y + h - y0) / n
    gap_r = min(0.08, rh * 0.12)
    det = [dn.rich({"b": lf.get("details") or []}) for _, lf in leaves]
    base = 11
    for sz in (12, 11):
        if all(dn.height(dn.sized(p, sz), dw, sz) <= rh - 0.02 for p in det):
            base = sz
            break
    leaf_shp = []
    for i, (mi, lf) in enumerate(leaves):
        ry = y0 + i * rh
        lb = c._rect(s, xs[2], ry + gap_r / 2, leaf_w, rh - gap_r, fill=_h.LIGHTEST_PURPLE)
        ls, _ = c.fit_size([lf.get("label", "")], leaf_w - 0.15, rh - gap_r, (16, 14, 12))
        c._shape_text(lb, lf.get("label", ""), ls, _h.DARKEST_PURPLE, False, inset=(0.06, 0, 0.06, 0))
        leaf_shp.append(lb)
        if lf.get("value"):
            vb = c._rect(s, vx, ry + gap_r / 2, val_w, rh - gap_r, fill=_h.LIGHTEST_PURPLE)
            vs, _ = c.fit_size([lf["value"]], val_w - 0.1, rh - gap_r, (18, 16, 14))
            c._shape_text(vb, lf["value"], vs, _h.DARK_PURPLE, True, inset=(0.02, 0, 0.02, 0))
        if lf.get("details"):
            c._connector(s, dx - 0.08, ry + rh / 2, vx + val_w + 0.08, ry + rh / 2, color=_h.TEXT_BODY, width=0.75, arrow=True)
            dn.draw_text(ctx, dx, ry, dw, rh, dn.sized(det[i], base), base, anchor="m")
        if i < n - 1:
            c._hline(s, xs[2], ry + rh, x + w - xs[2], _h.MID_GRAY, 0.5, dash=True)
    # 中分類（子の行にまたがる箱）と根
    mid_shp = []
    for mi, m in enumerate(mids):
        rows_i = [i for i, (k, _) in enumerate(leaves) if k == mi]
        if not rows_i:
            mid_shp.append(None)
            continue
        top, bot = y0 + rows_i[0] * rh, y0 + (rows_i[-1] + 1) * rh
        bh = max(0.6, (bot - top) * 0.7)
        mb = c._rect(s, xs[1], (top + bot) / 2 - bh / 2, mid_w, bh, fill=_h.DARK_PURPLE)
        text = m.get("label", "") + (f"\n（{m['value']}）" if m.get("value") else "")
        ms, _ = c.fit_size(text.split("\n"), mid_w - 0.15, bh, (18, 16, 14))
        c._shape_text(mb, text, ms, _h.WHITE, True, inset=(0.06, 0, 0.06, 0))
        mid_shp.append(mb)
        for i in rows_i:
            connect.link(s, mb, leaf_shp[i], "r", "l", _h.TEXT_BODY, 0.75, mid=xs[2] - gap / 2)
    rb_h = min(1.8, (y + h - y0) * 0.35)
    rb = c._rect(s, xs[0], y0 + (y + h - y0) / 2 - rb_h / 2, root_w, rb_h, fill=_h.DARKEST_PURPLE)
    c._shape_text(rb, d.get("root", ""), 18 if len(d.get("root", "")) <= 6 else 16, _h.WHITE, True, inset=(0.05, 0, 0.05, 0))
    for mb in mid_shp:
        if mb is not None:
            connect.link(s, rb, mb, "r", "l", _h.TEXT_BODY, 0.75, mid=xs[1] - gap / 2)


# ═══════════════════════════════════════════════════════════════
#  M-MELON（メロン図: 同心の帯のロードマップ）
# ═══════════════════════════════════════════════════════════════
def _quarter_band(slide, x, y, w, h, rx, ry, fill=None, line=None, line_w=0.75, dash=False):
    """左下をそろえ、右上の角だけを楕円の弧（半径 rx×ry）で丸めた帯（custGeom）。メロン図の 1 段。"""
    from lxml import etree
    from pptx.oxml.ns import qn
    c = _c()
    sh = c._rect(slide, x, y, w, h, fill=fill, line=line, line_w=line_w, dash=dash)
    E = 914400
    W, H, RX, RY = int(w * E), int(h * E), int(min(rx, w) * E), int(min(ry, h) * E)
    sp = sh._element.spPr
    pg = sp.find(qn("a:prstGeom"))
    cg = etree.Element(qn("a:custGeom"))
    for t in ("a:avLst", "a:gdLst", "a:ahLst", "a:cxnLst"):
        etree.SubElement(cg, qn(t))
    rc = etree.SubElement(cg, qn("a:rect"))
    for k_, v_ in (("l", "0"), ("t", "0"), ("r", "r"), ("b", "b")):
        rc.set(k_, v_)
    pl = etree.SubElement(cg, qn("a:pathLst"))
    pa = etree.SubElement(pl, qn("a:path"))
    pa.set("w", str(W))
    pa.set("h", str(H))

    def pt(tag, px, py):
        e = etree.SubElement(pa, qn(tag))
        q = etree.SubElement(e, qn("a:pt"))
        q.set("x", str(px))
        q.set("y", str(py))
    pt("a:moveTo", 0, H)
    pt("a:lnTo", 0, 0)
    pt("a:lnTo", W - RX, 0)
    arc = etree.SubElement(pa, qn("a:arcTo"))
    for k_, v_ in (("wR", str(RX)), ("hR", str(RY)), ("stAng", "16200000"), ("swAng", "5400000")):
        arc.set(k_, v_)
    pt("a:lnTo", W, H)
    etree.SubElement(pa, qn("a:close"))
    pg.addprevious(cg)
    sp.remove(pg)
    return sh


def m_melon(ctx, r, d):
    """メロン図（同心の帯のロードマップ）。
    {"levels": ["データ収集", "データ整理・可視化", "分析・データ活用", "自動化・最適化"]（内側から）,
     "horizons": [{"label": "2029 年度末", "level": 2}, {"label": "2031 年度以降", "level": 3, "dash": true}],
     "goal": ["人が 6 割に減っても業務が回る体制", "保全の高度化"],
     "tracks": [{"label": "ヒト", "milestones": ["改革全体像の更新", {"label": "役職者教育", "t": 0.3}, ..]}, ..]}
    道筋の軸（tracks の label）と本数は自由: ヒト・モノ・コト、業務・データ・システム、組織・業務・データ・システム など（2〜4 本）。
    … 人の資料: 左下をそろえた帯を外側から重ね（内側ほど丸い）、成熟度の段を帯で示す。左に段の名前（帯と同じ色）。
    時期の枠（2.25pt）で「いつまでにどこまで」を囲み、上に札。左下から右上のゴールへ、ヒト・モノ・コトなどの道筋の
    曲線を引き、道筋の上に白い丸のマイルストーンと名前（11pt 太字）を置く。名前は丸・ほかの名前に重ならない側に置く。
    段の色は内側から淡い灰 → ごく淡い紫（#F3E8FF）→ 淡い紫 → 明るい紫（内側ほど基礎。順番で色を交互にしない）。"""
    from pptx.dml.color import RGBColor
    from pptx.util import Inches, Pt
    c = _c()
    x, y, w, h = r
    s = ctx.slide
    levels = d.get("levels") or []
    n = max(len(levels), 1)
    lab_w = 1.35
    gx, gw = x + lab_w + 0.15, w - lab_w - 0.15
    top_pad = 0.42 if d.get("horizons") else 0.05
    gy, gh = y + top_pad, h - top_pad
    xb, yb = gx, gy + gh                          # 左下の基点
    base = [_h.OFF_WHITE, RGBColor(0xF3, 0xE8, 0xFF), _h.LIGHTEST_PURPLE, _h.LIGHT_PURPLE]   # ブランドの許可色だけで 4 段
    fills = base[:n] if n <= 4 else base + [_h.LIGHT_PURPLE] * (n - 4)

    def dims(k):                                  # 段 k（0＝内側）の幅・高さ・角の半径
        f = (k + 1) / n
        ww, hh = gw * (0.42 + 0.58 * f), gh * (0.4 + 0.6 * f)
        t = k / max(n - 1, 1)
        return ww, hh, ww * (0.55 - 0.3 * t), hh * (0.9 - 0.45 * t)      # 内側ほど丸く、外側も角を大きく丸める
    for k in range(n - 1, -1, -1):                # 外側から描く（内側の帯が上に重なる）
        ww, hh, rx, ry = dims(k)
        _quarter_band(s, xb, yb - hh, ww, hh, rx, ry, fill=fills[k])
    prev = 0
    for k, lv in enumerate(levels):               # 左の段の名前（帯の左端に見える高さの中央）
        hh = dims(k)[1]
        cy = yb - (prev + hh) / 2
        bh = min(0.7, (hh - prev) * 0.8)
        lb = c._rect(s, x, cy - bh / 2, lab_w, bh, fill=fills[k])
        c._shape_text(lb, lv, 14 if len(lv) <= 7 else 12, _h.DARKEST_PURPLE, True, align=PP_ALIGN.LEFT,
                      inset=(0.08, 0, 0.04, 0))
        prev = hh
    for j, hz in enumerate(d.get("horizons") or []):     # 時期の枠と札
        k = min(int(hz.get("level", n - 1)), n - 1)
        ww, hh, rx, ry = dims(k)
        col = _h.CORE_PURPLE if hz.get("dash") else _h.DARKEST_PURPLE
        _quarter_band(s, xb, yb - hh, ww, hh, rx, ry, fill=None, line=col, line_w=2.25, dash=bool(hz.get("dash")))
        lab = hz.get("label", "")
        tw = 0.3 + sum(c._char_w(ch, 14) for ch in lab) * 1.1
        tx = xb + (ww - rx) * (0.45 if j == 0 else 0.8) - tw / 2
        tg = c._rect(s, tx, yb - hh - 0.38, tw, 0.32, fill=_h.WHITE, line=col, line_w=1.5)
        c._shape_text(tg, lab, 14, col, True, inset=(0.03, 0, 0.03, 0), wrap=False)
    goal = d.get("goal") or []
    G = (xb + gw * 0.93, gy + gh * 0.1)
    if goal:                                      # ゴール（右上）
        bw = min(3.0, gw * 0.3)
        bh_ = 0.5
        bx0, by0 = x + w - bw, gy - 0.05
        for i, g in enumerate(goal):
            gb = c._rect(s, bx0, by0 + i * (bh_ + 0.08), bw, bh_, fill=_h.DARK_PURPLE)
            c._shape_text(gb, g, 14 if len(g) <= 14 else 12, _h.WHITE, True, inset=(0.06, 0, 0.06, 0))
        G = (bx0, by0 + len(goal) * (bh_ + 0.08) / 2)
    tracks = d.get("tracks") or []
    nt = max(len(tracks), 1)

    def bez(P, t):
        P0, P1, P2 = P
        return ((1 - t) ** 2 * P0[0] + 2 * (1 - t) * t * P1[0] + t * t * P2[0],
                (1 - t) ** 2 * P0[1] + 2 * (1 - t) * t * P1[1] + t * t * P2[1])
    paths = []
    for i, tr in enumerate(tracks):               # 道筋（左下から右上のゴールへの 2 次ベジェ）
        f = i / max(nt - 1, 1)
        # 始点は左下に斜めに並べる（軸の数が増えても名前が重ならないよう、横 0.35in・縦 0.3in ずつ）
        S0 = (xb + 0.85 + 0.35 * i, yb - 0.25 - 0.3 * (nt - 1 - i))
        C1 = (xb + 0.1 + gw * 0.85 * f, gy + gh * (0.12 + 0.8 * f))
        paths.append((S0, C1, G))
        pts = [bez((S0, C1, G), k / 40) for k in range(41)]
        ff = s.shapes.build_freeform(Inches(pts[0][0]), Inches(pts[0][1]))
        ff.add_line_segments([(Inches(px), Inches(py)) for px, py in pts[1:]], close=False)
        ln = ff.convert_to_shape()
        ln.fill.background()
        ln.line.color.rgb = _h.MID_GRAY
        ln.line.width = Pt(0.75)
        c._strip_style(ln)
        if tr.get("label"):         # 軸の名前は始点の左（右揃え）。軸は自由（ヒト・モノ・コト／業務・データ・システム など）
            c._textbox(s, S0[0] - 0.85, S0[1] - 0.14, 0.8, 0.28, [tr["label"]], 14 if len(tr["label"]) <= 4 else 12,
                       _h.DARKEST_PURPLE, bold=True, align=PP_ALIGN.RIGHT, anchor="m", space_after=0, inset=(0, 0, 0.02, 0))
    dd = 0.13
    dots, placed = [], []
    for i, tr in enumerate(tracks):               # マイルストーンの丸（先に全部置く）
        ms = [mm if isinstance(mm, dict) else {"label": str(mm)} for mm in tr.get("milestones") or []]
        tr["_ms"] = ms
        for j, mm in enumerate(ms):
            t = mm.get("t", 0.12 + 0.78 * (j + 0.5) / max(len(ms), 1))
            px, py = bez(paths[i], t)
            dots.append((px - dd / 2, py - dd / 2, dd, dd))
            c._rect(s, px - dd / 2, py - dd / 2, dd, dd, fill=_h.WHITE, line=_h.TEXT_BODY, line_w=0.75, shape=S.OVAL)
            mm["_p"] = (px, py)

    def hit(a, b):
        return a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]
    for tr in tracks:                             # 名前は、丸・ほかの名前に重ならない側に置く
        for mm in tr.pop("_ms", []):
            px, py = mm.pop("_p")
            lines = str(mm.get("label", "")).split("\n")
            lw_ = max(sum(c._char_w(ch, 11) for ch in ln_) for ln_ in lines) * 1.1 + 0.08
            lh_ = 0.19 * len(lines) + 0.06
            cands = [(px + 0.1, py - lh_ / 2), (px - 0.1 - lw_, py - lh_ / 2), (px - lw_ / 2, py - 0.1 - lh_),
                     (px - lw_ / 2, py + 0.1), (px + 0.1, py - lh_ - 0.02), (px + 0.1, py + 0.02),
                     (px - 0.1 - lw_, py - lh_ - 0.02), (px - 0.1 - lw_, py + 0.02)]
            own = (px - dd / 2, py - dd / 2, dd, dd)

            def free(q):
                rr = (q[0], q[1], lw_, lh_)
                if rr[0] < gx or rr[0] + rr[2] > x + w or rr[1] < gy or rr[1] + rr[3] > yb:
                    return False
                return not any(hit(rr, b) for b in placed + [b_ for b_ in dots if b_ != own])
            q = next((q_ for q_ in cands if free(q_)), None)
            if q is None:
                ctx.warn(f"M-MELON: マイルストーン「{lines[0][:10]}」の名前を重ならずに置けない（t で位置をずらす）")
                q = cands[0]
            placed.append((q[0], q[1], lw_, lh_))
            c._textbox(s, q[0], q[1], lw_, lh_, lines, 11, _h.TEXT_BODY, bold=True, space_after=0,
                       inset=(0.02, 0, 0.02, 0), line_spacing=0.95)


MODULES = {"M-CASELIST": m_caselist, "M-COLCARDS": m_colcards, "M-PROGRAM": m_program, "M-OUTPUTS": m_outputs, "M-MELON": m_melon}
