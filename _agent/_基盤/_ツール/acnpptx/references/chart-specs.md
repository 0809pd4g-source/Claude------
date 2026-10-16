# Chart Specifications — python-pptx Native Charts

All charts use Accenture brand colors. No SVG / No Node.js required.
Import from `scripts/charts.py`.

## Quick Reference

```python
from charts import (
    add_column_chart,        # vertical bars — most common
    add_bar_chart,           # horizontal bars
    add_line_chart,          # trend lines
    add_pie_chart,           # composition
    add_stacked_column_chart,# part-to-whole
    add_area_chart,          # filled area
)
```

## Series Data Format

```python
series_data = [
    {"name": "2025年実績", "values": [100, 120, 130, 150]},
    {"name": "2026年予測", "values": [110, 135, 145, 170]},
]
```

## Color Palette (auto-applied in order)

| Priority | Color | Hex | Typical use |
|----------|-------|-----|-------------|
| 1st series | CORE_PURPLE | #A100FF | Primary metric |
| 2nd series | DARKEST_PURPLE | #460073 | Comparison |
| 3rd series | DARK_PURPLE | #7500C0 | Third dimension |
| 4th series | LIGHT_PURPLE | #C2A3FF | Baseline / target |
| 5th series | BLUE | #224BFF | External reference |
| 6th series | AQUA | #05F2DB | Supplemental |
| 7th series | PINK | #FF50A0 | Alert / exception |

---

## グラフの配置

### Full-width chart (recommended)
```python
chart = add_column_chart(
    slide, title="",
    categories=cats, series_data=series,
    x=ML, y=2.30, w=CW, h=4.20,
    font_name=FONT,
)
```

### Left text + right chart
```python
# Left description
tb = slide.shapes.add_textbox(Inches(ML), Inches(2.35), Inches(3.50), Inches(4.00))
# Chart on right
chart = add_bar_chart(
    slide, title=None,
    categories=cats, series_data=series,
    x=4.20, y=2.30, w=8.60, h=4.20,
    font_name=FONT, show_legend=False,
)
```

### Chart + annotation below
```python
chart = add_line_chart(
    slide, title="月次トレンド",
    categories=cats, series_data=series,
    x=ML, y=2.20, w=CW, h=3.60,
    font_name=FONT, show_markers=True,
)
# Source note below chart
tb = slide.shapes.add_textbox(Inches(ML), Inches(5.90), Inches(CW), Inches(0.40))
p = tb.text_frame.paragraphs[0]
p.text = "出所: 社内データ 2026年2月末時点"
p.font.size = Pt(11); p.font.color.rgb = MID_GRAY; p.font.name = FONT
```

---

## Chart Type Guide

### Column Chart (縦棒グラフ)
Best for: category comparisons, quarterly/yearly data

```python
add_column_chart(
    slide, title="四半期別売上",
    categories=["Q1", "Q2", "Q3", "Q4"],
    series_data=[{"name": "売上", "values": [100, 120, 135, 150]}],
    x=ML, y=2.30, w=CW, h=4.20,
    show_data_labels=True,   # show values on bars
    font_name=FONT,
)
```

### Bar Chart (横棒グラフ)
Best for: rankings, comparisons with long category names

```python
add_bar_chart(
    slide, title="部門別コスト削減率",
    categories=["製造部門", "物流部門", "営業部門", "管理部門"],
    series_data=[{"name": "削減率(%)", "values": [15, 12, 8, 5]}],
    x=ML, y=2.30, w=CW, h=4.20,
    show_data_labels=True,
    font_name=FONT,
)
```

### Line Chart (折れ線グラフ)
Best for: trends over time, continuous metrics

```python
add_line_chart(
    slide, title="月次稼働率推移",
    categories=["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
    series_data=[
        {"name": "稼働率", "values": [88, 91, 87, 93, 95, 97]},
        {"name": "目標", "values": [90, 90, 90, 90, 90, 90]},
    ],
    x=ML, y=2.30, w=CW, h=4.20,
    show_markers=True,
    font_name=FONT,
)
```

### Pie Chart (円グラフ)
Best for: composition/breakdown (max 5–6 slices, sum = 100%)

**⚠ 必ず `w=CW` を使うこと。** 狭い幅（6〜7"）にすると右側に大きな空白が残る。凡例はチャートエリア内に自動配置される。

