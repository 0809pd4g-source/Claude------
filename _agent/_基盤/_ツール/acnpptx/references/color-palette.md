# Accenture Color Palette — Official Brand Colors

## Usage Ratio
- **Neutrals**: 60–70% of slide area
- **Purple spectrum**: 30–40%
- **Secondary colors**: < 5% (use sparingly, only for specific emphasis)

## Purple Spectrum

| Constant | Hex | Use Case |
|----------|-----|----------|
| `DARKEST_PURPLE` | `#460073` | Cover backgrounds, section dividers |
| `DARK_PURPLE` | `#7500C0` | Emphasis, key badges, accent bars |
| `CORE_PURPLE` | `#A100FF` | Primary accent, logo color, CTAs |
| `LIGHT_PURPLE` | `#C2A3FF` | Subtitle text on dark bg, tinted elements |
| `LIGHTEST_PURPLE` | `#E6DCFF` | Subtle tinted backgrounds, hover states |

## Neutrals

| Constant | Hex | Use Case |
|----------|-----|----------|
| `BLACK` | `#000000` | Titles, headings |
| `MID_GRAY` | `#818180` | Secondary text, metadata |
| `LIGHT_GRAY` | `#CFCFCF` | Borders, divider lines |
| `OFF_WHITE` | `#F1F1EF` | Card backgrounds, panels |
| `WHITE` | `#FFFFFF` | Slide backgrounds, text on dark |

## Secondary (use sparingly)

| Constant | Hex | Use Case |
|----------|-----|----------|
| `PINK` | `#FF50A0` | Highlights, special callouts |
| `BLUE` | `#224BFF` | Data visualization, links |
| `AQUA` | `#05F2DB` | Innovation, tech-themed slides |

## Practical Text Colors (not in official palette but approved for readability)

| Constant | Hex | Use Case |
|----------|-----|----------|
| `TEXT_BODY` | `#333333` | Body text on white background |
| `TEXT_SUB` | `#666666` | Captions, footnotes, metadata |

## Backward Compatibility Aliases

| Alias | Points To |
|-------|-----------|
| `PURPLE` | `CORE_PURPLE` (#A100FF) |
| `DEEP_PURPLE` | `DARKEST_PURPLE` (#460073) |
| `BG_LIGHT` | `OFF_WHITE` (#F1F1EF) |

## Rules

1. **No warm tones** — no reds, oranges, or yellows except with explicit approval
2. **No gradients** — solid fills only
3. **Contrast** — always ensure text contrast ≥ 4.5:1 against background
4. **Light mode default** — white background preferred for text-heavy slides
5. **Dark mode only for impact** — cover slides, section dividers
6. **Purple with purpose** — purple elements should guide the eye, not decorate

---

## Python Quick Reference

```python
# Purple (dark to light)
DARKEST_PURPLE  # #460073 — cover bg, section dividers
DARK_PURPLE     # #7500C0 — emphasis badges, message line
CORE_PURPLE     # #A100FF — primary accent
LIGHT_PURPLE    # #C2A3FF — subtitle on dark bg
LIGHTEST_PURPLE # #E6DCFF — subtle tinted backgrounds

# Neutrals
BLACK      # #000000 — titles
MID_GRAY   # #818180 — secondary text, breadcrumb
LIGHT_GRAY # #CFCFCF — borders
OFF_WHITE  # #F1F1EF — card backgrounds
WHITE      # #FFFFFF — slide bg, text on dark

# Text
TEXT_BODY  # #333333 — body on white
TEXT_SUB   # #666666 — captions, footnotes

# Aliases (backward compat)
PURPLE      = CORE_PURPLE       # #A100FF
DEEP_PURPLE = DARKEST_PURPLE    # #460073
BG_LIGHT    = OFF_WHITE         # #F1F1EF
```
