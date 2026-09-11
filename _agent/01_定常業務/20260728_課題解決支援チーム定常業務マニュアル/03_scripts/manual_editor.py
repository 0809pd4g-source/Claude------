#!/usr/bin/env python3
"""
manual_editor.py
================
（月）進捗・課題_マニュアル集.docx を ClaudeCode から更新するツール。

使い方:
  python manual_editor.py <コマンド> [オプション]

コマンド一覧:
  list                    セクション一覧を表示
  show <セクション名>     セクションの内容をテキスト表示
  replace <old> <new>     文言を置換（全セクション対象）
  replace-in <セクション> <old> <new>  特定セクション内で置換
  add-section <jsonfile>  JSONファイルからセクションを追加
  set-date <担当者名>     全ページの最終更新日を今日日付・指定担当者に更新

例:
  python manual_editor.py list
  python manual_editor.py show "会議参加・議事メモ作成"
  python manual_editor.py replace "中里、崎坂" "山田、鈴木"
  python manual_editor.py replace-in "開催連絡（金）" "佐藤さん" "田中さん"
  python manual_editor.py set-date "中澤"
  python manual_editor.py add-section new_section.json
"""

import sys
import os
import json
import zipfile
import shutil
import re
import copy
import datetime
import argparse
import subprocess
from pathlib import Path
from lxml import etree

# ── 定数 ─────────────────────────────────────────────
DOCX_PATH = Path(__file__).parent / "（月）進捗・課題_マニュアル集.docx"
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
TMP_DIR = Path(os.environ.get("TEMP", "/tmp")) / "manual_editor_work"

# ── ユーティリティ ────────────────────────────────────
def extract(src: Path, dst: Path):
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)
    with zipfile.ZipFile(src, "r") as z:
        z.extractall(dst)

def repack(src_dir: Path, dst: Path):
    if dst.exists():
        dst.unlink()
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as z:
        for fp in src_dir.rglob("*"):
            if fp.is_file():
                z.write(fp, fp.relative_to(src_dir))

def load_doc(path: Path = DOCX_PATH):
    extract(path, TMP_DIR)
    doc_path = TMP_DIR / "word" / "document.xml"
    tree = etree.parse(str(doc_path))
    return tree

def save_doc(tree, path: Path = DOCX_PATH):
    doc_path = TMP_DIR / "word" / "document.xml"
    tree.write(str(doc_path), xml_declaration=True, encoding="UTF-8", standalone=True)
    repack(TMP_DIR, path)
    shutil.rmtree(TMP_DIR)
    print(f"✅ 保存しました: {path}")

def get_text(el) -> str:
    return "".join(t.text or "" for t in el.iter(f"{{{W}}}t"))

def get_style(para) -> str:
    pPr = para.find(f"{{{W}}}pPr")
    if pPr is None:
        return ""
    pStyle = pPr.find(f"{{{W}}}pStyle")
    return pStyle.get(f"{{{W}}}val", "") if pStyle is not None else ""

def is_h1(para) -> bool:
    return get_style(para) == "Heading1"

def find_sections(body) -> list[dict]:
    """H1見出しでセクションを分割してリストを返す"""
    sections = []
    current = None
    for i, child in enumerate(body):
        tag = child.tag.split("}")[1] if "}" in child.tag else child.tag
        if tag == "p" and is_h1(child):
            if current:
                sections.append(current)
            current = {"title": get_text(child), "start": i, "elements": [child]}
        elif current:
            current["elements"].append(child)
    if current:
        sections.append(current)
    return sections

# ── コマンド実装 ──────────────────────────────────────

def cmd_list():
    """セクション一覧を表示"""
    tree = load_doc()
    body = tree.getroot().find(f"{{{W}}}body")
    sections = find_sections(body)
    shutil.rmtree(TMP_DIR)
    print(f"セクション数: {len(sections)}\n")
    for i, s in enumerate(sections, 1):
        # テキスト量を概算
        text = "\n".join(get_text(el) for el in s["elements"])
        char_count = len(text.strip())
        print(f"  {i:2}. {s['title'][:50]}  （約{char_count}文字）")


