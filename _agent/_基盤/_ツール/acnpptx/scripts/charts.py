"""
PPTX Skill — Native Chart Helpers (python-pptx)

Charts use the active theme's brand colors via helpers.py.
No SVG / No Node.js required — uses python-pptx's built-in chart engine.

Usage:
    from charts import add_column_chart, add_bar_chart, add_line_chart, add_pie_chart

Chart data format (series_data):
    [
        {"name": "Series A", "values": [10, 20, 30]},
        {"name": "Series B", "values": [15, 25, 35]},
    ]
"""

from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.chart.data import ChartData
from pptx.enum.chart import (
    XL_CHART_TYPE, XL_LEGEND_POSITION, XL_LABEL_POSITION, XL_TICK_MARK
)
from lxml import etree
import helpers as _h

# ── Chart series palette — reads from helpers.py at call time ─────────────────
# When load_theme() changes colors, _get_series_colors() returns updated values.
# The 7-color order: primary, primary_dark, dark, primary_light, secondary×3

def _get_series_colors():
    """Build chart series palette from the current theme colors."""
    return [
        _h.CORE_PURPLE,      # primary
        _h.DARKEST_PURPLE,   # primary dark
        _h.DARK_PURPLE,      # dark
        _h.LIGHT_PURPLE,     # primary light
        _h.MID_GRAY,         # 5 系列目以降は灰色の濃淡（青・水色・ピンクは使わない。ブランドの紫と灰の中に収める）
        _h.LIGHT_GRAY,
        _h.LIGHTEST_PURPLE,
    ]

# Neutral colors — these rarely change across themes
_BLACK      = RGBColor(0x00, 0x00, 0x00)
_WHITE      = RGBColor(0xFF, 0xFF, 0xFF)

def _get_text_body():
    return _h.TEXT_BODY

def _get_mid_gray():
    return _h.MID_GRAY

def _get_light_gray():
    return _h.LIGHT_GRAY

def _get_off_white():
    return _h.OFF_WHITE

# Default font — follows helpers.FONT (set by set_lang())
def _get_default_font():
    return _h.FONT


# ─────────────────────────────────────────────────────────────────────────────
# INTERNAL HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _rgb_hex(color: RGBColor) -> str:
    return f"{color[0]:02X}{color[1]:02X}{color[2]:02X}"


def _apply_series_colors(chart, colors=None):
    """Apply theme palette to all series in the chart."""
    colors = colors or _get_series_colors()
    for i, series in enumerate(chart.series):
        color = colors[i % len(colors)]
        fill = series.format.fill
        fill.solid()
        fill.fore_color.rgb = color


def _style_chart_axes(chart, font_name, font_size_pt=10):
    """Style value and category axes with brand fonts/colors."""
    font_name = font_name or _get_default_font()
    try:
        ax = chart.value_axis
        ax.has_title = False
        ax.tick_labels.font.name = font_name
        ax.tick_labels.font.size = Pt(font_size_pt)
        ax.tick_labels.font.color.rgb = _get_mid_gray()
        ax.tick_marks = XL_TICK_MARK.NONE
        vals = [v for p in chart.plots for s in p.series for v in s.values if v is not None]
        if vals and max(abs(v) for v in vals) >= 1000 and all(float(v).is_integer() for v in vals):
            ax.tick_labels.number_format = "#,##0"      # 桁区切り（50000 → 50,000）。小数のあるグラフは触らない
            ax.tick_labels.number_format_is_linked = False
    except Exception:
        pass

    try:
        ax = chart.category_axis
        ax.tick_labels.font.name = font_name
        ax.tick_labels.font.size = Pt(font_size_pt)
        ax.tick_labels.font.color.rgb = _get_mid_gray()
        ax.tick_marks = XL_TICK_MARK.NONE
    except Exception:
        pass


