"""v8：ユーザー修正版v7に、具体例（検査項目：総蛋白）の図のスライドを1枚追加する（1枚目の次に挿入）。
自院が臨床情報詳細画面で見る名称と、他院がPDFで見る名称が異なることを示す。
体裁は手本（20260902_血液型の共有について.pptx）のラベル・アイコン・中央基盤の囲みに合わせる。
使い方：python 本ファイル <ユーザー修正版v7> <手本pptx> <出力pptx>
"""
import copy
import sys
from pptx import Presentation
from pptx.util import Cm, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.opc.constants import RELATIONSHIP_TYPE as RT
from pptx.oxml.ns import qn
from lxml import etree

SRC, REF, OUT = sys.argv[1:4]
prs = Presentation(SRC)
ref = Presentation(REF)

first = prs.slides[0]
LAYOUT = first.slide_layout
LABEL = next(copy.deepcopy(sh._element) for sh in first.shapes if sh.name.startswith("ラベル"))
BODY = next(copy.deepcopy(sh._element) for sh in first.shapes if sh.is_placeholder and sh.placeholder_format.idx == 1)
ICON = next(sh for sh in ref.slides[1].shapes if sh.shape_type == 13)
ICON_XML = copy.deepcopy(ICON._element)
ICON_PART = ref.slides[1].part.rels[etree.ElementBase.xpath(ICON._element, ".//asvg:svgBlip/@r:embed", namespaces={
    "asvg": "http://schemas.microsoft.com/office/drawing/2016/SVG/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"})[0]].target_part

NAVY = RGBColor(0x1F, 0x49, 0x7D)
RED = RGBColor(0xC0, 0x00, 0x00)
ORANGE = RGBColor(0xF7, 0x96, 0x46)
GRAY = RGBColor(0x7F, 0x7F, 0x7F)
BLACK = RGBColor(0, 0, 0)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
_id = [500]


def nid():
    _id[0] += 1
    return str(_id[0])


def set_xfrm(el, x, y, w, h):
    xf = el.find(".//" + qn("a:xfrm")) if el.find(".//" + qn("a:xfrm")) is not None else el.find(".//" + qn("p:xfrm"))
    off = xf.find(qn("a:off")); ext = xf.find(qn("a:ext"))
    off.set("x", str(int(Cm(x)))); off.set("y", str(int(Cm(y))))
    ext.set("cx", str(int(Cm(w)))); ext.set("cy", str(int(Cm(h))))


def label(s, text, x, y, w=4.57):
    el = copy.deepcopy(LABEL)
    el.find(".//" + qn("p:cNvPr")).set("id", nid())
    set_xfrm(el, x, y, w, 0.69)
    el.find(".//" + qn("a:t")).text = text
    s.shapes._spTree.append(el)


def body(s, paras, x, y, w, h, size=1200):
    el = copy.deepcopy(BODY)
    el.find(".//" + qn("p:cNvPr")).set("id", nid())
    set_xfrm(el, x, y, w, h)
    tx = el.find(qn("p:txBody"))
    for p in tx.findall(qn("a:p")):
        tx.remove(p)
    for para in paras:
        p = etree.SubElement(tx, qn("a:p"))
        ppr = etree.SubElement(p, qn("a:pPr"), marL="285750", indent="-285750")
        sa = etree.SubElement(ppr, qn("a:spcAft")); etree.SubElement(sa, qn("a:spcPts"), val="300")
        etree.SubElement(ppr, qn("a:buFont"), typeface="Arial", panose="020B0604020202020204", pitchFamily="34", charset="0")
        etree.SubElement(ppr, qn("a:buChar"), char="•")
        for t, o in ([(para, {})] if isinstance(para, str) else para):
            r = etree.SubElement(p, qn("a:r"))
            rpr = etree.SubElement(r, qn("a:rPr"), lang="ja-JP", altLang="en-US", sz=str(size))
            if o.get("bold"):
                rpr.set("b", "1")
            etree.SubElement(r, qn("a:t")).text = t
    s.shapes._spTree.append(el)


def box(s, x, y, w, h, fill=None, line=GRAY, shape=MSO_SHAPE.ROUNDED_RECTANGLE, lw=1.0, dash=False):
    b = s.shapes.add_shape(shape, Cm(x), Cm(y), Cm(w), Cm(h))
    if shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        b.adjustments[0] = 0.06
    if fill is None:
        b.fill.background()
    else:
        b.fill.solid(); b.fill.fore_color.rgb = fill
    if line is None:
        b.line.fill.background()
    else:
        b.line.color.rgb = line; b.line.width = Pt(lw)
        if dash:
            from pptx.enum.dml import MSO_LINE
            b.line.dash_style = MSO_LINE.DASH
    b.shadow.inherit = False
    b.text_frame.text = ""
    return b