```python
add_pie_chart(
    slide, title="リソース配分",
    labels=["開発", "テスト", "設計", "管理"],
    values=[45, 25, 20, 10],
    x=ML, y=2.20, w=CW, h=4.40,   # w=CW 必須 — 狭くしない
    show_legend=True,
    show_data_labels=True,
    font_name=FONT,
)
```

### Stacked Column (積み上げ棒グラフ)
Best for: part-to-whole over time/categories

```python
add_stacked_column_chart(
    slide, title="コスト内訳",
    categories=["2023", "2024", "2025", "2026"],
    series_data=[
        {"name": "人件費", "values": [500, 520, 540, 560]},
        {"name": "設備費", "values": [200, 210, 215, 220]},
        {"name": "その他", "values": [100, 95, 90, 85]},
    ],
    x=ML, y=2.30, w=CW, h=4.20,
    percentage=False,  # True for 100% stacked
    font_name=FONT,
)
```

### Radar Chart / Spider Chart (レーダーチャート)
Best for: multi-axis evaluation, skill assessment, competitive comparison (3–8 axes)
Corresponds to Multilayer Chart.pptx slide 3 "Radar Chart 2"

```python
from pptx.chart.data import ChartData
from pptx.enum.chart import XL_CHART_TYPE

chart_data = ChartData()
chart_data.categories = ["品質", "コスト", "スピード", "イノベーション", "顧客満足"]
chart_data.add_series("自社",   (80, 70, 60, 90, 75))
chart_data.add_series("競合A",  (60, 80, 75, 55, 65))

chart_frame = slide.shapes.add_chart(
    XL_CHART_TYPE.RADAR_FILLED,   # RADAR / RADAR_FILLED / RADAR_MARKERS
    Inches(ML), Inches(2.30), Inches(CW), Inches(4.20),
    chart_data,
)
chart = chart_frame.chart
chart.has_legend = True
chart.has_title = False  # タイトルはスライドのメッセージラインで表現する

# 系列の色設定
from pptx.dml.color import RGBColor
from pptx.oxml.ns import qn as _qn
SERIES_COLORS = [CORE_PURPLE, DARK_PURPLE, DARKEST_PURPLE, LIGHT_PURPLE]
for i, series in enumerate(chart.series):
    color = SERIES_COLORS[i % len(SERIES_COLORS)]
    series.format.fill.solid()
    series.format.fill.fore_color.rgb = color
    series.format.line.color.rgb = color
    # 塗りつぶし透明度（RADAR_FILLED で使用）
    sp_pr = series.format._element
    solid_fill = sp_pr.find('.//' + _qn('a:solidFill'))
    if solid_fill is not None:
        alpha = solid_fill.find(_qn('a:alpha'))
        if alpha is None:
            from lxml import etree
            alpha = etree.SubElement(solid_fill, _qn('a:alpha'))
        alpha.set('val', '40000')  # 40% 透明度（100000 = 100%）

# フォント設定
chart.plots[0].series[0].data_labels.font.size = Pt(10)
if chart.has_legend:
    chart.legend.font.size = Pt(11)
    chart.legend.font.name = FONT
```

**Chart type variants:**
| Type | OOXML constant | 用途 |
|------|----------------|------|
| `RADAR` | `XL_CHART_TYPE.RADAR` | 線のみ（塗りなし） |
| `RADAR_FILLED` | `XL_CHART_TYPE.RADAR_FILLED` | 透明塗りつぶし（複数系列比較に最適） |
| `RADAR_MARKERS` | `XL_CHART_TYPE.RADAR_MARKERS` | マーカー付き線 |

---

### Doughnut Chart (ドーナツグラフ)
Best for: 1 系列の構成比（pie の変形）。中央に大きな数値を重ねて視覚的インパクトを出す場合に有効
Corresponds to Multilayer Chart.pptx slide 2 "Doughnut Chart"