def _style_chart_base(chart, title, font_name, show_legend=True, legend_pos=None):
    """Set chart title, legend, plot area, and font styling."""
    font_name = font_name or _get_default_font()
    # Chart area background: transparent
    chart.chart_style = 2  # minimal style

    # Title
    if title:
        chart.has_title = True
        chart.chart_title.has_text_frame = True
        tf = chart.chart_title.text_frame
        tf.text = title
        tf.paragraphs[0].font.size = Pt(14)
        tf.paragraphs[0].font.bold = True
        tf.paragraphs[0].font.color.rgb = _BLACK
        tf.paragraphs[0].font.name = font_name
    else:
        chart.has_title = False

    # Legend
    if show_legend:
        chart.has_legend = True
        chart.legend.position = legend_pos or XL_LEGEND_POSITION.BOTTOM
        chart.legend.include_in_layout = False
        chart.legend.font.name = font_name
        chart.legend.font.size = Pt(12)
        chart.legend.font.color.rgb = _get_mid_gray()
    else:
        chart.has_legend = False

    # Plot area — white background via XML
    try:
        plot_area = chart.plots[0]
        # Access underlying plot XML to remove background
    except Exception:
        pass



def _make_category_chart_data(categories, series_data):
    """Build ChartData from categories and series_data list."""
    cd = ChartData()
    cd.categories = categories
    for s in series_data:
        cd.add_series(s["name"], tuple(s["values"]))
    return cd


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────────────────────────────────────

def add_column_chart(slide, title, categories, series_data,
                     x, y, w, h,
                     font_name=None,
                     show_legend=True,
                     show_data_labels=False,
                     colors=None):
    """
    Add a vertical column chart (clustered bars).

    Args:
        slide       : target slide
        title       : chart title string (or None)
        categories  : list of category labels, e.g. ["Q1", "Q2", "Q3"]
        series_data : list of {"name": str, "values": list[float]}
        x, y, w, h  : position and size in inches
        font_name   : font for labels (default Meiryo UI)
        show_legend : show legend (default True)
        show_data_labels: show value labels on bars (default False)
        colors      : list of RGBColor for series (default: current theme palette)

    Returns:
        pptx Chart object
    """
    cd = _make_category_chart_data(categories, series_data)
    chart_frame = slide.shapes.add_chart(
        XL_CHART_TYPE.COLUMN_CLUSTERED,
        Inches(x), Inches(y), Inches(w), Inches(h),
        cd
    )
    chart = chart_frame.chart

    _apply_series_colors(chart, colors)
    _style_chart_base(chart, title, font_name, show_legend)
    _style_chart_axes(chart, font_name)

    if show_data_labels:
        for series in chart.series:
            series.has_data_labels = True
            series.data_labels.font.size = Pt(12)
            series.data_labels.font.name = font_name
            series.data_labels.font.color.rgb = _get_text_body()

    # Remove chart border


    return chart


def add_bar_chart(slide, title, categories, series_data,
                  x, y, w, h,
                  font_name=None,
                  show_legend=True,
                  show_data_labels=False,
                  colors=None):
    """
    Add a horizontal bar chart.

    Same parameters as add_column_chart.

    Returns:
        pptx Chart object
    """
    cd = _make_category_chart_data(categories, series_data)
    chart_frame = slide.shapes.add_chart(
        XL_CHART_TYPE.BAR_CLUSTERED,
        Inches(x), Inches(y), Inches(w), Inches(h),
        cd
    )
    chart = chart_frame.chart

    _apply_series_colors(chart, colors)
    _style_chart_base(chart, title, font_name, show_legend)
    _style_chart_axes(chart, font_name)

    if show_data_labels:
        for series in chart.series:
            series.has_data_labels = True
            series.data_labels.font.size = Pt(12)
            series.data_labels.font.name = font_name
            series.data_labels.font.color.rgb = _get_text_body()


    return chart


def add_line_chart(slide, title, categories, series_data,
                   x, y, w, h,
                   font_name=None,
                   show_legend=True,
                   show_markers=True,
                   colors=None):
    """
    Add a line chart.

    Args:
        show_markers: show data point markers (default True)
    Returns:
        pptx Chart object
    """
    cd = _make_category_chart_data(categories, series_data)
    chart_type = (XL_CHART_TYPE.LINE_MARKERS if show_markers
                  else XL_CHART_TYPE.LINE)
    chart_frame = slide.shapes.add_chart(
        chart_type,
        Inches(x), Inches(y), Inches(w), Inches(h),
        cd
    )
    chart = chart_frame.chart

    # For line charts, color the lines instead of fills
    colors = colors or _get_series_colors()
    for i, series in enumerate(chart.series):
        color = colors[i % len(colors)]
        series.format.line.color.rgb = color
        series.format.line.width = Pt(2.0)
        if show_markers:
            try:
                series.marker.style = 4  # circle marker
                series.marker.size = 6
                series.marker.format.fill.solid()
                series.marker.format.fill.fore_color.rgb = color
            except Exception:
                pass

    _style_chart_base(chart, title, font_name, show_legend)
    _style_chart_axes(chart, font_name)

    return chart


