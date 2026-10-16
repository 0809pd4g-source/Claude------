# API Reference — pptx スキル

## helpers.py

`from helpers import *` で全てインポート可能。

### Slide セットアップ

```python
clear_placeholders(slide)
# Layout 2 スライドの未使用 idx=10 body placeholder を削除。
# add_slide() 直後に呼ぶ。idx=0 (title) と idx=11 (breadcrumb) は保持。
```

### 必須ヘッダー関数（この順序で呼ぶこと）

```python
add_breadcrumb(slide, "Section > Topic")
# idx=11 placeholder (y=0.08") に書き込む。12pt MID_GRAY。
# ⚠ 空文字列禁止 — 未入力だとヒントテキストが表示される。

add_title(slide, "タイトル", size_pt=28)
# idx=0 placeholder (y=0.42") に書き込む。28pt bold BLACK。
# ⚠ textbox でタイトルを直接配置しないこと — 二重表示になる。

add_message_line(slide, "スライドの主張を常体で。")
# layout_notes にメッセージライン placeholder idx が未定義の場合に使う。
# y=MSG_Y=0.95", 18pt bold DARK_PURPLE のテキストボックスを追加。
# layout_notes に idx が定義されている場合はその placeholder に直接書き込むこと。

set_footer(slide)
# 全コンテンツスライドに必須。
```

### レイアウト定数

```python
# デフォルト値 — layout_notes.content.content_area_y があればそちらを使う
CY    = 1.50   # content area Y start
BY    = 6.85   # content area bottom
AH    = 5.35   # available height (BY - CY)
ML    = 0.42   # margin left
CW    = 12.50  # content width
MSG_Y = 0.95   # message line Y（layout_notes に placeholder がある場合はその座標が優先）
MSG_H = 0.45   # message line height
```

### テーマ・言語

```python
_h.set_lang("ja")          # "ja" or "en" — set_lang を load_theme より先に呼ぶこと
_h.load_theme("Accenture") # テーマ名を入れる（【acnpptx設定】テーマ= の値）
# from helpers import * の後に TEMPLATE_PATH, FONT, 全カラー定数が使える
```

### モダンビジュアルヘルパー

```python
accent_color(index)       # RGBColor: dark → primary → light をサイクル
accent_color_hex(index)   # "#RRGGBB" 文字列版（SVG / 文字列フォーマット用）

make_dark_divider(slide, "Section Title", "Optional subtitle")
# DARKEST_PURPLE bg + 白文字のセクション区切り。1デッキ最大2枚。

add_title_accent_line(slide)
# コンテンツエリア直上 (y = CY - 0.03) に CORE_PURPLE の細線を追加。

make_closing_slide(prs, "Thank You")
# カバーレイアウトを使ったクロージングスライド。マスターが bg/logo/GT を自動提供。
# 白背景テーマでは text_color=BLACK を渡すこと。

strip_sections(prs)
# PowerPoint セクションヘッダーを削除。prs.save() の直前に必ず呼ぶ。
```

---

## charts.py

詳細は [chart-specs.md](chart-specs.md) 参照。

```python
from charts import add_column_chart, add_bar_chart, add_line_chart, add_pie_chart

add_column_chart(slide, title, categories, series_data, x, y, w, h, font_name,
                 show_data_labels=True, ...)
add_bar_chart(...)
add_line_chart(...)
add_pie_chart(slide, title, labels, values, x, y, w, h, font_name, ...)
add_stacked_column_chart(...)
add_area_chart(...)
# テーマパレットは helpers.py により自動適用される。
```

---

