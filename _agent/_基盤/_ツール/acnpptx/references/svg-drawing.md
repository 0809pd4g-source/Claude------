# svg-drawing.md — Claude が作図して、編集できる図形として入れる

既存部品・素材で表せない概念図や線画アイコンは、Claude が SVG を書き、`svg_to_shapes.add_svg()` で
**PowerPoint のネイティブ図形（矩形・楕円・フリーフォーム・コネクタ・テキストボックスのグループ）**に変換して入れる。画像としては貼らない。

## 使える要素（これ以外はエラー）

| SVG | 変換後 |
|---|---|
| `rect`（x, y, width, height） | 矩形。`rx` は無視（角丸禁止） |
| `circle` / `ellipse` | 楕円 |
| `line` | 直線コネクタ |
| `polyline` | 開いたフリーフォーム |
| `polygon` / `path`（M L H V C S Q T A Z、相対も可） | フリーフォーム（custGeom） |
| `text`（x, y, font-size, font-weight, text-anchor, fill） | テキストボックス（テーマのフォント） |
| `g`（transform: translate / scale / rotate / matrix） | 入れ子は展開して 1 つのグループに |

使えない: gradient（`url(...)`）, filter（影・ぼかし）, image, use, clipPath, mask, pattern, style シート。

## 描き方の規約

- `viewBox` を必ず書く。配置枠（インチ）に等倍縮尺で中央揃えされる
- **色はテーマ色だけ**: #460073（濃）/ #7500C0 / #A100FF（主）/ #C2A3FF / #E6DCFF（淡）/ #000000 / #333333 / #818180 / #CFCFCF / #F1F1EF / #FFFFFF。違う色は近いテーマ色に丸められる
- **線画アイコン**: `viewBox="0 0 24 24"`, `fill="none"`, `stroke-width="1.5"`, 主線 #7500C0。要素は 3〜8 個まで
- **概念図**: 箱は rect、つながりは line（矢印が必要なら小さい polygon の三角）、ラベルは text（font-size は viewBox 幅 400 なら 16〜22）
- 文字はなるべく図の外（部品のテキスト）に出す。図の中の text は短いラベル（10 字以内）だけ
- 意味のない装飾の円・重なりは描かない（CB-15）

## 使い方

```python
from svg_to_shapes import add_svg, lint_svg
svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 240">
  <rect x="10" y="80" width="110" height="80" fill="#E6DCFF"/>
  <rect x="145" y="80" width="110" height="80" fill="#C2A3FF"/>
  <rect x="280" y="80" width="110" height="80" fill="#A100FF"/>
  <line x1="120" y1="120" x2="145" y2="120" stroke="#460073" stroke-width="3"/>
  <line x1="255" y1="120" x2="280" y2="120" stroke="#460073" stroke-width="3"/>
  <text x="65" y="126" text-anchor="middle" font-size="18" fill="#460073">計画</text>
  <text x="200" y="126" text-anchor="middle" font-size="18" fill="#460073">実行</text>
  <text x="335" y="126" text-anchor="middle" font-size="18" fill="#FFFFFF">評価</text>
</svg>"""
assert not lint_svg(svg)                       # 使えない要素がないか
grp = add_svg(slide, svg, x=ML, y=CY, w=CW, h=4.5, name="PDCA 概念図")
print(grp.svg_warnings)
```

outline からは `{"svg": "<svg …>"}`（M-ILLUST の `svg`、カードの `icon` など）で指定できる。

## 確認

描画後のサムネイルで、visual_evaluator が「意味が合っているか」「ブランドから浮いていないか」を評価する（基準 8・9）。
編集できることの確認: PowerPoint でグループを選び「グループ解除」すると、個々の図形の色・形を直せる。

## 参考: PowerPoint の「図形に変換」（COM）との比較

| | 自作変換（既定） | COM（SVG 貼り付け → 図形に変換） |
|---|---|---|
| 成功率（サンプル 10 点 × 2 回） | 10/10 | `Ungroup` 直呼び 0/10、画面選択＋`ExecuteMso("SVGEdit")` 10/10 |
| 速度 | 約 0.01 秒/点 | 0.3〜1.7 秒/点 |
| 前提 | python-pptx のみ（PowerPoint 不要） | PowerPoint のウィンドウ表示と選択操作が必要 |
| 結果 | 1 グループ、線はコネクタ、色はテーマに丸め | 図形がばらばら、色は SVG のまま |