def add_pie_chart(slide, title, labels, values,
                  x, y, w, h,
                  font_name=None,
                  show_legend=True,
                  show_data_labels=True,
                  colors=None):
    """
    Add a pie chart.

    Args:
        labels : list of category labels
        values : list of numeric values (same length as labels)
        show_data_labels: show percentages on slices (default True)
    Returns:
        pptx Chart object
    """
    cd = ChartData()
    cd.categories = labels
    cd.add_series("", tuple(values))

    chart_frame = slide.shapes.add_chart(
        XL_CHART_TYPE.PIE,
        Inches(x), Inches(y), Inches(w), Inches(h),
        cd
    )
    chart = chart_frame.chart

    # Color individual pie slices
    colors = colors or _get_series_colors()
    try:
        series = chart.series[0]
        for i, point in enumerate(series.points):
            color = colors[i % len(colors)]
            point.format.fill.solid()
            point.format.fill.fore_color.rgb = color
    except Exception:
        _apply_series_colors(chart, colors)

    _style_chart_base(chart, title, font_name, show_legend,
                      legend_pos=XL_LEGEND_POSITION.RIGHT)

    if show_data_labels:
        try:
            series = chart.series[0]
            series.has_data_labels = True
            dl = series.data_labels
            dl.font.size = Pt(12)
            dl.font.name = font_name
            dl.font.color.rgb = _WHITE
            dl.position = XL_LABEL_POSITION.INSIDE_END
            dl.show_percentage = True
            dl.show_value = False
            dl.show_category_name = False
        except Exception:
            pass


    return chart


def add_stacked_column_chart(slide, title, categories, series_data,
                              x, y, w, h,
                              font_name=None,
                              show_legend=True,
                              percentage=False,
                              colors=None):
    """
    Add a stacked (or 100% stacked) column chart.

    Args:
        percentage: if True, use 100% stacked variant (default False)
    Returns:
        pptx Chart object
    """
    chart_type = (XL_CHART_TYPE.COLUMN_STACKED_100 if percentage
                  else XL_CHART_TYPE.COLUMN_STACKED)
    cd = _make_category_chart_data(categories, series_data)
    chart_frame = slide.shapes.add_chart(
        chart_type,
        Inches(x), Inches(y), Inches(w), Inches(h),
        cd
    )
    chart = chart_frame.chart

    _apply_series_colors(chart, colors)
    _style_chart_base(chart, title, font_name, show_legend)
    _style_chart_axes(chart, font_name)

    return chart


def add_area_chart(slide, title, categories, series_data,
                   x, y, w, h,
                   font_name=None,
                   show_legend=True,
                   colors=None):
    """
    Add a filled area chart.

    Returns:
        pptx Chart object
    """
    cd = _make_category_chart_data(categories, series_data)
    chart_frame = slide.shapes.add_chart(
        XL_CHART_TYPE.AREA,
        Inches(x), Inches(y), Inches(w), Inches(h),
        cd
    )
    chart = chart_frame.chart

    _apply_series_colors(chart, colors)
    _style_chart_base(chart, title, font_name, show_legend)
    _style_chart_axes(chart, font_name)

    return chart


def _fmt(v):
    return f"{v:,.0f}" if abs(v) >= 100 or float(v).is_integer() else f"{v:,.1f}"