def cmd_show(section_name: str):
    """特定セクションの内容をテキスト表示"""
    tree = load_doc()
    body = tree.getroot().find(f"{{{W}}}body")
    sections = find_sections(body)
    shutil.rmtree(TMP_DIR)

    matched = [s for s in sections if section_name in s["title"]]
    if not matched:
        print(f"❌ セクションが見つかりません: '{section_name}'")
        print("利用可能なセクション:")
        for s in sections:
            print(f"  - {s['title']}")
        return

    for s in matched:
        print(f"=== {s['title']} ===\n")
        lines = []
        for el in s["elements"]:
            tag = el.tag.split("}")[1] if "}" in el.tag else el.tag
            if tag == "p":
                t = get_text(el).strip()
                if t:
                    style = get_style(el)
                    prefix = ""
                    if "Heading2" in style:
                        prefix = "## "
                    elif "Heading3" in style:
                        prefix = "### "
                    lines.append(f"{prefix}{t}")
            elif tag == "tbl":
                lines.append("[テーブル]")
        print("\n".join(lines))
        print()


def cmd_replace(old: str, new: str, section_name: str = None):
    """文言を置換する（全体 or 特定セクション）"""
    tree = load_doc()
    root = tree.getroot()

    # XML内のテキストランを直接編集
    count = 0
    for t_el in root.iter(f"{{{W}}}t"):
        if t_el.text and old in t_el.text:
            # セクション絞り込みがある場合はスキップ判定
            if section_name:
                # 親パラグラフがそのセクション内にあるか確認（簡易版）
                para = t_el.getparent()
                while para is not None and para.tag.split("}")[-1] != "p":
                    para = para.getparent()
                # セクション名チェックのため前の H1 を探す
                body = root.find(f"{{{W}}}body")
                paragraphs = list(body)
                try:
                    para_idx = paragraphs.index(para)
                except ValueError:
                    # テーブル内セルなど
                    para_idx = -1

                # この段落の直前のH1タイトルを取得
                current_section = ""
                for p in reversed(paragraphs[:para_idx]):
                    if is_h1(p):
                        current_section = get_text(p)
                        break
                if section_name not in current_section:
                    continue

            t_el.text = t_el.text.replace(old, new)
            count += 1

    if count == 0:
        print(f"❌ '{old}' は見つかりませんでした")
        shutil.rmtree(TMP_DIR)
        return

    print(f"✅ {count}箇所を置換しました: '{old}' → '{new}'")
    save_doc(tree)


def cmd_insert_after(section_name: str, anchor_text: str, new_text: str, color: str = "888888"):
    """特定セクション内で、anchor_textを含む段落の直後に新しい段落を挿入する（対象会議・最終更新など欠落メタ行の補完用）"""
    tree = load_doc()
    root = tree.getroot()
    body = root.find(f"{{{W}}}body")
    sections = find_sections(body)

    matched = [s for s in sections if section_name in s["title"]]
    if not matched:
        print(f"❌ セクションが見つかりません: '{section_name}'")
        shutil.rmtree(TMP_DIR)
        return

    target = matched[0]
    anchor_el = None
    for el in target["elements"]:
        tag = el.tag.split("}")[1] if "}" in el.tag else el.tag
        if tag == "p" and anchor_text in get_text(el):
            anchor_el = el
            break

    if anchor_el is None:
        print(f"❌ アンカーテキストが見つかりません: '{anchor_text}'")
        shutil.rmtree(TMP_DIR)
        return

    new_p = etree.Element(f"{{{W}}}p")
    pPr = etree.SubElement(new_p, f"{{{W}}}pPr")
    spacing = etree.SubElement(pPr, f"{{{W}}}spacing")
    spacing.set(f"{{{W}}}after", "60")
    r = etree.SubElement(new_p, f"{{{W}}}r")
    rPr = etree.SubElement(r, f"{{{W}}}rPr")
    color_el = etree.SubElement(rPr, f"{{{W}}}color")
    color_el.set(f"{{{W}}}val", color)
    sz = etree.SubElement(rPr, f"{{{W}}}sz")
    sz.set(f"{{{W}}}val", "20")
    szCs = etree.SubElement(rPr, f"{{{W}}}szCs")
    szCs.set(f"{{{W}}}val", "20")
    t_el = etree.SubElement(r, f"{{{W}}}t")
    t_el.text = new_text
    t_el.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")

    parent = anchor_el.getparent()
    idx = list(parent).index(anchor_el)
    parent.insert(idx + 1, new_p)

    print(f"✅ '{anchor_text}' の直後に挿入しました: '{new_text}'")
    save_doc(tree)


