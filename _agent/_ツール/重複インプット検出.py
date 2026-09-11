# -*- coding: utf-8 -*-
"""
_agent/ 配下の各プロジェクト 01_input/ に置かれているファイルのうち、
_agent/_input/ にも同名ファイルが存在するものを検出する。

「二重保持」を防ぐため、各プロジェクトの 01_input/ には
参照情報（所在メモ）だけを置き、実体は _agent/_input/ に1箇所に集約するのが原則。

使い方:
    python _agent/_ツール/重複インプット検出.py
    python _agent/_ツール/重複インプット検出.py --all  # 全01_inputの内容を一覧表示（重複に限らず）
"""
import os, io, sys

ROOT = r"C:\Users\masato.nakazawa\Downloads\Claudeプロジェクト\_agent"
SHARED_INPUT = os.path.join(ROOT, "_input")
SHOW_ALL = "--all" in sys.argv


def list_shared():
    """_agent/_input/ のファイル名セットを返す"""
    try:
        return {f.lower(): f for f in os.listdir(SHARED_INPUT)
                if os.path.isfile(os.path.join(SHARED_INPUT, f))}
    except Exception:
        return {}


def scan():
    shared = list_shared()
    duplicates = []
    all_files = []

    for dirpath, dirnames, filenames in os.walk(ROOT):
        # _input/ フォルダ自体はスキップ
        if os.path.basename(dirpath) == "_input" and dirpath == SHARED_INPUT:
            continue
        # 各プロジェクトの 01_input/ のみ対象
        if os.path.basename(dirpath) != "01_input":
            continue

        for fname in filenames:
            rel_dir = os.path.relpath(dirpath, ROOT)
            full_path = os.path.join(dirpath, fname)
            size = os.path.getsize(full_path)

            entry = {
                "name": fname,
                "path": os.path.join(rel_dir, fname),
                "size_kb": round(size / 1024, 1),
                "in_shared": fname.lower() in shared,
            }
            all_files.append(entry)
            if entry["in_shared"]:
                duplicates.append(entry)

    return duplicates, all_files, shared


def main():
    duplicates, all_files, shared = scan()

    print(f"\n{'='*60}")
    print("  _input/ 重複検出レポート")
    print(f"{'='*60}\n")
    print(f"  _agent/_input/ の共有資料数: {len(shared)} ファイル")
    print(f"  プロジェクト 01_input/ のファイル数: {len(all_files)} ファイル")

    if duplicates:
        print(f"\n⚠️  重複（_agent/_input/ に同名あり）: {len(duplicates)} ファイル")
        print("  → 以下のファイルはプロジェクト側で保持せず、_agent/_input/ を参照してください\n")
        for d in duplicates:
            print(f"  🔴 {d['name']}  ({d['size_kb']} KB)")
            print(f"      場所: _agent/{d['path']}")
            print(f"      共有: _agent/_input/{d['name']}")
    else:
        print("\n✅ 重複なし（全プロジェクトが独自の資料のみ保持）")

    if SHOW_ALL:
        unique = [f for f in all_files if not f["in_shared"]]
        if unique:
            print(f"\n--- プロジェクト固有のファイル: {len(unique)} ---")
            for u in unique:
                print(f"  _agent/{u['path']}  ({u['size_kb']} KB)")

    print(f"\n{'='*60}\n")


if __name__ == "__main__":
    main()