def add_waterfall_chart(slide, title, steps, x, y, w, h, font_name=None, unit=""):
    """
    ウォーターフォール（増減の橋渡し）。見えない「基準」の棒の上に増減の棒を積む。
    steps: [{"label": "2024年度", "value": 100, "total": True}, {"label": "価格改定", "value": 20},
            {"label": "原価増", "value": -8}, {"label": "2025年度", "total": True}]   # total に value が無ければ累計
    合計の棒は濃い紫、増加は紫、減少は灰。値は棒の上に直接書く（増減は +/− 付き）。
    """
    run = 0.0
    cats, base, up, down, tot, labels = [], [], [], [], [], []
    for st in steps:
        cats.append(st.get("label", ""))
        if st.get("total"):
            v = float(st["value"]) if st.get("value") is not None else run
            run = v
            base.append(0); up.append(0); down.append(0); tot.append(v)
            labels.append(_fmt(v) + unit)
        else:
            dv = float(st.get("value", 0))
            lo = run + min(dv, 0)
            base.append(lo); up.append(max(dv, 0)); down.append(max(-dv, 0)); tot.append(0)
            run += dv
            labels.append(("+" if dv >= 0 else "−") + _fmt(abs(dv)) + unit)
    # 値のラベルは、棒の上に積む見えない「ラベル用」の棒に付ける（小さい棒でもラベルが切れず、常に棒の上に並ぶ）
    top = max([b + u + dn + t for b, u, dn, t in zip(base, up, down, tot)] + [1])
    carrier = [top * 0.09] * len(cats)
    cd = ChartData()
    cd.categories = cats
    for name, vals in (("base", base), ("total", tot), ("up", up), ("down", down), ("label", carrier)):
        cd.add_series(name, tuple(vals))
    gf = slide.shapes.add_chart(XL_CHART_TYPE.COLUMN_STACKED, Inches(x), Inches(y), Inches(w), Inches(h), cd)
    chart = gf.chart
    _style_chart_base(chart, title, font_name, show_legend=False)
    _style_chart_axes(chart, font_name)
    plot = chart.plots[0]
    plot.gap_width = 45
    plot.overlap = 100
    cols = {"total": _h.DARKEST_PURPLE, "up": _h.CORE_PURPLE, "down": _h.MID_GRAY}
    for s in chart.series:
        if s.name in ("base", "label"):
            s.format.fill.background()
            s.format.line.fill.background()
        else:
            s.format.fill.solid()
            s.format.fill.fore_color.rgb = cols[s.name]
            s.format.line.fill.background()
    lab_ser = [s for s in chart.series if s.name == "label"][0]
    for i, lab in enumerate(labels):
        dl = lab_ser.points[i].data_label
        dl.has_text_frame = True
        dl.text_frame.text = lab
        dl.position = XL_LABEL_POSITION.INSIDE_BASE
        f = dl.text_frame.paragraphs[0].runs[0].font
        f.size = Pt(12); f.bold = True; f.name = font_name or _get_default_font()
        f.color.rgb = _h.DARKEST_PURPLE if steps[i].get("total") else (_h.TEXT_BODY if down[i] else _h.DARK_PURPLE)
    try:
        chart.value_axis.has_major_gridlines = False
        chart.value_axis.visible = False
    except Exception:
        pass
    return chart


def add_doughnut_chart(slide, title, labels, values, x, y, w, h, font_name=None, colors=None, hole=62):
    """ドーナツ。値の割合をリングに書き、凡例は右。中央の合計は呼び出し側が文字で重ねる。"""
    cd = ChartData()
    cd.categories = labels
    cd.add_series("", tuple(values))
    gf = slide.shapes.add_chart(XL_CHART_TYPE.DOUGHNUT, Inches(x), Inches(y), Inches(w), Inches(h), cd)
    chart = gf.chart
    colors = colors or _get_series_colors()
    for i, point in enumerate(chart.series[0].points):
        point.format.fill.solid()
        point.format.fill.fore_color.rgb = colors[i % len(colors)]
        point.format.line.color.rgb = _WHITE
    _style_chart_base(chart, title, font_name, True, legend_pos=XL_LEGEND_POSITION.RIGHT)
    dn = chart.plots[0]._element
    hs = dn.find(qn_c("holeSize"))
    if hs is None:
        hs = etree.SubElement(dn, qn_c("holeSize"))
    hs.set("val", str(hole))
    s = chart.series[0]
    s.has_data_labels = True
    dl = s.data_labels
    dl.show_percentage = True
    dl.show_value = False
    dl.show_category_name = False
    dl.font.size = Pt(12)
    dl.font.bold = True
    dl.font.name = font_name or _get_default_font()
    dl.font.color.rgb = _WHITE
    return chart


def qn_c(tag):
    return "{http://schemas.openxmlformats.org/drawingml/2006/chart}" + tag


