# Editing Workflow (Template-Based)

7-phase process for modifying existing PPTX files via XML manipulation.

## Phase 1: Analysis

Examine the template visually and textually:

```bash
# Set SKILL_DIR once at the start of each session
# SKILL_DIR と PY は SKILL.md の Setup で示したもの

$PY -m markitdown '<template.pptx>'                                # Extract all text（パスは単一引用符で囲む）
$PY "$SKILL_DIR/scripts/thumbnail.py" template.pptx                # Visual grid (requires Microsoft PowerPoint + pywin32)
```

Identify: available layouts, reusable slides, slide dimensions, placeholder indices.

**thumbnail.py implementation (PowerPoint COM):**

```python
# scripts/thumbnail.py
# Requires: pip install pywin32  (Microsoft PowerPoint must be installed)
import win32com.client, os, sys

def export_thumbnails(pptx_path, output_dir="thumbnails", width=1280):
    abs_path = os.path.abspath(pptx_path)
    os.makedirs(output_dir, exist_ok=True)
    ppt = win32com.client.Dispatch("PowerPoint.Application")
    ppt.Visible = True
    try:
        prs = ppt.Presentations.Open(abs_path, ReadOnly=True, WithWindow=False)
        for i in range(1, prs.Slides.Count + 1):
            out = os.path.abspath(os.path.join(output_dir, f"slide_{i:02d}.png"))
            prs.Slides(i).Export(out, "PNG", width)
            print(f"  slide_{i:02d}.png")
        print(f"Saved {prs.Slides.Count} thumbnails → {output_dir}/")
        prs.Close()
    finally:
        ppt.Quit()

if __name__ == "__main__":
    export_thumbnails(sys.argv[1] if len(sys.argv) > 1 else "template.pptx")
```

## Phase 2: Layout Planning

Select slide designs for each content section. **Avoid repeating the same layout.**

Seek: multi-column layouts, image + text combos, full-bleed images, quote slides, section dividers, stat callouts, icon grids.

Do NOT default to title + bullet slides.

## Phase 3: Unpacking

```bash
python "$SKILL_DIR/scripts/unpack.py" template.pptx output_dir/
```

Extracts PPTX into editable XML. Each slide becomes `slide{N}.xml`.

## Phase 4: Structural Modification

Reorganize slides: delete unwanted, duplicate reusable, reorder via `<p:sldIdLst>`.

```bash
python "$SKILL_DIR/scripts/add_slide.py" output_dir/ --duplicate 2 --position 3
```

**Complete ALL structural changes before content editing.**

## Phase 5: Content Editing

Update text within `slide{N}.xml` files using the Edit tool.

**Text formatting rules:**
- Bold headers: `b="1"` on `<a:rPr>`
- Lists: `<a:buChar>` or `<a:buAutoNum>` (never unicode bullets)
- Multi-item lists: separate `<a:p>` elements
- Smart quotes: `&#x201C;` `&#x201D;` (not ASCII `"`)

Slide files are independent — parallel subagent editing is possible.

## Phase 6: Cleanup

```bash
python "$SKILL_DIR/scripts/clean.py" output_dir/
```

Removes orphaned files and unused media references.

## Phase 7: Repacking

```bash
python "$SKILL_DIR/scripts/pack.py" output_dir/ output.pptx
```

Converts modified XML back into validated PPTX.

## Available Scripts

| Script | Function |
|--------|----------|
| `unpack.py` | Extract and format PPTX to editable XML |
| `add_slide.py` | Duplicate or create slides from layouts |
| `clean.py` | Remove unused files and references |
| `pack.py` | Repack XML into validated PPTX |
| `thumbnail.py` | Export slides as PNG thumbnails via PowerPoint COM (requires `pywin32` + Microsoft PowerPoint) |

**Important**: Never manually copy slide files. Use `add_slide.py` to preserve internal references.