def cmd_delete_section(section_name: str):
    """セクションをH1見出しごと完全に削除する（他セクションへの統合・整理用）"""
    tree = load_doc()
    root = tree.getroot()
    body = root.find(f"{{{W}}}body")
    sections = find_sections(body)

    matched = [s for s in sections if section_name in s["title"]]
    if not matched:
        print(f"❌ セクションが見つかりません: '{section_name}'")
        shutil.rmtree(TMP_DIR)
        return

    target = matched[0]
    for el in target["elements"]:
        parent = el.getparent()
        if parent is not None:
            parent.remove(el)

    print(f"✅ セクションを削除しました: '{target['title']}'")
    save_doc(tree)


def cmd_set_date(author: str):
    """全ページの最終更新日を今日・指定担当者に更新"""
    today = datetime.date.today()
    date_str = f"{today.year}年{today.month}月{today.day}日"
    new_text = f"最終更新：{date_str}　　担当：{author}"

    tree = load_doc()
    root = tree.getroot()
    count = 0

    for t_el in root.iter(f"{{{W}}}t"):
        if t_el.text and "最終更新：" in t_el.text:
            t_el.text = re.sub(
                r"最終更新：\d{4}年\d{1,2}月\d{1,2}日[　\s]+担当：\S+",
                new_text,
                t_el.text
            )
            count += 1

    print(f"✅ {count}箇所の最終更新日を更新: {new_text}")
    save_doc(tree)


