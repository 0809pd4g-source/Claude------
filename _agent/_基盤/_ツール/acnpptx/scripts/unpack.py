"""
unpack.py — Extract a PPTX file into an editable XML directory.

Usage:
    python scripts/unpack.py input.pptx [output_dir]

If output_dir is omitted, creates a folder named <basename>_unpacked
in the same directory as the input file.

Output layout mirrors the PPTX ZIP structure:
    output_dir/
    ├── [Content_Types].xml
    ├── _rels/
    ├── ppt/
    │   ├── presentation.xml
    │   ├── slides/
    │   │   ├── slide1.xml  ...
    │   │   └── _rels/
    │   ├── slideLayouts/
    │   ├── slideMasters/
    │   └── media/
    └── docProps/

All XML / .rels files are pretty-printed for readability.
"""

import os
import sys
import zipfile
from lxml import etree

import paths as _paths
import safexml


def _format_xml(data: bytes) -> bytes:
    """Pretty-print XML bytes; return original bytes on parse failure."""
    try:
        root = safexml.fromstring(data)
        return etree.tostring(
            root,
            pretty_print=True,
            xml_declaration=True,
            encoding="UTF-8",
            standalone=True,
        )
    except etree.XMLSyntaxError:
        return data


def unpack(pptx_path: str, output_dir: str | None = None) -> str:
    """Extract *pptx_path* into *output_dir* and return the output path."""
    pptx_path = _paths.check_path(pptx_path)
    if not os.path.isfile(pptx_path):
        print(f"Error: file not found — {pptx_path}", file=sys.stderr)
        sys.exit(1)

    if output_dir is None:
        base = os.path.splitext(os.path.basename(pptx_path))[0]
        output_dir = os.path.join(os.path.dirname(pptx_path), base + "_unpacked")

    output_dir = _paths.check_path(output_dir, write=True)

    with zipfile.ZipFile(pptx_path, "r") as zf:
        for info in zf.infolist():
            # 「..」・絶対パス・ドライブ指定を含む名前は展開しない
            parts = info.filename.replace("\\", "/").split("/")
            if info.filename.startswith(("/", "\\")) or ":" in info.filename or ".." in parts:
                print(f"Error: unsafe ZIP entry — {info.filename}", file=sys.stderr)
                sys.exit(1)
            target = os.path.normpath(os.path.join(output_dir, info.filename))
            safe_root = os.path.normpath(output_dir)
            if not target.startswith(safe_root + os.sep) and target != safe_root:
                print(f"Error: unsafe ZIP entry — {info.filename}", file=sys.stderr)
                sys.exit(1)
            if info.is_dir():
                os.makedirs(target, exist_ok=True)
                continue

            os.makedirs(os.path.dirname(target), exist_ok=True)
            raw = zf.read(info.filename)

            if info.filename.endswith(".xml") or info.filename.endswith(".rels"):
                raw = _format_xml(raw)

            with open(target, "wb") as f:
                f.write(raw)

    print(f"Unpacked: {output_dir}/")

    slides_dir = os.path.join(output_dir, "ppt", "slides")
    if os.path.exists(slides_dir):
        slides = sorted(
            f for f in os.listdir(slides_dir)
            if f.startswith("slide") and f.endswith(".xml")
        )
        print(f"  {len(slides)} slide(s): {', '.join(slides)}")

    return output_dir


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    unpack(
        sys.argv[1],
        sys.argv[2] if len(sys.argv) > 2 else None,
    )
