"""
org.py — 体制図（提案書の「推進体制（案）」のページ）。

  M-ORG          体制図。貴社／アクセンチュアの系列を左右に並べ、見出し帯付きの役割箱を階層の線でつなぐ。
                 同じ高さのカウンターパートを横の線で結び、提案範囲の枠・凡例・注記を付けられる。
  M-ORG-PYRAMID  廃止（v6.4）。人の提案書に体制ピラミッドの作りは無い。渡されたら会議体の表（M-TABLE）に置き換える。

人の提案書（52 本中の体制ページと公式テンプレートの Teams and People）の作りに合わせる:
- 箱は「塗りの見出し帯（役職）＋白地に細い枠の本文（氏名・人数）」。顧客側は灰、自社側は紫の帯
- 親子は直角の線（親の下辺 → 子の上辺）。兄弟は横の線で束ねる。脇に付く役割（SME・PMO など）は横から結ぶ
- 顧客と自社の同じ階層は同じ高さに揃え、横の線（必要なら「連携」のラベル）で結ぶ
- 提案範囲は紫の破線で囲み、左上にラベル。凡例（フルタイム／パートタイム）は右上、注記は左下
data の形は references/compose-api.md を参照。
"""

from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE as S
from pptx.enum.text import PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches
from lxml import etree

import helpers as _h

HEAD_H = 0.3      # 役職の見出し帯
SIDE_HDR = 0.42   # 「貴社」「アクセンチュア」の見出し
MAX_BOX_W = 2.4


def _c():
    import compose
    return compose


def _both_arrows(conn):
    ln = conn.line._get_or_add_ln()
    for tag in ("a:headEnd", "a:tailEnd"):
        e = etree.SubElement(ln, qn(tag))
        e.set("type", "triangle")
        e.set("w", "med")
        e.set("len", "med")


# ═══════════════════════════════════════════════════════════════
#  M-ORG
# ═══════════════════════════════════════════════════════════════
def _body_paras(n):
    ppl = n.get("people") if n.get("people") is not None else n.get("text")
    if ppl is None:
        return []
    ppl = ppl if isinstance(ppl, list) else [ppl]
    return [str(p) for p in ppl]


def _one_line(c, texts, w, sizes=(14, 12), bold=False):
    """すべての行が 1 行に収まる最大の文字サイズ（収まらなければ None）。
    太字は 8% 広い（Meiryo UI Bold の実測）。描画の誤差に備えて 3% の余裕を見る。"""
    eff = (w - 0.12) / (1.08 if bold else 1.0) * 0.92 + 0.12   # 検査（verify_pptx）の見積もりと食い違わない余裕
    for sz in sizes:
        if all(c.est_lines(t, eff, sz) == 1 for t in texts):
            return sz
    return None


_BREAK = (" ", "　", "・", "（", "(", "/", "／")


def _split_line(c, text, w, sz, bold=False):
    """1 行に入らない語句を、空白・中黒・括弧の前で 2 行に分ける（人が手で改行する位置）。分けられなければ None。"""
    cands = [i for i, ch in enumerate(text) if ch in _BREAK and 0 < i < len(text) - 1]
    cands.sort(key=lambda i: abs(i - len(text) / 2))
    for i in cands:
        a, b = text[:i].rstrip(), text[i:].lstrip(" 　") if text[i] in " 　" else text[i:]
        a = a + "・" if text[i] == "・" else a
        b = b[1:] if text[i] == "・" else b
        if _one_line(c, [a, b], w, (sz,), bold):
            return [a, b]
    return None


def _fit_lines(c, texts, w, bold=False):
    """各行を 1 行（だめなら自然な位置で 2 行）に収める最大サイズと、改行後の行。"""
    for sz in (14, 12):
        out = []
        for t in texts:
            if _one_line(c, [t], w, (sz,), bold):
                out.append(t)
            else:
                sp = _split_line(c, t, w, sz, bold)
                if not sp:
                    break
                out += sp
        else:
            return sz, out
    return None, texts


PERSON_H = 0.2      # 人のアイコンの高さ（文字 1 行分）
MEMBER_ROW = 0.27   # メンバー 1 行の高さ
KIND_LABEL = {"full": "フルタイム", "part": "パートタイム", "sme": "専門家（SME）"}