def cmd_add_section(json_path: str):
    """
    JSONファイルからセクションを追加する。

    JSON形式:
    {
      "title": "【手順】新しいページ名",
      "after": "既存セクション名（この後に挿入。省略時は末尾）",
      "content": [
        {"type": "h2", "text": "概要"},
        {"type": "p",  "text": "説明文"},
        {"type": "h3", "text": "手順"},
        {"type": "step", "text": "最初にこれをする"},
        {"type": "step", "text": "次にこれをする"},
        {"type": "check", "text": "確認項目"},
        {"type": "note", "text": "補足情報（グレー）"},
        {"type": "warn", "text": "注意事項（赤・⚠️付き）"}
      ]
    }
    """
    try:
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ JSONファイルの読み込みエラー: {e}")
        return

    title = data.get("title", "")
    after_section = data.get("after", None)
    content = data.get("content", [])

    if not title:
        print("❌ title が指定されていません")
        return

    tree = load_doc()
    root = tree.getroot()

    # numbering.xml からnumId情報を取得
    num_path = TMP_DIR / "word" / "numbering.xml"
    tree_num = etree.parse(str(num_path))
    root_num = tree_num.getroot()

    # 既存のdecimal numIdを1つ選ぶ
    decimal_nid = None
    for num in root_num.findall(f"{{{W}}}num"):
        nid = num.get(f"{{{W}}}numId")
        abs_ref = num.find(f"{{{W}}}abstractNumId")
        if abs_ref is not None:
            anid = abs_ref.get(f"{{{W}}}val")
            for an in root_num.findall(f"{{{W}}}abstractNum"):
                if an.get(f"{{{W}}}abstractNumId") == anid:
                    for lvl in an.findall(f"{{{W}}}lvl"):
                        if lvl.get(f"{{{W}}}ilvl") == "0":
                            fmt = lvl.find(f"{{{W}}}numFmt")
                            if fmt is not None and fmt.get(f"{{{W}}}val") == "decimal":
                                decimal_nid = nid
                                decimal_anid = anid
                                break
                if decimal_nid:
                    break
        if decimal_nid:
            break

    # 新しいnumIdを作成（このセクション専用・1から開始）
    max_nid = max((int(n.get(f"{{{W}}}numId", 0)) for n in root_num.findall(f"{{{W}}}num")), default=0)
    max_nid += 1
    new_step_nid = str(max_nid)
    new_num = etree.SubElement(root_num, f"{{{W}}}num")
    new_num.set(f"{{{W}}}numId", new_step_nid)
    abs_ref_el = etree.SubElement(new_num, f"{{{W}}}abstractNumId")
    abs_ref_el.set(f"{{{W}}}val", decimal_anid)
    for lv in ["0", "1"]:
        lo = etree.SubElement(new_num, f"{{{W}}}lvlOverride")
        lo.set(f"{{{W}}}ilvl", lv)
        so = etree.SubElement(lo, f"{{{W}}}startOverride")
        so.set(f"{{{W}}}val", "1")

    tree_num.write(str(num_path), xml_declaration=True, encoding="UTF-8", standalone=True)

    # ヘルパー: 段落を生成
    def make_para(style_val=None, runs=None, numId=None, ilvl="0"):
        p = etree.Element(f"{{{W}}}p")
        pPr = etree.SubElement(p, f"{{{W}}}pPr")
        if style_val:
            pStyle = etree.SubElement(pPr, f"{{{W}}}pStyle")
            pStyle.set(f"{{{W}}}val", style_val)
        if numId:
            numPr = etree.SubElement(pPr, f"{{{W}}}numPr")
            ilvl_el = etree.SubElement(numPr, f"{{{W}}}ilvl")
            ilvl_el.set(f"{{{W}}}val", ilvl)
            numId_el = etree.SubElement(numPr, f"{{{W}}}numId")
            numId_el.set(f"{{{W}}}val", numId)
        if runs:
            for run_text, run_opts in runs:
                r = etree.SubElement(p, f"{{{W}}}r")
                rPr = etree.SubElement(r, f"{{{W}}}rPr")
                if run_opts.get("color"):
                    color_el = etree.SubElement(rPr, f"{{{W}}}color")
                    color_el.set(f"{{{W}}}val", run_opts["color"])
                if run_opts.get("size"):
                    sz = etree.SubElement(rPr, f"{{{W}}}sz")
                    sz.set(f"{{{W}}}val", str(run_opts["size"]))
                if run_opts.get("bold"):
                    etree.SubElement(rPr, f"{{{W}}}b")
                t_el = etree.SubElement(r, f"{{{W}}}t")
                t_el.text = run_text
                t_el.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        return p

    # セクション要素を構築
    today = datetime.date.today()
    new_elements = []

    # ページブレーク
    pb = etree.Element(f"{{{W}}}p")
    pb_r = etree.SubElement(pb, f"{{{W}}}r")
    pb_br = etree.SubElement(pb_r, f"{{{W}}}br")
    pb_br.set(f"{{{W}}}type", "page")
    new_elements.append(pb)

    # H1タイトル
    new_elements.append(make_para("Heading1", [(title, {"bold": True})]))

    # 最終更新行
    new_elements.append(make_para(None, [(
        f"最終更新：{today.year}年{today.month}月{today.day}日　　担当：中澤",
        {"color": "888888", "size": 20}
    )]))

    # コンテンツ要素
    for item in content:
        t = item.get("type", "p")
        text = item.get("text", "")

        if t == "h2":
            new_elements.append(make_para("Heading2", [(text, {"bold": True})]))
        elif t == "h3":
            new_elements.append(make_para("Heading3", [(text, {"bold": True})]))
        elif t == "p":
            new_elements.append(make_para(None, [(text, {})]))
        elif t == "step":
            new_elements.append(make_para(None, [(text, {})], numId=new_step_nid, ilvl="0"))
        elif t == "substep":
            new_elements.append(make_para(None, [(text, {})], numId=new_step_nid, ilvl="1"))
        elif t == "bullet":
            p = make_para(None, [(text, {})])
            pPr = p.find(f"{{{W}}}pPr")
            numPr = etree.SubElement(pPr, f"{{{W}}}numPr")
            ilvl_el = etree.SubElement(numPr, f"{{{W}}}ilvl")
            ilvl_el.set(f"{{{W}}}val", "0")
            numId_el = etree.SubElement(numPr, f"{{{W}}}numId")
            numId_el.set(f"{{{W}}}val", "1")  # bullet list
            new_elements.append(p)
        elif t == "check":
            new_elements.append(make_para(None, [("☐ " + text, {})]))
        elif t == "note":
            p = make_para(None, [(text, {"color": "888888", "size": 20})])
            pPr = p.find(f"{{{W}}}pPr")
            ind = etree.SubElement(pPr, f"{{{W}}}ind")
            ind.set(f"{{{W}}}left", "360")
            new_elements.append(p)
        elif t == "warn":
            p = make_para(None, [("⚠️ " + text, {"color": "C0392B"})])
            new_elements.append(p)
        elif t == "divider":
            p = etree.Element(f"{{{W}}}p")
            pPr = etree.SubElement(p, f"{{{W}}}pPr")
            pBdr = etree.SubElement(pPr, f"{{{W}}}pBdr")
            bottom = etree.SubElement(pBdr, f"{{{W}}}bottom")
            bottom.set(f"{{{W}}}val", "single")
            bottom.set(f"{{{W}}}sz", "1")
            bottom.set(f"{{{W}}}color", "CCCCCC")
            new_elements.append(p)

    # 挿入位置を決定
    body = root.find(f"{{{W}}}body")
    body_children = list(body)
    insert_idx = len(body_children) - 1  # デフォルトは末尾（sectPrの前）

    if after_section:
        sections = find_sections(body)
        matched = [s for s in sections if after_section in s["title"]]
        if matched:
            target = matched[0]
            # そのセクションの最後の要素の次
            last_el = target["elements"][-1]
            try:
                insert_idx = body_children.index(last_el) + 1
            except ValueError:
                pass
        else:
            print(f"⚠️ after セクション '{after_section}' が見つからないため末尾に追加します")

    # 挿入
    for i, el in enumerate(new_elements):
        body.insert(insert_idx + i, el)

    print(f"✅ セクション追加: '{title}' （{len(new_elements)}要素）")
    save_doc(tree)