def add_combo_chart(slide, title, categories, bar_series, line_series, x, y, w, h, font_name=None,
                    show_legend=True):
    """縦棒（主軸）＋折れ線（第 2 軸）。棒は紫、折れ線は濃い紫のマーカー付き。
    bar_series / line_series: [{"name": .., "values": [..]}]"""
    cd = _make_category_chart_data(categories, list(bar_series) + list(line_series))
    gf = slide.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(x), Inches(y), Inches(w), Inches(h), cd)
    chart = gf.chart
    _apply_series_colors(chart, [_h.CORE_PURPLE, _h.LIGHT_PURPLE, _h.MID_GRAY])
    _style_chart_base(chart, title, font_name, show_legend)
    _style_chart_axes(chart, font_name)
    plot_area = chart._chartSpace.find(".//" + qn_c("plotArea"))
    bar = plot_area.find(qn_c("barChart"))
    ax_ids = [a.get("val") for a in bar.findall(qn_c("axId"))]
    sers = bar.findall(qn_c("ser"))[len(bar_series):]
    line = etree.SubElement(plot_area, qn_c("lineChart"))
    plot_area.remove(line)
    bar.addnext(line)
    etree.SubElement(line, qn_c("grouping")).set("val", "standard")
    etree.SubElement(line, qn_c("varyColors")).set("val", "0")
    for k, ser in enumerate(sers):
        bar.remove(ser)
        for tag in ("invertIfNegative",):
            e = ser.find(qn_c(tag))
            if e is not None:
                ser.remove(e)
        line.append(ser)
        sp = ser.find(qn_c("spPr"))
        if sp is not None:
            ser.remove(sp)
        col = _rgb_hex(_h.DARKEST_PURPLE if k == 0 else _h.DARK_PURPLE)
        sp = etree.fromstring(
            '<c:spPr xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart" '
            'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
            f'<a:ln w="28575"><a:solidFill><a:srgbClr val="{col}"/></a:solidFill></a:ln></c:spPr>')
        mk = etree.fromstring(
            '<c:marker xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart" '
            'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><c:symbol val="circle"/><c:size val="6"/>'
            f'<c:spPr><a:solidFill><a:srgbClr val="{col}"/></a:solidFill>'
            f'<a:ln><a:solidFill><a:srgbClr val="{col}"/></a:solidFill></a:ln></c:spPr></c:marker>')
        # c:ser の子の順序: idx, order, tx, spPr, marker, ... cat, val, smooth
        tx = ser.find(qn_c("tx"))
        (tx if tx is not None else ser.find(qn_c("order"))).addnext(sp)
        sp.addnext(mk)
        etree.SubElement(ser, qn_c("smooth")).set("val", "0")
    etree.SubElement(line, qn_c("marker")).set("val", "1")
    etree.SubElement(line, qn_c("axId")).set("val", "50001")
    etree.SubElement(line, qn_c("axId")).set("val", "50002")
    # 第 2 軸（カテゴリ軸は隠し、値軸は右）
    val0 = plot_area.find(qn_c("valAx"))
    cat2 = etree.fromstring(
        '<c:catAx xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart"><c:axId val="50001"/>'
        '<c:scaling><c:orientation val="minMax"/></c:scaling><c:delete val="1"/><c:axPos val="b"/>'
        '<c:majorTickMark val="none"/><c:minorTickMark val="none"/><c:tickLblPos val="nextTo"/>'
        '<c:crossAx val="50002"/><c:crosses val="autoZero"/><c:auto val="1"/><c:lblAlgn val="ctr"/>'
        '<c:lblOffset val="100"/><c:noMultiLvlLbl val="0"/></c:catAx>')
    val2 = etree.fromstring(
        '<c:valAx xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart" '
        'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><c:axId val="50002"/>'
        '<c:scaling><c:orientation val="minMax"/></c:scaling><c:delete val="0"/><c:axPos val="r"/>'
        '<c:numFmt formatCode="General" sourceLinked="1"/><c:majorTickMark val="none"/><c:minorTickMark val="none"/>'
        '<c:tickLblPos val="nextTo"/><c:spPr><a:ln><a:noFill/></a:ln></c:spPr>'
        '<c:txPr><a:bodyPr/><a:lstStyle/><a:p><a:pPr><a:defRPr sz="1000"><a:solidFill><a:srgbClr val="818180"/>'
        '</a:solidFill></a:defRPr></a:pPr><a:endParaRPr lang="ja-JP"/></a:p></c:txPr>'
        '<c:crossAx val="50001"/><c:crosses val="max"/><c:crossBetween val="between"/></c:valAx>')
    last_ax = plot_area.findall(qn_c("valAx"))[-1]
    last_ax.addnext(cat2)
    cat2.addnext(val2)
    for g in list(plot_area.iter(qn_c("majorGridlines"))):   # 目盛線は消す（2 軸あると python-pptx の軸指定が効かない）
        g.getparent().remove(g)
    return chart


