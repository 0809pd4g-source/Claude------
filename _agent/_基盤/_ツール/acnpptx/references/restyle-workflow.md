# Restyle Workflow

Transform an existing presentation into the pptx design system while preserving its content.
This is different from **Retheme** (which only changes colors and slide master while keeping layout structure intact).

## When to Use

The user has an existing `.pptx` and wants it **restyled** — better visuals, consistent layout patterns, proper typography, restructured slides. The original deck may be plain, inconsistent, or from a different template.

**Restyle vs Retheme:**

| | Restyle | Retheme |
|---|---------|---------|
| **What changes** | Layout, structure, visual patterns, content arrangement | Colors, fonts, slide master only |
| **Content** | Preserved but may be split/merged/reorganized | Preserved as-is |
| **Slide count** | May change (split dense, merge sparse) | Same |
| **Process** | Extract → restructure → regenerate from scratch | Run `retheme.py` script |
| **When to use** | Deck looks outdated/inconsistent, needs redesign | Deck structure is fine, just needs brand colors |

## Steps

### 1. Extract Content

```bash
$PY -m markitdown '<existing.pptx>'   # $PY は SKILL.md の Setup 参照。パスは単一引用符で囲み、記号を含む名前は使わない
```

Read the markdown output to understand slide boundaries, headings, bullet points, data tables, and any embedded chart descriptions.

### 2. Analyze and Plan

For each original slide, note:
- **Content type**: title/cover, agenda, data table, bullet list, process flow, chart, quote, key message
- **Content volume**: how much text, how many items
- **Data**: any numbers, statistics, or data series that could become charts

### 3. Restructure (if beneficial)

Restructuring is allowed and encouraged:
- **Split** dense slides with 8+ bullet points into 2-3 focused slides
- **Merge** sparse slides that have only a heading and 1-2 bullets
- **Promote** data buried in bullets to chart slides (M-CHART)
- **Add** an agenda slide (type: agenda) if the original lacks one and has 3+ sections
- **Convert** text-heavy process descriptions into chevron flows (M-CHEVRON) or a timeline (M-TIMELINE)

The goal is readability and visual impact, not 1:1 slide count preservation.

### 4. Map to the design grammar

元のスライドの内容を、outline.json（v2）の設計票に起こす（[grammar-guide](grammar-guide.md) の 3a〜3c）。

| 元の内容 | relation | 使う表現の例 |
|---|---|---|
| 箇条書き 3〜4 項目（本当に並列） | parallel | M-ROWHEAD / M-HEADCOL / 骨格（`skeleton.py --relation parallel`） |
| 箇条書き 5 項目以上 | — | スライドを分けるか、表（M-TABLE）にまとめる |
| データの表 | contrast / parallel | M-TABLE（`"^"` で区分のセルを結合） |
| 2 案の比較 | contrast | 同じ形の左右（M-NGOK、K-009 など） |
| 手順・工程 | sequence / flow | M-CHEVRON / M-TIMELINE / M-PIPELINE |
| 数値・KPI | cause | M-CHART（値ラベル）／M-KPI-STACK（主役は 1 つ） |
| 現状 → あるべき姿 | contrast | 骨格（K-065 など）、R-WEDGE |
| 階層・構成 | hierarchy | M-LAYER / M-PYRAMID / M-ARCH / M-TREE |
| 位置づけ・優先度 | contrast | M-2AXIS |
| 体制・人物 | hierarchy | M-PROFILE / M-ACTORS / 骨格（intent=org） |

### 5. Generate New Deck

Create a generation script following the standard Create workflow (Steps 0-10 from SKILL.md). Use:
- The extracted content as input text
- The mapped patterns for layout
- Native shapes and charts for data visualization
- Icons where concepts have clear visual matches

### 6. Preserve Data Integrity

Critical: all numbers, data, quotes, and attributions from the original must carry over exactly. Do not paraphrase statistics or round numbers.

If the original deck contains images:
- Extract them from the unpacked PPTX (use `unpack.py`)
- Re-embed using `add_image_fit()` or M-PHOTO / M-SCREEN

### 7. Mandatory Closing Sequence

```python
make_closing_slide(prs)   # or make_closing_slide(prs, "ありがとうございました")
strip_sections(prs)
prs.save(output_path)
```

### 8. Verify

Run the standard verification pipeline (Steps 9-10 from SKILL.md):
1. `brand_check.py` → brand compliance
2. `verify_pptx.py` → structural QA
3. `thumbnail.py` → visual export
4. `markitdown output.pptx` → placeholder残留チェック
5. Read each thumbnail → visual self-review checklist

Compare the restyled deck against the original to ensure no content was lost.