# ── メイン ────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="マニュアル更新ツール",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("list", help="セクション一覧を表示")

    p_show = sub.add_parser("show", help="セクションの内容を表示")
    p_show.add_argument("section", help="セクション名（部分一致）")

    p_rep = sub.add_parser("replace", help="文言を全体で置換")
    p_rep.add_argument("old", help="置換前の文言")
    p_rep.add_argument("new", help="置換後の文言")

    p_repin = sub.add_parser("replace-in", help="特定セクション内で置換")
    p_repin.add_argument("section", help="セクション名（部分一致）")
    p_repin.add_argument("old", help="置換前の文言")
    p_repin.add_argument("new", help="置換後の文言")

    p_date = sub.add_parser("set-date", help="最終更新日を今日・指定担当者に更新")
    p_date.add_argument("author", help="担当者名")

    p_add = sub.add_parser("add-section", help="JSONからセクションを追加")
    p_add.add_argument("jsonfile", help="セクション定義JSONファイルのパス")

    p_ins = sub.add_parser("insert-after", help="特定セクション内の指定段落の直後に新しい段落を挿入")
    p_ins.add_argument("section", help="セクション名（部分一致）")
    p_ins.add_argument("anchor", help="挿入位置の目印となる既存テキスト（部分一致）")
    p_ins.add_argument("text", help="挿入する新しいテキスト")
    p_ins.add_argument("--color", default="888888", help="文字色（16進、既定888888）")

    p_del = sub.add_parser("delete-section", help="セクションをH1見出しごと完全に削除")
    p_del.add_argument("section", help="セクション名（部分一致）")

    args = parser.parse_args()

    if args.command == "list":
        cmd_list()
    elif args.command == "show":
        cmd_show(args.section)
    elif args.command == "replace":
        cmd_replace(args.old, args.new)
    elif args.command == "replace-in":
        cmd_replace(args.old, args.new, section_name=args.section)
    elif args.command == "set-date":
        cmd_set_date(args.author)
    elif args.command == "add-section":
        cmd_add_section(args.jsonfile)
    elif args.command == "insert-after":
        cmd_insert_after(args.section, args.anchor, args.text, color=args.color)
    elif args.command == "delete-section":
        cmd_delete_section(args.section)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
