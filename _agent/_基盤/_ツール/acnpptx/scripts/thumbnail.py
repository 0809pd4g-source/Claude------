"""
thumbnail.py — Export each slide as a PNG thumbnail via PowerPoint COM automation.

Requirements:
    pip install pywin32
    Microsoft PowerPoint must be installed on this machine (Windows only).

Usage:
    python scripts/thumbnail.py presentation.pptx [output_dir] [width]

    output_dir  Default: thumbnails/  (created if absent)
    width       Export width in pixels. Default: 1280
                Height is calculated automatically to preserve 16:9 ratio.

Output:
    output_dir/slide_01.png
    output_dir/slide_02.png
    ...
"""

import os
import sys


def export_thumbnails(
    pptx_path: str,
    output_dir: str = "thumbnails",
    width: int = 1280,
) -> None:
    try:
        import win32com.client
    except ImportError:
        print(
            "Error: pywin32 is not installed.\n"
            "Run:  pip install pywin32\n"
            "Also ensure Microsoft PowerPoint is installed.",
            file=sys.stderr,
        )
        sys.exit(1)

    abs_path = os.path.abspath(pptx_path)
    if not os.path.isfile(abs_path):
        print(f"Error: file not found — {abs_path}", file=sys.stderr)
        sys.exit(1)
    if abs_path.lower().endswith((".pptm", ".potm", ".ppsm", ".ppam")):
        print(f"Error: macro-enabled file is not supported — {abs_path}", file=sys.stderr)
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)

    ppt = win32com.client.Dispatch("PowerPoint.Application")
    ppt.AutomationSecurity = 3  # msoAutomationSecurityForceDisable: 開くファイルのマクロを実行しない
    ppt.Visible = True
    prs = None
    try:
        prs = ppt.Presentations.Open(abs_path, ReadOnly=True, WithWindow=False)
        count = prs.Slides.Count
        for i in range(1, count + 1):
            out = os.path.abspath(os.path.join(output_dir, f"slide_{i:02d}.png"))
            prs.Slides(i).Export(out, "PNG", width)
            print(f"  slide_{i:02d}.png")
        print(f"Saved {count} thumbnail(s): {output_dir}/")
    finally:
        if prs is not None:
            prs.Close()
            del prs
        ppt.Quit()
        del ppt
        import gc
        gc.collect()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    import paths as _paths
    pptx   = _paths.check_path(sys.argv[1])
    outdir = _paths.check_path(sys.argv[2] if len(sys.argv) > 2 else "thumbnails", write=True)
    w      = int(sys.argv[3]) if len(sys.argv) > 3 else 1280

    if w < 256 or w > 4096:
        print("Error: width must be between 256 and 4096", file=sys.stderr)
        sys.exit(1)

    export_thumbnails(pptx, outdir, w)
