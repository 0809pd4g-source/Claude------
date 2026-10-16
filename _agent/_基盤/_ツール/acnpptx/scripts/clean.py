"""
clean.py — Remove orphaned media files from an unpacked PPTX directory.

Usage:
    python scripts/clean.py output_dir/

Scans all .rels files to build the set of referenced media, then deletes
any file in ppt/media/ that is not referenced.
"""

import os
import sys
from lxml import etree

import paths as _paths
import safexml


def _collect_referenced_media(unpacked_dir: str) -> set[str]:
    """Walk all .rels files and collect referenced media filenames."""
    referenced: set[str] = set()

    for root, _dirs, files in os.walk(unpacked_dir):
        for fname in files:
            if not fname.endswith(".rels"):
                continue
            path = os.path.join(root, fname)
            try:
                tree = safexml.parse(path)
            except etree.XMLSyntaxError:
                continue
            for rel in tree.getroot():
                target = rel.get("Target", "")
                # Targets look like "../media/image1.png" or "media/image1.png"
                if "media/" in target:
                    referenced.add(os.path.basename(target))

    return referenced


def clean(unpacked_dir: str) -> None:
    """Remove unreferenced files from ppt/media/."""
    unpacked_dir = _paths.check_path(unpacked_dir, write=True)
    if not os.path.isdir(unpacked_dir):
        print(f"Error: directory not found — {unpacked_dir}", file=sys.stderr)
        sys.exit(1)

    media_dir = os.path.join(unpacked_dir, "ppt", "media")
    if not os.path.exists(media_dir):
        print("No ppt/media/ directory — nothing to clean.")
        return

    referenced = _collect_referenced_media(unpacked_dir)
    removed = 0

    for fname in sorted(os.listdir(media_dir)):
        if fname not in referenced:
            fpath = os.path.join(media_dir, fname)
            os.remove(fpath)
            print(f"  Removed orphaned: {fname}")
            removed += 1

    if removed == 0:
        print("Clean: no orphaned files found.")
    else:
        print(f"Clean: removed {removed} file(s).")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    clean(sys.argv[1])