```python
from pptx.chart.data import ChartData
from pptx.enum.chart import XL_CHART_TYPE

chart_data = ChartData()
chart_data.categories = ["Label A", "Label B", "Label C", "その他"]
chart_data.add_series("構成", (45, 28, 17, 10))

chart_frame = slide.shapes.add_chart(
    XL_CHART_TYPE.DOUGHNUT,
    Inches(ML), Inches(2.20), Inches(6.50), Inches(4.40),
    chart_data,
)
chart = chart_frame.chart
chart.has_legend = True
chart.has_title = False

# スライス色を個別設定（系列の各点を変更）
SLICE_COLORS = [DARKEST_PURPLE, CORE_PURPLE, LIGHT_PURPLE, LIGHTEST_PURPLE]
series = chart.series[0]
for i, point in enumerate(series.points):
    point.format.fill.solid()
    point.format.fill.fore_color.rgb = SLICE_COLORS[i % len(SLICE_COLORS)]

# ドーナツの穴サイズ調整（デフォルト 75%）
# XML で直接設定: chart.plots[0]._element.get_or_add("c:holeSize").set("val", "60")

# 中央に大きな数値を重ねる場合（オプション）
# ドーナツの中心座標を計算してテキストボックスを重ねる
center_x = ML + (6.50 / 2) - 0.80
center_y = 2.20 + (4.40 / 2) - 0.50
tb_center = slide.shapes.add_textbox(
    Inches(center_x), Inches(center_y), Inches(1.60), Inches(1.00))
tf = tb_center.text_frame
p = tf.paragraphs[0]; p.text = "45%"
p.font.size = Pt(36); p.font.bold = True
p.font.color.rgb = DARKEST_PURPLE; p.font.name = FONT; p.alignment = PP_ALIGN.CENTER
p2 = tf.add_paragraph(); p2.text = "Label A"
p2.font.size = Pt(12); p2.font.color.rgb = MID_GRAY; p2.font.name = FONT
p2.alignment = PP_ALIGN.CENTER
```

---

### Combination Chart — Column + Line (複合チャート)
Best for: 量（棒）と比率/トレンド（折れ線）を同時に表示。第2軸使用
Corresponds to Multilayer Chart.pptx slide 60 "Combination Column-line Chart 1"

```python
from pptx.chart.data import ChartData
from pptx.enum.chart import XL_CHART_TYPE
from lxml import etree
from pptx.oxml.ns import qn as _qn, nsmap as _nsmap

# 複合チャートは python-pptx の高レベル API で直接作れないため
# 棒グラフで生成後、第2系列の type を折れ線に変更する
chart_data = ChartData()
chart_data.categories = ["Q1", "Q2", "Q3", "Q4", "Q5", "Q6"]
chart_data.add_series("売上（百万円）", (204, 274, 900, 204, 400, 550))   # 棒
chart_data.add_series("成長率（%）",    (5,   3,   6,   9,   10,  3))     # 折れ線（第2軸）

chart_frame = slide.shapes.add_chart(
    XL_CHART_TYPE.COLUMN_CLUSTERED,
    Inches(ML), Inches(2.30), Inches(CW), Inches(4.20),
    chart_data,
)
chart = chart_frame.chart

# 棒グラフの色（第1系列）
chart.series[0].format.fill.solid()
chart.series[0].format.fill.fore_color.rgb = DARKEST_PURPLE
chart.series[0].format.line.fill.background()

# 第2系列を折れ線チャートに変換（XML 操作）
# plotArea 内の第2系列の barChart → lineChart に変更
plot_area = chart._element.find('.//' + _qn('c:plotArea'))
bar_charts = plot_area.findall(_qn('c:barChart'))
if bar_charts:
    bar_chart_el = bar_charts[0]
    ser_els = bar_chart_el.findall(_qn('c:ser'))
    if len(ser_els) >= 2:
        # 第2系列を barChart から取り出して lineChart を作成
        ser2 = ser_els[1]
        bar_chart_el.remove(ser2)

        line_chart_xml = f'''<c:lineChart xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart">
  <c:barDir val="col"/>
  <c:grouping val="standard"/>
  <c:varyColors val="0"/>
  {etree.tostring(ser2, encoding="unicode")}
  <c:axId val="200"/>
  <c:axId val="201"/>
</c:lineChart>'''
        line_chart_el = etree.fromstring(line_chart_xml)
        plot_area.append(line_chart_el)

# 第2系列の色（折れ線）
# bar_chart 内の ser[1] が残っている場合は直接設定
# ここでは簡易的に charts.py の add_line_chart を別途重ねる方法を推奨

# ── 実用的な代替: 2 つのチャートを重ねる方法（推奨）──────────────────
# 棒グラフ（第1軸）
from charts import add_column_chart, add_line_chart

col_chart = add_column_chart(
    slide, title="",
    categories=["Q1", "Q2", "Q3", "Q4", "Q5", "Q6"],
    series_data=[{"name": "売上（百万円）", "values": [204, 274, 900, 204, 400, 550]}],
    x=ML, y=2.30, w=CW, h=4.20, font_name=FONT, show_data_labels=False,
)
col_chart.series[0].format.fill.solid()
col_chart.series[0].format.fill.fore_color.rgb = DARKEST_PURPLE

# 折れ線グラフを同じ位置に重ねる（透明背景にして軸のみ第2軸として機能）
# ※ この方法はあくまで視覚的な重ね合わせであり、軸スケールの自動整合はされない
# → 実務では max_scale を揃えてから配置すること
line_chart = add_line_chart(
    slide, title="",
    categories=["Q1", "Q2", "Q3", "Q4", "Q5", "Q6"],
    series_data=[{"name": "成長率（%）", "values": [5, 3, 6, 9, 10, 3]}],
    x=ML, y=2.30, w=CW, h=4.20, font_name=FONT, show_markers=True,
)
# 折れ線グラフのプロット領域を透明にする（背景の棒グラフを透けて見せる）
line_chart_frame = slide.shapes[-1]  # 最後に追加したシェイプ
from pptx.util import Emu
line_chart_frame.chart.plot_area.format.fill.background()
```