def _members(n):
    """members: ["氏名", {"name": "氏名", "kind": "full|part|sme"}, ...]。文字列の末尾 (F)/(P) も読む。"""
    out = []
    for m in n.get("members") or []:
        if isinstance(m, str):
            k = "part" if m.rstrip().endswith(("(P)", "（P）")) else "full"
            out.append({"name": m.replace("(F)", "").replace("(P)", "").replace("（F）", "").replace("（P）", "").strip(), "kind": k})
        else:
            out.append({"name": m.get("name", ""), "kind": m.get("kind", "full")})
    return out


def _member_cols(n, bw):
    k = len(_members(n))
    return 1 if k <= 3 or bw < 2.0 else 2


def person(c, s, x, y, kind="full", hgt=PERSON_H):
    """人のアイコン（頭の楕円＋胴の四角）。full: 塗り / part: 胴が白 / sme: 線だけ。"""
    col = _h.DARK_PURPLE
    hd = hgt * 0.52
    bw_ = hgt * 0.78
    head = c._rect(s, x + (bw_ - hd) / 2, y, hd, hd, fill=None if kind == "sme" else col, line=col, line_w=0.75,
                   shape=S.OVAL)
    body = c._rect(s, x, y + hd + hgt * 0.04, bw_, hgt - hd - hgt * 0.04, fill=col if kind == "full" else _h.WHITE,
                   line=col, line_w=0.75)
    return head, body


def _measure(c, n, bw):
    """役割箱の見出し（サイズ・高さ・行）と本文（サイズ・高さ・行）。語句の途中で折り返さないサイズと改行位置を選ぶ。"""
    hs, hl = _fit_lines(c, [n.get("role", "")], bw + 0.08, bold=True)   # 見出しの内余白は左右 0.02
    head = (hs or 12, HEAD_H if len(hl) == 1 and hs else HEAD_H + 0.2, hl)
    if n.get("members"):
        import math
        rows = math.ceil(len(_members(n)) / _member_cols(n, bw))
        return head, (12, rows * MEMBER_ROW + 0.1, ["__members__"])
    paras = _body_paras(n)
    if not paras:
        return head, (14, 0.12, [])
    bs, bl = _fit_lines(c, paras, bw)                                     # 本文の内余白は左右 0.06
    if bs is None:
        bs, _ = c.fit_size(paras, bw, 9, (14, 12), 0)
    return head, (bs, c.est_height(bl, bw, bs, 0), bl)


def _layout_side(side, n_rows):
    """系列の中で、各役割箱の列位置（スロット）と行を決める。脇の役割（attach）は右端の列にまとめる。"""
    nodes = side.get("nodes") or []
    ids = {n.get("id", n.get("role", f"n{i}")): n for i, n in enumerate(nodes)}
    for i, n in enumerate(nodes):
        n.setdefault("id", n.get("role", f"n{i}"))
    kids = {}
    for n in nodes:
        if n.get("parent") in ids and not n.get("attach"):
            kids.setdefault(n["parent"], []).append(n)
    roots = [n for n in nodes if n.get("parent") not in ids and not n.get("attach")]

    def depth(n):
        d, p = 0, n.get("parent")
        while p in ids and d < 10:
            d, p = d + 1, ids[p].get("parent")
        return d

    def width(n):
        ks = kids.get(n["id"], [])
        return max(1, sum(width(k) for k in ks))

    def place(n, left):
        n["_row"] = n.get("layer", depth(n))
        ks = kids.get(n["id"], [])
        if not ks:
            n["_slot"] = left + 0.5
            return left + 1
        cur = left
        for k in ks:
            cur = place(k, cur)
        n["_slot"] = (ks[0]["_slot"] + ks[-1]["_slot"]) / 2
        return cur

    cur = 0
    for r in roots:
        cur = place(r, cur)
    att = [n for n in nodes if n.get("attach")]
    if att:
        for n in att:
            p = ids.get(n.get("parent"))
            n["_row"] = n.get("layer", p.get("_row", 0) if p else 0)
            n["_slot"] = cur + 0.5
        cur += 1
    for n in nodes:
        n["_row"] = min(n.get("_row", 0), n_rows - 1)
    return nodes, ids, kids, max(cur, 1)