# ─────────────────────────────────────────────────────────────────────────────
# MATPLOTLIB CHART FUNCTIONS (PNG output)
# ─────────────────────────────────────────────────────────────────────────────
# These return PNG bytes. Embed via:
#   slide.shapes.add_picture(BytesIO(png_bytes), Inches(x), Inches(y), Inches(w), Inches(h))

import io

def _get_mpl_palette(n: int = 8) -> list:
    """Build a matplotlib color palette from the current theme.

    Returns list of hex color strings for chart segments/series.
    """
    series = _get_series_colors()
    hex_colors = [f"#{c[0]:02X}{c[1]:02X}{c[2]:02X}" for c in series]
    # Extend if needed
    while len(hex_colors) < n:
        hex_colors.extend(hex_colors)
    return hex_colors[:n]


def chart_marimekko(
    categories: list,
    widths: list,
    stacks: list,
    stack_labels: list = None,
    title: str = None,
    figsize: tuple = (12, 6),
) -> bytes:
    """Variable-width stacked bar (Marimekko/Mekko) chart.

    Args:
        categories: column labels (len = number of columns)
        widths: column widths (will be normalized to sum=100)
        stacks: list of stacked segment values per column
                e.g. [[30,70],[20,80]] for 2 columns with 2 segments each
        stack_labels: segment legend labels
        title: chart title

    Returns:
        PNG bytes.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches

    total_w = sum(widths)
    norm_widths = [w / total_w * 100 for w in widths]

    n_cols = len(categories)
    n_segs = max(len(s) for s in stacks)
    seg_colors = _get_mpl_palette(n_segs)

    fig, ax = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    x_pos = 0.0
    for ci, (cat, wid, seg_vals) in enumerate(zip(categories, norm_widths, stacks)):
        seg_total = sum(seg_vals)
        bottom = 0.0
        for si, sv in enumerate(seg_vals):
            pct = sv / seg_total * 100 if seg_total > 0 else 0
            color = seg_colors[si % len(seg_colors)]
            ax.bar(
                x_pos + wid / 2, pct, width=wid * 0.96,
                bottom=bottom, color=color, edgecolor="white", linewidth=0.5,
            )
            if pct > 7:
                ax.text(
                    x_pos + wid / 2, bottom + pct / 2,
                    f"{pct:.0f}%", ha="center", va="center",
                    color="white", fontsize=9, fontweight="bold",
                    fontfamily="sans-serif",
                )
            bottom += pct
        ax.text(
            x_pos + wid / 2, 103,
            f"{wid:.0f}%", ha="center", va="bottom",
            color="#333333", fontsize=9, fontfamily="sans-serif",
        )
        ax.text(
            x_pos + wid / 2, -5,
            cat, ha="center", va="top",
            color="#333333", fontsize=10, fontfamily="sans-serif",
        )
        if ci > 0:
            ax.axvline(x=x_pos, color="#FFFFFF", linewidth=2)
        x_pos += wid

    ax.set_xlim(0, 100)
    ax.set_ylim(-12, 112)
    ax.axis("off")

    if title:
        ax.set_title(title, fontsize=13, fontweight="bold", color="#000000",
                     fontfamily="sans-serif", pad=14)

    if stack_labels:
        patches = [mpatches.Patch(color=seg_colors[i % len(seg_colors)], label=stack_labels[i])
                   for i in range(min(n_segs, len(stack_labels)))]
        ax.legend(handles=patches, loc="upper right", frameon=False,
                  fontsize=9, ncol=min(n_segs, 4))

    plt.tight_layout(pad=0.5)
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                facecolor="white", edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def chart_gantt(
    tasks: list,
    start_dates: list,
    end_dates: list,
    milestones: list = None,
    today: str = None,
    groups: list = None,
    title: str = None,
    figsize: tuple = (14, 6),
) -> bytes:
    """Gantt chart for project timelines.

    Args:
        tasks: task name strings
        start_dates: list of datetime or "YYYY-MM-DD" strings
        end_dates: list of datetime or "YYYY-MM-DD" strings
        milestones: list of dicts {"task_idx": int, "date": str, "label": str}
        today: "YYYY-MM-DD" string for vertical "today" line
        groups: optional group label per task
        title: chart title

    Returns:
        PNG bytes.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    import matplotlib.dates as mdates
    from datetime import datetime

    def _parse(d):
        if isinstance(d, str):
            return datetime.strptime(d, "%Y-%m-%d")
        return d

    starts = [_parse(d) for d in start_dates]
    ends   = [_parse(d) for d in end_dates]
    n = len(tasks)

    # Gradient from theme colors
    palette = _get_mpl_palette(n)

    row_h = 0.6
    fig, ax = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#FAFAFA")

    for i, (task, s, e) in enumerate(zip(tasks, starts, ends)):
        y = n - 1 - i
        duration = (e - s).days
        color = palette[i % len(palette)]
        ax.barh(y, duration, left=mdates.date2num(s), height=row_h,
                color=color, alpha=0.85, edgecolor="white", linewidth=0.5)
        ax.text(mdates.date2num(s) + duration / 2, y,
                task, ha="center", va="center",
                color="white", fontsize=8.5, fontweight="bold",
                fontfamily="sans-serif")

    if milestones:
        for ms in milestones:
            ti = ms["task_idx"]
            md = _parse(ms["date"])
            y = n - 1 - ti
            ax.plot(mdates.date2num(md), y, marker="D",
                    color="#FFEA00", markersize=8, zorder=5)
            ax.text(mdates.date2num(md), y + 0.38,
                    ms.get("label", ""), ha="center", va="bottom",
                    color="#333333", fontsize=7.5, fontfamily="sans-serif")

    if today:
        td = _parse(today)
        ax.axvline(mdates.date2num(td), color="#FF0000", linewidth=1.2,
                   linestyle="--", alpha=0.7, label=f"Today ({today})")
        ax.legend(loc="upper right", frameon=False, fontsize=8)

    ax.set_yticks(range(n))
    ax.set_yticklabels(list(reversed(tasks)), fontsize=9, fontfamily="sans-serif")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b '%y"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right", fontsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.grid(axis="x", color="#E0E0E0", linewidth=0.5)

    if title:
        ax.set_title(title, fontsize=13, fontweight="bold", color="#000000",
                     fontfamily="sans-serif", pad=10)

    plt.tight_layout(pad=0.8)
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                facecolor="white", edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def chart_stacked_bar_100(
    categories: list,
    series_labels: list,
    values: list,
    title: str = None,
    figsize: tuple = (10, 6),
) -> bytes:
    """100% stacked horizontal bar chart.

    Args:
        categories: row labels (one per bar)
        series_labels: segment labels (shared across all bars)
        values: 2D list [row][segment] — raw values; rows are normalized to 100%
        title: chart title

    Returns:
        PNG bytes.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches

    n_rows = len(categories)
    n_segs = len(series_labels)
    seg_colors = _get_mpl_palette(n_segs)

    fig, ax = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    for ri, (cat, row_vals) in enumerate(zip(categories, values)):
        total = sum(row_vals) or 1
        left = 0.0
        for si, rv in enumerate(row_vals):
            pct = rv / total * 100
            color = seg_colors[si % len(seg_colors)]
            ax.barh(ri, pct, left=left, height=0.6, color=color,
                    edgecolor="white", linewidth=0.5)
            if pct > 5:
                ax.text(left + pct / 2, ri, f"{pct:.0f}%",
                        ha="center", va="center", color="white",
                        fontsize=8.5, fontweight="bold", fontfamily="sans-serif")
            left += pct

    ax.set_yticks(range(n_rows))
    ax.set_yticklabels(categories, fontsize=10, fontfamily="sans-serif")
    ax.set_xlim(0, 100)
    ax.set_xlabel("Share (%)", fontsize=9, fontfamily="sans-serif")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="x", color="#E0E0E0", linewidth=0.5, linestyle="--")

    if title:
        ax.set_title(title, fontsize=13, fontweight="bold", color="#000000",
                     fontfamily="sans-serif", pad=10)

    patches = [mpatches.Patch(color=seg_colors[i % len(seg_colors)], label=series_labels[i])
               for i in range(n_segs)]
    ax.legend(handles=patches, loc="lower right", frameon=False, fontsize=9,
              ncol=min(n_segs, 4))

    plt.tight_layout(pad=0.6)
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                facecolor="white", edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return buf.read()