**Tips:**
- python-pptx は複合チャートを直接生成する API を持たないため、重ね合わせ方式が最も確実
- 軸スケールを合わせる場合: `chart.value_axis.maximum_scale = N` で設定
- データラベルが重なる場合は `series.has_data_labels = False` で一方を非表示に

---

## Scatter Chart (散布図: XY_SCATTER)
**Use**: 2変数の相関・分布分析（縦軸: 価値/インパクト、横軸: 難易度/コスト）。スライド 4 タイプ参照。

```python
from pptx.chart.data import XyChartData
from pptx.enum.chart import XL_CHART_TYPE

chart_data = XyChartData()
series1 = chart_data.add_series("サービスA")
for x, y in [(1.5, 60), (3.0, 75), (4.5, 85), (6.0, 70), (8.0, 50)]:
    series1.add_data_point(x, y)
series2 = chart_data.add_series("サービスB")
for x, y in [(2.0, 40), (4.0, 55), (7.0, 65)]:
    series2.add_data_point(x, y)

chart_frame = slide.shapes.add_chart(
    XL_CHART_TYPE.XY_SCATTER,
    Inches(ML), Inches(2.30), Inches(CW), Inches(4.20),
    chart_data)
chart = chart_frame.chart
chart.has_legend = True
chart.value_axis.axis_title.text_frame.text   = "Y軸ラベル"
chart.category_axis.axis_title.text_frame.text = "X軸ラベル"

# Marker colors
chart.series[0].marker.format.fill.solid()
chart.series[0].marker.format.fill.fore_color.rgb = DARKEST_PURPLE
chart.series[0].marker.size = 10
chart.series[1].marker.format.fill.solid()
chart.series[1].marker.format.fill.fore_color.rgb = CORE_PURPLE
chart.series[1].marker.size = 10
```

**Tips:**
- `XY_SCATTER`: マーカーのみ（線なし）。線あり: `XY_SCATTER_LINES`、スムーズ: `XY_SCATTER_SMOOTH`
- マーカー形状: `from pptx.enum.chart import XL_MARKER_STYLE` → `series.marker.style = XL_MARKER_STYLE.CIRCLE`
- 軸ラベルは省略するとタイトルなし。`axis_title.has_title = True` が前提

---

## Bubble Chart (バブルチャート: BUBBLE)
**Use**: 3変数の可視化（X軸・Y軸・バブルサイズ）。3次元ポートフォリオ分析に最適。スライド 5 タイプ参照。

