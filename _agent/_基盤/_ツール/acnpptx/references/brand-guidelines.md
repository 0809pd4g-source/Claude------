# Accenture Brand Guidelines — PPTX Generation Rules

## Logo Usage

Logo and GT symbol are embedded in the slide master and provided automatically on every slide. **Never add them manually.**

- `add_logo()` and `add_gt_symbol()` have been removed — calling them will cause an error
- Use `add_cover_slide()` for cover slides; the master supplies logo, GT symbol, and background automatically
- Use `add_slide()` for content slides; the master supplies GT symbol and footer band automatically

### Logo prohibitions
- Do NOT change logo colors
- Do NOT rotate the logo
- Do NOT box or frame the logo
- Do NOT add text or slogans
- Do NOT alter opacity
- Do NOT use the GT symbol as an arrow or directional indicator

## Typography

### Fonts by language

| Language | Primary Font | Secondary (quotes only) | Fallback |
|----------|-------------|--------------------------|---------|
| English | Graphik | GT Sectra Fine | Arial |
| Japanese | Meiryo UI | — | MS Gothic |

**Set language at top of generation script:**
```python
from helpers import set_lang
set_lang("en")  # or set_lang("ja")
```

### Font sizes — コンテンツスライド（白背景）

| Role | Size | Weight | Text color | Zone bg |
|------|------|--------|-----------|---------|
| Slide title | 28pt | Bold | BLACK | NONE |
| Message line | **18pt** | Bold | DARK_PURPLE | NONE |
| Lead / subtitle | 18pt | Regular | TEXT_BODY | NONE |
| Body / bullets | 14pt | Regular | TEXT_BODY | NONE |
| Label on colored bg | 14pt | Regular/Bold | WHITE | (card fill) |
| Caption / note | 12pt | Regular | MID_GRAY | NONE |
| Footer | 8pt | Regular | TEXT_SUB | NONE |

### Font sizes — カバースライド（DARKEST_PURPLE 背景）

| Role | Size | Weight | Text color | Zone bg |
|------|------|--------|-----------|---------|
| Cover title | 36–44pt | Bold | WHITE | DARKEST_PURPLE |
| Cover subtitle | 18pt | Regular | LIGHT_PURPLE | DARKEST_PURPLE |
| Date / author | 16pt | Regular | LIGHT_PURPLE | DARKEST_PURPLE |

> **白背景カバー (`cover_text_color: "BLACK"`)**: WHITE / LIGHT_PURPLE は不可視になる。全テキストを BLACK / TEXT_BODY / MID_GRAY にすること。

- **13pt は使用禁止** — 使用可能サイズ: 12 / 14 / 18 / 28 / 36〜44
- **Minimum**: 12pt（brand_check.py が強制）
- **Sentence case only** — ALL CAPS・Title Case 禁止

### Text alignment
- **Left-align** all body text
- **Center-align** only for cover titles and single-value KPI numbers
- Never right-align body content

## Shape Rules

- **Rectangles only** — no rounded corners, no circles for containers
  - `prs.slides.add_shape(MSO_SHAPE_TYPE.RECTANGLE, ...)`
  - `rounded=0` always
- **No gradients** — solid fills only
- **No image cropping** with circular masks
- **No shadows** on text

## Slide Design Principles

1. **White canvas default** — start with `#FFFFFF` background for content slides
2. **Generous whitespace** — don't pack content wall-to-wall
3. **One visual focus** per slide — the reader's eye should go to one primary element
4. **GT symbol as decoration** — subtle size (0.8"–1.5"), low-key placement
5. **Purple with purpose** — use purple to highlight 1–2 key elements, not everywhere
6. **No mixing light/dark** — one mode per slide

## Greater Than Symbol Placement Guide

```
Cover slide:
  Large GT (2.0"–3.0"), bottom-right, dark_bg=True, semi-transparent feel
  OR: background-sized GT (~5") behind title, very light opacity look

Internal slide (content):
  Small GT (0.8"–1.2"), bottom-right corner (x≈11.8", y≈5.8")
  OR: medium GT (1.5"), right-margin decorative (x≈12.3", y≈2.0")
  Color: CORE_PURPLE (light bg) or WHITE (dark bg)

Section divider:
  Medium GT (1.5"–2.0"), centered-right, white on dark background
```

## Assets Path Reference

Logo and GT symbol assets have been removed — they are now provided exclusively by the slide master.

```python
# Slide master template (provides logo, GT symbol, footer automatically)
TEMPLATE = os.path.join(_SKILL_DIR, "assets", "slide-master.pptx")

# Color constants (from helpers.py)
from helpers import (
    CORE_PURPLE, DARK_PURPLE, DARKEST_PURPLE, LIGHT_PURPLE, LIGHTEST_PURPLE,
    BLACK, MID_GRAY, LIGHT_GRAY, OFF_WHITE, WHITE,
    TEXT_BODY, TEXT_SUB,
    PINK, BLUE, AQUA,
)
```