def text(s, x, y, w, h, lines, size=11, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, shape=None):
    """lines: [str | [(text, {bold,color,size,underline})]]"""
    tb = shape if shape is not None else s.shapes.add_textbox(Cm(x), Cm(y), Cm(w), Cm(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Cm(0.15)
    tf.margin_top = tf.margin_bottom = Cm(0.05)
    for i, ln in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        for t, o in ([(ln, {})] if isinstance(ln, str) else ln):
            r = p.add_run(); r.text = t
            r.font.name = "Meiryo UI"; r.font.size = Pt(o.get("size", size))
            r.font.bold = o.get("bold", False); r.font.underline = o.get("underline", False)
            r.font.color.rgb = o.get("color", BLACK)
            rpr = r._r.get_or_add_rPr(); etree.SubElement(rpr, qn("a:ea"), typeface="Meiryo UI")
    return tb


def arrow(s, x1, y1, x2, y2, color=GRAY, w=1.5, dash=False):
    c = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Cm(x1), Cm(y1), Cm(x2), Cm(y2))
    c.line.color.rgb = color; c.line.width = Pt(w)
    ln = c.line._get_or_add_ln()
    if dash:
        etree.SubElement(ln, qn("a:prstDash"), val="dash")
    etree.SubElement(ln, qn("a:tailEnd"), type="triangle", w="med", len="med")
    return c


def icon(s, x, y, size=1.5):
    el = copy.deepcopy(ICON_XML)
    el.find(".//" + qn("p:cNvPr")).set("id", nid())
    rid = s.part.relate_to(ICON_PART, RT.IMAGE)
    for b in el.iter("{http://schemas.microsoft.com/office/drawing/2016/SVG/main}svgBlip"):
        b.set(qn("r:embed"), rid)
    set_xfrm(el, x, y, size, size)
    s.shapes._spTree.append(el)


B = {"bold": True}

# ---- 具体例スライド（本田さん作成の血液型資料1/2下部の図の作りに合わせる） ----
LIGHTBLUE = RGBColor(0xC5, 0xD9, 0xF1)
s = prs.slides.add_slide(LAYOUT)
for ph in list(s.placeholders):
    if ph.placeholder_format.idx == 1:
        ph._element.getparent().remove(ph._element)
s.shapes.title.text = "X.臨床情報詳細画面とPDF帳票の名称の差について（具体例）"

label(s, "具体例（検査項目の場合）", 1.37, 2.3, w=6.2)
body(s, [
    [("医療機関Aが、検査項目「総タンパク」を", {}), ("JLAC10コード付き", B), ("で登録した場合、", {}), ("自院（A）が臨床情報詳細画面で見る名称と、他院（B）がPDFで見る名称が異なる。", B)],
], 1.37, 3.0, 24.8, 1.2)


NAVY2 = RGBColor(0x1F, 0x38, 0x64)


def panel(x, y, w, h, head, sub):
    box(s, x, y, w, h, fill=WHITE, line=GRAY, shape=MSO_SHAPE.RECTANGLE, lw=0.75)
    hd = box(s, x, y, w, 0.8, fill=LIGHTBLUE, line=GRAY, shape=MSO_SHAPE.RECTANGLE, lw=0.75)
    text(s, 0, 0, 0, 0, [[(head, {"bold": True, "size": 10.5})]], align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, shape=hd)
    sb = box(s, x + 0.2, y + 1.0, w - 0.4, 0.65, fill=RGBColor(0xDC, 0xE6, 0xF2), line=GRAY, shape=MSO_SHAPE.RECTANGLE, lw=0.5)
    text(s, 0, 0, 0, 0, [[(sub, {"bold": True, "size": 9.5})]], align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, shape=sb)


def caption(x, y, w, h, lines):
    c = box(s, x, y, w, h, fill=WHITE, line=RED, shape=MSO_SHAPE.RECTANGLE, lw=1.25)
    text(s, 0, 0, 0, 0, [[(t, {"bold": True, "size": 9.5, "color": RED})] for t in lines], align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, shape=c)


def block_arrow(x, y, w=1.3, h=1.3):
    ar = s.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, Cm(x), Cm(y), Cm(w), Cm(h))
    ar.fill.solid(); ar.fill.fore_color.rgb = NAVY2; ar.line.fill.background(); ar.shadow.inherit = False