```python
from pptx.chart.data import BubbleChartData
from pptx.enum.chart import XL_CHART_TYPE

chart_data = BubbleChartData()
series1 = chart_data.add_series("第1グループ")
for x, y, size in [(2, 4, 0.5), (5, 7, 1.0), (8, 3, 0.7)]:
    series1.add_data_point(x, y, size)
series2 = chart_data.add_series("第2グループ")
for x, y, size in [(3, 2, 0.3), (6, 5, 0.8), (9, 6, 0.4)]:
    series2.add_data_point(x, y, size)

chart_frame = slide.shapes.add_chart(
    XL_CHART_TYPE.BUBBLE,
    Inches(ML), Inches(2.30), Inches(CW), Inches(4.20),
    chart_data)
chart = chart_frame.chart
chart.series[0].format.fill.solid()
chart.series[0].format.fill.fore_color.rgb = DARKEST_PURPLE
chart.series[1].format.fill.solid()
chart.series[1].format.fill.fore_color.rgb = CORE_PURPLE
```

**Tips:**
- `size` の単位は python-pptx 内部スケール（0.1〜2.0 程度が視認しやすい）
- 半透明バブル: `series.format.fill.fore_color._xClrChange` に alpha XML を追加（Radar Chart 参照）
- 3D バブル: `XL_CHART_TYPE.BUBBLE_THREE_D_EFFECT`（見た目が重いので推奨しない）

---

## Range / Floating Bar Chart (範囲バーチャート)
**Use**: 工程の開始〜終了範囲（Gantt 的）、データのレンジ（最小〜最大）の可視化。スライド 57 タイプ参照。

python-pptx に直接の Range Bar API はないため、**積み上げ棒グラフの透明オフセット方式**を使用。

```python
from pptx.chart.data import ChartData
from pptx.enum.chart import XL_CHART_TYPE

categories = ["プロセスA", "プロセスB", "プロセスC", "プロセスD"]
# starts: 透明（不可視）オフセット / widths: 可視バー幅 (end - start)
starts = [2, 4, 1, 5]
widths = [3, 2, 4, 2]

chart_data = ChartData()
chart_data.categories = categories
chart_data.add_series("オフセット（非表示）", starts)
chart_data.add_series("範囲",                widths)

chart_frame = slide.shapes.add_chart(
    XL_CHART_TYPE.BAR_STACKED,
    Inches(ML), Inches(2.30), Inches(CW), Inches(4.20),
    chart_data)
chart = chart_frame.chart

# オフセット系列を透明にする
chart.series[0].format.fill.background()
chart.series[0].format.line.fill.background()
chart.series[0].has_data_labels = False

# 可視系列の色とラベル
chart.series[1].format.fill.solid()
chart.series[1].format.fill.fore_color.rgb = DARKEST_PURPLE
chart.series[1].has_data_labels = True
chart.series[1].data_labels.font.size = Pt(11)
chart.series[1].data_labels.font.name = FONT
chart.series[1].data_labels.font.color.rgb = WHITE
```

**Tips:**
- 縦方向（Column）にしたい場合: `XL_CHART_TYPE.COLUMN_STACKED` に変更
- ギャップ調整: `chart.plots[0].gap_width = 100`（値が小さいほどバーが太い）
- X軸の範囲固定: `chart.category_axis.minimum_scale = 0` と `maximum_scale = N` でスケール固定

---

## Post-Chart Styling (advanced)

After calling the helper, you can fine-tune the chart object:

```python
# Access chart object
chart = add_column_chart(...)  # returns pptx Chart object

# Override series color
from pptx.dml.color import RGBColor
series = chart.series[0]
series.format.fill.solid()
series.format.fill.fore_color.rgb = RGBColor(0x46, 0x00, 0x73)

# Add data labels to specific series
series.has_data_labels = True
series.data_labels.font.size = Pt(10)
series.data_labels.font.name = FONT

# Adjust axis range
chart.value_axis.maximum_scale = 200
chart.value_axis.minimum_scale = 0

# Legend position
from pptx.enum.chart import XL_LEGEND_POSITION
chart.legend.position = XL_LEGEND_POSITION.RIGHT
```

---

## Common Mistakes

| Issue | Fix |
|-------|-----|
| Chart has wrong colors | `_apply_series_colors(chart, [custom_list])` |
| Legend overlaps chart | `chart.legend.include_in_layout = False` |
| Axis labels too small | `chart.value_axis.tick_labels.font.size = Pt(10)` |
| Pie slices wrong color | Color each `series.points[i]` individually |
| Chart has white border | `chart_frame.line.fill.background()` |
| Values not showing | `series.has_data_labels = True` |
