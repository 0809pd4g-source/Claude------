"""
add_slide.py — Duplicate an existing slide or insert a new blank slide from a layout.

Usage:
    # Duplicate slide 2, insert after position 3
    python scripts/add_slide.py output_dir/ --duplicate 2 --position 3

    # Duplicate slide 2 and append at end
    python scripts/add_slide.py output_dir/ --duplicate 2

IMPORTANT: Never copy slide files manually. Always use this script to keep
           presentation.xml, relationships, and slide IDs consistent.
"""

import argparse
import os
import re
import shutil
import sys
from lxml import etree

import paths as _paths
import safexml


# XML namespaces
NS_PML  = "http://schemas.openxmlformats.org/presentationml/2006/main"
NS_REL  = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_CT   = "http://schemas.openxmlformats.org/package/2006/content-types"
TYPE_SLIDE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide"
CT_SLIDE   = "application/vnd.openxmlformats-officedocument.presentationml.slide+xml"


def _parse(path: str) -> etree._ElementTree:
    with open(path, "rb") as f:
        return safexml.parse(f)


def _write(tree: etree._ElementTree, path: str) -> None:
    with open(path, "wb") as f:
        f.write(etree.tostring(
            tree.getroot(),
            pretty_print=True,
            xml_declaration=True,
            encoding="UTF-8",
            standalone=True,
        ))


def _slide_files(slides_dir: str) -> list[str]:
    """Return sorted list of slide XML filenames (e.g. ['slide1.xml', 'slide2.xml'])."""
    return sorted(
        (f for f in os.listdir(slides_dir) if re.match(r"slide\d+\.xml$", f)),
        key=lambda f: int(re.search(r"\d+", f).group()),
    )


def _next_slide_num(slides_dir: str) -> int:
    """Return the next available slide file number."""
    files = _slide_files(slides_dir)
    if not files:
        return 1
    return max(int(re.search(r"\d+", f).group()) for f in files) + 1


def _max_sld_id(prs_root: etree._Element) -> int:
    """Return the current maximum <p:sldId id=...> value."""
    ids = [
        int(e.get("id"))
        for e in prs_root.iter(f"{{{NS_PML}}}sldId")
        if e.get("id") is not None
    ]
    return max(ids) if ids else 255


def _next_rid(rels_root: etree._Element) -> str:
    """Return the next available rId string."""
    nums = [
        int(re.search(r"\d+", e.get("Id", "rId0")).group())
        for e in rels_root
        if re.search(r"\d+", e.get("Id", ""))
    ]
    return f"rId{max(nums) + 1 if nums else 1}"


def duplicate_slide(unpacked_dir: str, source_num: int, position: int | None) -> int:
    """
    Duplicate slide *source_num* (1-indexed) and insert it after *position*
    (1-indexed). Appends at end if *position* is None.

    Returns the new slide's file number.
    """
    ppt_dir    = os.path.join(unpacked_dir, "ppt")
    slides_dir = os.path.join(ppt_dir, "slides")
    rels_dir   = os.path.join(slides_dir, "_rels")
    prs_path   = os.path.join(ppt_dir, "presentation.xml")
    prs_rels_path = os.path.join(ppt_dir, "_rels", "presentation.xml.rels")

    src_xml  = os.path.join(slides_dir, f"slide{source_num}.xml")
    src_rels = os.path.join(rels_dir,   f"slide{source_num}.xml.rels")

    if not os.path.exists(src_xml):
        raise FileNotFoundError(f"slide{source_num}.xml not found in {slides_dir}")

    new_num  = _next_slide_num(slides_dir)
    new_xml  = os.path.join(slides_dir, f"slide{new_num}.xml")
    new_rels = os.path.join(rels_dir,   f"slide{new_num}.xml.rels")

    # --- Copy slide content files ---
    shutil.copy2(src_xml, new_xml)
    if os.path.exists(src_rels):
        shutil.copy2(src_rels, new_rels)

    # --- Add relationship in presentation.xml.rels ---
    prs_rels_tree = _parse(prs_rels_path)
    prs_rels_root = prs_rels_tree.getroot()
    new_rid = _next_rid(prs_rels_root)

    new_rel = etree.SubElement(prs_rels_root, "Relationship")
    new_rel.set("Id",     new_rid)
    new_rel.set("Type",   TYPE_SLIDE)
    new_rel.set("Target", f"slides/slide{new_num}.xml")
    _write(prs_rels_tree, prs_rels_path)

    # --- Add <p:sldId> entry in presentation.xml ---
    prs_tree = _parse(prs_path)
    prs_root = prs_tree.getroot()
    sld_id_lst = prs_root.find(f"{{{NS_PML}}}sldIdLst")
    if sld_id_lst is None:
        raise RuntimeError("<p:sldIdLst> not found in presentation.xml")

    new_sld_id = etree.Element(f"{{{NS_PML}}}sldId")
    new_sld_id.set("id", str(_max_sld_id(prs_root) + 1))
    new_sld_id.set(f"{{{NS_REL}}}id", new_rid)

    children = list(sld_id_lst)
    if position is None or position >= len(children):
        sld_id_lst.append(new_sld_id)
    else:
        sld_id_lst.insert(position, new_sld_id)

    _write(prs_tree, prs_path)

    # --- Register new slide in [Content_Types].xml ---
    ct_path = os.path.join(unpacked_dir, "[Content_Types].xml")
    ct_tree = _parse(ct_path)
    ct_root = ct_tree.getroot()
    override = etree.SubElement(ct_root, f"{{{NS_CT}}}Override")
    override.set("PartName", f"/ppt/slides/slide{new_num}.xml")
    override.set("ContentType", CT_SLIDE)
    _write(ct_tree, ct_path)

    pos_label = "end" if (position is None or position >= len(children)) else f"after position {position}"
    print(f"Duplicated slide{source_num} -> slide{new_num}.xml  ({pos_label})")
    return new_num


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Duplicate a slide in an unpacked PPTX directory.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("unpacked_dir", help="Path to the unpacked PPTX directory")
    parser.add_argument(
        "--duplicate", type=int, metavar="N", required=True,
        help="Slide number to duplicate (1-indexed)",
    )
    parser.add_argument(
        "--position", type=int, metavar="N", default=None,
        help="Insert after this position (1-indexed; default: append at end)",
    )
    args = parser.parse_args()
    try:
        duplicate_slide(_paths.check_path(args.unpacked_dir, write=True), args.duplicate, args.position)
    except (FileNotFoundError, RuntimeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