def output(y, head, sub, name, cap):
    panel(11.7, y, 9.0, 4.5, head, sub)
    scr = box(s, 12.0, y + 1.85, 8.4, 2.45, fill=WHITE, line=GRAY, lw=0.75)
    text(s, 0, 0, 0, 0, [[("患者名：厚労太郎", {"size": 9.5})]], shape=scr)
    hl = box(s, 12.3, y + 2.45, 7.8, 0.9, fill=WHITE, line=RED, shape=MSO_SHAPE.RECTANGLE, lw=1.5)
    text(s, 0, 0, 0, 0, [[("検査項目：", {"size": 11}), (name, {"size": 12, "bold": True, "color": RED})]], anchor=MSO_ANCHOR.MIDDLE, shape=hl)
    text(s, 12.3, y + 3.4, 7.8, 0.7, ["検査結果：7.0 g/dL"], size=9.5)
    caption(21.0, y + 0.9, 5.1, 2.8, cap)


# 左：登録する情報（1つ）
panel(1.4, 4.5, 8.4, 10.1, "医療機関Aが登録する情報", "登録データ（FHIR）")
card = box(s, 1.8, 6.4, 7.6, 5.4, fill=WHITE, line=GRAY, lw=0.75)
text(s, 0, 0, 0, 0, [
    [("Bundleリソース", {"size": 9})],
    [("患者名：厚労太郎", {"size": 9})],
    [("", {"size": 5})],
    [("Observationリソース", {"size": 9, "bold": True})],
    [("code.text：", {"size": 10}), ("総タンパク", {"size": 10, "bold": True, "color": RED})],
    [("code.coding（JLAC10）", {"size": 10})],
    [("　code：（総蛋白のJLAC10コード）", {"size": 9})],
    [("　display：", {"size": 10}), ("TP", {"size": 10, "bold": True, "color": RED})],
    [("valueQuantity：7.0 g/dL", {"size": 10})],
], shape=card)
caption(1.8, 12.1, 7.6, 2.2, ["医療機関の項目名（code.text）と、", "JLAC10の固定の名称（display：TP）の", "両方が登録される"])

# 右：2つの出力
block_arrow(10.1, 6.1)
block_arrow(10.1, 11.3)
output(4.5, "自院（医療機関A）", "臨床情報詳細画面（資格確認端末）", "総タンパク",
       ["自院の画面は、", "code.textを表示", "→「総タンパク」"])
output(10.1, "他院（医療機関B）", "臨床情報一覧（PDF帳票）", "TP",
       ["他院のPDFは、", "JLAC10のdisplayを表示※", "→「TP」"])
text(s, 15.4, 8.95, 1.6, 1.2, [[("≠", {"bold": True, "size": 24, "color": NAVY2})]], align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

summ = box(s, 1.4, 15.0, 24.7, 1.2, fill=RGBColor(0xFB, 0xE5, 0xD6), line=ORANGE, shape=MSO_SHAPE.RECTANGLE, lw=1.5)
text(s, 0, 0, 0, 0, [[("同じ登録データでも、自院が確認する名称（総タンパク）と他院が見る名称（TP）が異なり、自院の画面では他院に届く名称を確認できない", {"bold": True, "size": 11})]], align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, shape=summ)
text(s, 1.4, 16.4, 24.7, 1.2, [
    [("※技術解説書の記載どおりFHIR項目名称に変換している場合は「総蛋白(TP)」。いずれの場合も自院の画面の「総タンパク」とは異なる（変換の有無は機構に確認中）。", {"size": 9})],
    [("※名称・値は説明のための例。PDFの名称は、DX機構の調査結果（10/6）の記載「JLAC10のコードセットのディスプレイ値」と、JLACコードマスタのFHIR識別文字列（総蛋白＝TP）による。", {"size": 9})],
])

# 1枚目の次へ移す
lst = prs.slides._sldIdLst
el = lst[-1]
lst.remove(el)
lst.insert(1, el)

cp = prs.core_properties
for k in ("author", "last_modified_by", "title", "subject", "keywords", "comments", "category"):
    setattr(cp, k, "")
pkg = prs.part.package
for rId, rel in list(pkg._rels.items()):
    if rel.reltype.endswith("/custom-properties"):
        pkg._rels.pop(rId)
prs.save(OUT)
print("saved")