def m_org(ctx, r, d):
    """{"sides": [{"label": "貴社", "tone": "gray", "nodes": [{"id": "po", "role": "プロジェクトオーナー", "people": ["部長"]},
                                                            {"id": "pm", "role": "PM", "parent": "po"}]},
                   {"label": "アクセンチュア", "nodes": [...], "scope": "ご提案範囲"}],
        "links": [["pm", "acn_pm", "連携"]],          # 系列をまたぐ線（同じ高さならまっすぐ横）
        "legend": ["(F) フルタイム", "(P) パートタイム"], "note": "※本体制図は指揮命令系統を示すものではありません"}
    node: id / role / people(str|list) / members([氏名 | {name, kind: full|part|sme}] 人のアイコン付き) / parent /
          layer(行の番号) / attach(true: 親の横に付く役割) / scope(true: 提案範囲) / emph"""
    c = _c()
    x, y, w, h = r
    s = ctx.slide
    sides = d.get("sides") or [{"label": "", "nodes": d.get("nodes") or []}]
    if d.get("layers"):    # v6.4: 体制ピラミッドは廃止（人の体制図に無い組み合わせで、主役の体制図がぼやける）
        ctx.warn("M-ORG: layers（体制ピラミッド）は廃止。会議体は別ページの表（M-TABLE / M-MATRIX-SYM）で示す")
    n_rows = 1
    laid = []
    for sd in sides:
        nodes, ids, kids, slots = _layout_side(sd, 99)
        laid.append((sd, nodes, ids, kids, slots))
        n_rows = max(n_rows, max([n["_row"] for n in nodes] + [0]) + 1)

    # 横の配分: 系列（スロット数に比例）
    gap_side = 0.6 if len(sides) > 1 else 0
    total_slots = sum(L[4] for L in laid)
    unit = (w - gap_side * (len(sides) - 1)) / max(total_slots, 1)
    bw = min(MAX_BOX_W, unit - 0.16)
    if bw < 1.2:
        ctx.warn("M-ORG: 役割箱が多く、箱の幅が狭い（1 行に並ぶ箱を減らすか、チームをまとめる）")

    # 縦の配分: 行ごとに箱の高さ（中身の量）を出し、行の間に線の余地を取る
    note_h = 0.3 if d.get("note") else 0
    top = y + (SIDE_HDR + 0.12 if any(sd.get("label") for sd in sides) else 0)
    avail = y + h - note_h - top
    row_h = [HEAD_H + 0.3] * n_rows
    for sd, nodes, *_ in laid:
        for n in nodes:
            (hs, hh, _), (bs, ph, _) = n["_m"] = _measure(c, n, bw)
            row_h[n["_row"]] = max(row_h[n["_row"]], hh + ph + 0.1)
    gap = (avail - sum(row_h)) / max(n_rows - 1, 1) if n_rows > 1 else 0
    gap = max(0.32, min(gap, 0.75)) if n_rows > 1 else 0
    used = sum(row_h) + gap * (n_rows - 1)
    if used > avail + 0.05:
        ctx.warn("M-ORG: 体制図が縦に収まらない（階層か人数の行を減らす）")
    row_y = []
    yy = top + max(0, (avail - used) * 0.25)
    for rh in row_h:
        row_y.append(yy)
        yy += rh + gap

    shp = {}      # id → (見出し帯, 本体の枠)。コネクタの接続先
    boxes = {}
    used_kinds = set()
    sx = x
    for k, (sd, nodes, ids, kids, slots) in enumerate(laid):
        sw = slots * unit
        if sd.get("label"):
            c.pane_header(ctx, (sx, y, sw, h), sd["label"], style="rule")
        purple = sd.get("tone", "purple" if k == len(laid) - 1 else "gray") == "purple"   # 自社（最後の系列）を紫に
        for n in nodes:
            bx = sx + n["_slot"] * unit - bw / 2
            by = row_y[n["_row"]]
            (hs, hh, hl), (bs, ph, paras) = n["_m"]
            bh = max(hh + ph + 0.1, hh + 0.3)
            on = n.get("emph")
            # 見出し帯は構造の色（濃い紫・灰）。明るい紫は提案範囲の枠とタグだけに使う（紫の意味を固定する）
            band_col = (_h.DARK_PURPLE if on else _h.DARKEST_PURPLE) if purple else (_h.DARK_PURPLE if on else _h.MID_GRAY)
            band = c._rect(s, bx, by, bw, hh, fill=band_col)
            c._shape_text(band, hl, hs, _h.WHITE, True, inset=(0.02, 0, 0.02, 0))
            frame = c._rect(s, bx, by + hh, bw, bh - hh, fill=None, line=_h.LIGHT_GRAY, line_w=0.75)
            shp[n["id"]] = (band, frame)
            if paras == ["__members__"]:          # 人のアイコン＋氏名を 1〜2 列で並べる
                mem = _members(n)
                ncol = _member_cols(n, bw)
                cw_ = (bw - 0.16) / ncol
                rows = -(-len(mem) // ncol)
                y0 = by + hh + (bh - hh - rows * MEMBER_ROW) / 2
                for i, m in enumerate(mem):
                    rr, cc = divmod(i, ncol)
                    mx, my = bx + 0.1 + cc * cw_, y0 + rr * MEMBER_ROW
                    person(c, s, mx, my + (MEMBER_ROW - PERSON_H) / 2, m["kind"])
                    c._textbox(s, mx + PERSON_H * 0.78 + 0.08, my, cw_ - PERSON_H - 0.06, MEMBER_ROW, [m["name"]], 12,
                               _h.TEXT_BODY, anchor="m", space_after=0, inset=(0, 0, 0, 0))
                used_kinds.update(m["kind"] for m in mem)
            elif paras:
                c._textbox(s, bx, by + hh + 0.02, bw, bh - hh - 0.02, paras, bs, _h.TEXT_BODY, anchor="m",
                           align=PP_ALIGN.CENTER, space_after=0, inset=(0.06, 0.02, 0.06, 0.02))
            boxes[n["id"]] = (bx, by, bw, bh, n)
        # 親子の線: 親の下辺 → 子の上辺の接続付きのカギ線（子ごとに 1 本。重なった横の部分が束ね線に見える）
        import connect
        for pid, ks in kids.items():
            if pid not in boxes:
                continue
            pbx, pby, pbw, pbh, _ = boxes[pid]
            child_top = min(boxes[k["id"]][1] for k in ks)
            mid = (pby + pbh + child_top) / 2
            for k in ks:
                if k["id"] in shp:
                    connect.link(s, shp[pid][1], shp[k["id"]][0], "b", "t", _h.MID_GRAY, 1.0, mid=mid)
        # 脇の役割（親の右辺から横に結ぶ。高さが違えば親の下辺 → 脇の左辺の L 字）
        for n in nodes:
            if n.get("attach") and n.get("parent") in boxes and n["id"] in shp:
                pbx, pby, pbw, pbh, _ = boxes[n["parent"]]
                ax, ay, aw, ah, _ = boxes[n["id"]]
                if abs(ay - pby) < 0.02:
                    connect.link(s, shp[n["parent"]][0], shp[n["id"]][0], "r", "l", _h.MID_GRAY, 1.0)
                else:
                    connect.link(s, shp[n["parent"]][1], shp[n["id"]][1], "b", "l", _h.MID_GRAY, 1.0)
        # 提案範囲の枠
        sc = [boxes[n["id"]] for n in nodes if n.get("scope")]
        if sc or sd.get("scope_all"):
            sc = [boxes[n["id"]] for n in nodes] if sd.get("scope_all") else sc   # scope_all: 系列の全員を囲む
            fx = min(b[0] for b in sc) - 0.1
            fy = min(b[1] for b in sc) - 0.1
            fw = max(b[0] + b[2] for b in sc) + 0.1 - fx
            fh = max(b[1] + b[3] for b in sc) + 0.1 - fy
            c._rect(s, fx, fy, fw, fh, fill=None, line=_h.CORE_PURPLE, line_w=2.0, dash=True)
            lab = sd.get("scope") if isinstance(sd.get("scope"), str) else "ご提案範囲"
            tw = 0.25 + len(lab) * 0.17
            tag = c._rect(s, fx + fw - tw, fy + fh, tw, 0.28, fill=_h.CORE_PURPLE)
            c._shape_text(tag, lab, 12, _h.WHITE, True, inset=(0.03, 0, 0.03, 0), wrap=False)
        sx += sw + gap_side

    # 系列をまたぐ線
    for lk in d.get("links") or []:
        a, b = boxes.get(lk[0]), boxes.get(lk[1])
        if not a or not b:
            ctx.warn(f"M-ORG: 線の端の役割が見つからない: {lk[:2]}")
            continue
        if a[0] > b[0]:
            a, b = b, a
        ya, yb = a[1] + a[3] / 2, b[1] + b[3] / 2
        label = lk[2] if len(lk) > 2 else None
        between = [o for o in boxes.values() if o is not a and o is not b and o[0] > a[0] + a[2] - 0.01
                   and o[0] + o[2] < b[0] + 0.01 and o[1] < max(a[1] + a[3], b[1] + b[3]) and o[1] + o[3] > min(a[1], b[1])]
        if between:                    # 間に別の箱がある: 線は引かない（人の資料も向かい合う箱どうしだけを結ぶ）
            ctx.warn(f"M-ORG: {lk[0]}〜{lk[1]} の間に別の箱があるため線を省いた（向かい合う位置に並べ替える）")
            continue
        import connect
        sa_, sb_ = shp.get(a[4]["id"]), shp.get(b[4]["id"])
        same = abs(a[1] - b[1]) < 0.02
        yl = a[1] + min(a[3], b[3]) / 2 + HEAD_H / 2 if same else (ya + yb) / 2
        if sa_ and sb_:          # 向かい合う箱の本体どうしを、接続付きの線で（高さが違えばカギ線）
            connect.link(s, sa_[1] if same else sa_[1], sb_[1], "r", "l", _h.DARK_PURPLE if label else _h.MID_GRAY,
                         2.0 if label else 1.0, both=bool(label), dash=not label)
        if label:
            mx = (a[0] + a[2] + b[0]) / 2
            c._textbox(s, mx - 0.6, yl - 0.3, 1.2, 0.26, [label], 12, _h.DARK_PURPLE, bold=True, align=PP_ALIGN.CENTER,
                       anchor="b", space_after=0, inset=(0, 0, 0, 0))

    if used_kinds:            # 人のアイコンの凡例（右上）。使った種類だけ
        labels = {**KIND_LABEL, **(d.get("people_legend") or {})}
        kinds = [k for k in ("full", "part", "sme") if k in used_kinds]
        ws = [PERSON_H * 0.78 + 0.08 + sum(c._char_w(ch, 11) for ch in labels[k]) + 0.25 for k in kinds]
        lx = r[0] + r[2] - sum(ws)
        for k, ww in zip(kinds, ws):
            person(c, s, lx, y - 0.3, k)
            c._textbox(s, lx + PERSON_H * 0.78 + 0.06, y - 0.36, ww, 0.3, [labels[k]], 11, _h.TEXT_SUB, anchor="m",
                       space_after=0, inset=(0, 0, 0, 0))
            lx += ww
    elif d.get("legend"):
        leg = d["legend"] if isinstance(d["legend"], list) else [d["legend"]]
        text = "　".join(leg)
        lw = min(w, 0.3 + len(text) * 0.15)
        c._textbox(s, r[0] + r[2] - lw, y - 0.34, lw, 0.3, [text], 12, _h.TEXT_SUB, align=PP_ALIGN.RIGHT, anchor="m",
                   space_after=0)
    if d.get("note"):
        c._textbox(s, r[0], y + h - note_h, r[2], note_h, [d["note"]], 12, _h.TEXT_SUB, anchor="b", space_after=0)


# ═══════════════════════════════════════════════════════════════
#  M-ORG-PYRAMID（廃止 → 会議体の表）
# ═══════════════════════════════════════════════════════════════
def m_org_pyramid(ctx, r, d):
    """v6.4 で廃止。旧い outline のために、段（layers）の cells を会議体の表（M-TABLE）に置き換えて描く。"""
    c = _c()
    ctx.warn("M-ORG-PYRAMID は廃止。会議体は M-TABLE（会議名・目的・参加者・頻度）で描いた")
    cols = d.get("columns") or []
    rows = []
    for L in d.get("layers") or []:
        cells = [("、".join(x) if isinstance(x, list) else str(x)) for x in (L.get("cells") or [])]
        rows.append(cells or [L.get("label", "")])
    c.m_table(ctx, r, {"columns": cols, "rows": rows, "col_widths": d.get("col_weights")})


def register(modules):
    modules.update({"M-ORG": m_org, "M-ORG-PYRAMID": m_org_pyramid})
