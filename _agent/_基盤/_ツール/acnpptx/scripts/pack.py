"""
pack.py — Repack an unpacked PPTX directory back into a .pptx file.

Usage:
    python scripts/pack.py input_dir output.pptx

The script zips the entire directory tree and writes a valid PPTX.
[Content_Types].xml is written first (some readers expect it early in the archive).
"""

import os
import sys
import zipfile

import paths as _paths


def pack(input_dir: str, output_pptx: str) -> None:
    """Zip *input_dir* into *output_pptx* (PPTX-compatible ZIP)."""
    input_dir = _paths.check_path(input_dir)
    output_pptx = _paths.check_path(output_pptx, write=True)

    if not os.path.isdir(input_dir):
        print(f"Error: directory not found — {input_dir}", file=sys.stderr)
        sys.exit(1)

    # Collect all files, putting [Content_Types].xml first
    all_files: list[str] = []
    content_types: list[str] = []

    for root, _dirs, files in os.walk(input_dir):
        for fname in files:
            fpath = os.path.join(root, fname)
            arcname = os.path.relpath(fpath, input_dir).replace(os.sep, "/")
            if arcname == "[Content_Types].xml":
                content_types.append(fpath)
            else:
                all_files.append(fpath)

    with zipfile.ZipFile(output_pptx, "w", zipfile.ZIP_DEFLATED) as zf:
        # Write [Content_Types].xml first
        for fpath in content_types:
            arcname = os.path.relpath(fpath, input_dir).replace(os.sep, "/")
            zf.write(fpath, arcname)
        # Write everything else
        for fpath in all_files:
            arcname = os.path.relpath(fpath, input_dir).replace(os.sep, "/")
            zf.write(fpath, arcname)

    size_kb = os.path.getsize(output_pptx) // 1024
    print(f"Packed: {input_dir}/ -> {output_pptx}  ({size_kb} KB)")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    pack(sys.argv[1], sys.argv[2])
