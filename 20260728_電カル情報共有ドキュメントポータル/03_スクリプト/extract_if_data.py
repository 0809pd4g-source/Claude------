#!/usr/bin/env python3
"""
外部インターフェイス仕様書 データ抽出スクリプト
====================================================
対象PDF:
  - 別紙3-1_XMLレイアウト_オン資格_電子処方箋_電カル情報共有__Ver*.pdf
  - 外部インターフェイス仕様書_オン資格_電子処方箋_電カル情報共有__Ver*.pdf

使い方:
  python extract_if_data.py --xml-layout 別紙3-1_....pdf --output if_data.json
  python extract_if_data.py --xml-layout 別紙3-1_....pdf --output if_data.json --inject-html portal.html

依存:
  pip install pdfminer.six  # または pdftotext (poppler-utils) が使えればOK
"""

import re
import json
import argparse
import subprocess
import sys
import os
from pathlib import Path


# ============================================================
# 既知のIF名称マッピング（テキスト抽出でズレる場合のフォールバック）
# ============================================================
OQS_NAMES = {
    'OQS-IF-001': '資格確認要求', 'OQS-IF-002': '資格確認結果',
    'OQS-IF-003': '照会番号登録要求', 'OQS-IF-004': '照会番号登録結果',
    'OQS-IF-005': '資格確認一括照会要求', 'OQS-IF-006': '資格確認一括照会アップロード結果',
    'OQS-IF-007': '資格確認一括照会ダウンロード要求', 'OQS-IF-008': '資格確認一括照会結果',
    'OQS-IF-009': '照会番号一括登録要求', 'OQS-IF-010': '照会番号一括登録アップロード結果',
    'OQS-IF-011': '照会番号一括登録ダウンロード要求', 'OQS-IF-012': '照会番号一括登録結果',
    'OQS-IF-013': '委託先資格情報の一括取得要求', 'OQS-IF-014': '委託先資格情報の一括取得アップロード結果',
    'OQS-IF-015': '委託先資格情報の一括取得ダウンロード要求', 'OQS-IF-016': '委託先資格情報の一括取得結果',
    'OQS-IF-017': '同意済資格情報一括取得要求（訪問診療等）', 'OQS-IF-018': '同意済資格情報一括取得アップロード結果（訪問診療等）',
    'OQS-IF-019': '同意済資格情報一括取得ダウンロード要求（訪問診療等）', 'OQS-IF-020': '同意済資格情報一括取得結果（訪問診療等）',
    'OQS-IF-021': '同意済資格情報一括取得要求（オンライン診療等）', 'OQS-IF-022': '同意済資格情報一括取得アップロード結果（オンライン診療等）',
    'OQS-IF-023': '同意済資格情報一括取得ダウンロード要求（オンライン診療等）', 'OQS-IF-024': '同意済資格情報一括取得結果（オンライン診療等）',
    'OQS-IF-025': '資格確認要求（訪問診療等）', 'OQS-IF-026': '資格確認結果（訪問診療等）',
    'OQS-IF-027': '資格確認要求（オンライン診療等）', 'OQS-IF-028': '資格確認結果（オンライン診療等）',
    'OQS-IF-029': '資格確認一括照会要求（訪問診療等）', 'OQS-IF-030': '資格確認一括照会アップロード結果（訪問診療等）',
    'OQS-IF-031': '資格確認一括照会ダウンロード要求（訪問診療等）', 'OQS-IF-032': '資格確認一括照会結果（訪問診療等）',
    'OQS-IF-033': '資格確認一括照会要求（オンライン診療等）', 'OQS-IF-034': '資格確認一括照会アップロード結果（オンライン診療等）',
    'OQS-IF-035': '資格確認一括照会ダウンロード要求（オンライン診療等）', 'OQS-IF-036': '資格確認一括照会結果（オンライン診療等）',
    'OQS-IF-037': '閲覧同意取り消し要求（訪問診療等）', 'OQS-IF-038': '閲覧同意取り消し結果（訪問診療等）',
    'OQS-IF-039': '医療機関アクセスURL取得要求', 'OQS-IF-040': '医療機関アクセスURL取得結果',
    'OQS-IF-041': '医療機関環境設定情報照会要求', 'OQS-IF-042': '医療機関環境設定情報照会結果',
    'OQS-IF-043': '医療機関環境設定情報更新要求', 'OQS-IF-044': '医療機関環境設定情報更新結果',
    'OQS-IF-045': '電子カルテ情報共有サービス施設利用状況回答要求', 'OQS-IF-046': '電子カルテ情報共有サービス施設利用状況回答結果',
    'OQS-IF-047': '資格確認要求（救急時医療情報閲覧）', 'OQS-IF-048': '資格確認結果（救急時医療情報閲覧）',
    'OQS-IF-049': '目視確認用パスコード取得要求', 'OQS-IF-050': '目視確認用パスコード取得結果',
    'OQS-IF-051': 'アクティベーションコード照会要求', 'OQS-IF-052': 'アクティベーションコード照会結果',
    'OQS-IF-053': 'アクティベーションコード発行要求', 'OQS-IF-054': 'アクティベーションコード発行結果',
    'OQS-IF-055': 'アクティベーションコード無効化要求', 'OQS-IF-056': 'アクティベーションコード無効化結果',
}

EPS_NAMES = {
    'EPS-IF-101': '重複投薬等チェック事前処理要求', 'EPS-IF-102': '重複投薬等チェック事前処理結果',
    'EPS-IF-103': '重複投薬等チェック結果',
    'EPS-IF-201': '処方箋登録要求', 'EPS-IF-202': '処方箋登録結果',
    'EPS-IF-203': '処方箋取消要求', 'EPS-IF-204': '処方箋取消結果',
    'EPS-IF-205': '処方箋変更要求', 'EPS-IF-206': '処方箋変更結果',
    'EPS-IF-207': '処方箋取消UNDO要求', 'EPS-IF-208': '処方箋取消UNDO結果',
    'EPS-IF-209': '処方箋変更UNDO要求', 'EPS-IF-210': '処方箋変更UNDO結果',
    'EPS-IF-211': '処方内容（控え）取得要求', 'EPS-IF-212': '処方内容（控え）取得結果',
    'EPS-IF-213': '処方箋状況及び調剤結果リスト要求', 'EPS-IF-214': '処方箋状況及び調剤結果リスト',
    'EPS-IF-215': '調剤結果要求（調剤結果ID）', 'EPS-IF-216': '調剤結果',
    'EPS-IF-217': '処方箋状況及び調剤結果要求（処方箋ID）', 'EPS-IF-218': '処方箋状況及び調剤結果（処方箋単位）',
    'EPS-IF-219': '重複投薬等チェック要求（確定前処方箋情報）',
    'EPS-IF-220': '処方箋ID検索要求（医療機関）', 'EPS-IF-221': '処方箋ID検索結果（医療機関）',
    'EPS-IF-301': '処方箋受付要求（引換番号）', 'EPS-IF-302': '処方箋受付結果',
    'EPS-IF-303': '処方箋受付取消要求', 'EPS-IF-304': '処方箋受付取消結果',
    'EPS-IF-305': '処方箋回収要求', 'EPS-IF-306': '処方箋回収結果',
    'EPS-IF-307': '調剤結果登録要求', 'EPS-IF-308': '調剤結果登録結果',
    'EPS-IF-309': '調剤結果取消要求', 'EPS-IF-310': '調剤結果取消結果',
    'EPS-IF-311': '調剤結果変更要求', 'EPS-IF-312': '調剤結果変更結果',
    'EPS-IF-313': '調剤済み電子処方箋リスト要求', 'EPS-IF-314': '調剤済み電子処方箋リスト',
    'EPS-IF-315': '重複投薬等チェック要求（確定前調剤結果情報）',
    'EPS-IF-316': '調剤済み電子処方箋要求（調剤結果ID）', 'EPS-IF-317': '調剤済み電子処方箋',
    'EPS-IF-318': '処方箋回収UNDO要求', 'EPS-IF-319': '処方箋回収UNDO結果',
    'EPS-IF-320': '処方箋ID検索要求（薬局）', 'EPS-IF-321': '処方箋ID検索結果（薬局）',
    'EPS-IF-322': '調剤結果ID検索要求', 'EPS-IF-323': '調剤結果ID検索結果',
    'EPS-IF-324': '保管調剤結果登録要求', 'EPS-IF-325': '保管調剤結果登録結果',
    'EPS-IF-328': '保管調剤結果取得（単件）要求', 'EPS-IF-329': '保管調剤結果取得（単件）結果',
    'EPS-IF-330': '保管調剤結果登録要求（調剤済み電子処方箋）', 'EPS-IF-331': '保管調剤結果登録結果（調剤済み電子処方箋）',
    'EPS-IF-401': '院内処方等登録要求', 'EPS-IF-402': '院内処方等登録結果',
    'EPS-IF-403': '院内処方等取消要求', 'EPS-IF-404': '院内処方等取消結果',
    'EPS-IF-405': '院内処方等変更要求', 'EPS-IF-406': '院内処方等変更結果',
    'EPS-IF-407': '院内処方等ID検索要求', 'EPS-IF-408': '院内処方等ID検索結果',
    'EPS-IF-409': '重複投薬等チェック要求（確定前院内処方等情報）',
}

CIS_NAMES = {
    'CIS-IF-101': '文書情報登録要求', 'CIS-IF-102': '文書情報登録結果',
    'CIS-IF-103': '文書情報取消要求', 'CIS-IF-104': '文書情報取消結果',
    'CIS-IF-107': '文書情報変更要求', 'CIS-IF-108': '文書情報変更結果',
    'CIS-IF-109': '文書情報状況照会要求', 'CIS-IF-110': '文書情報状況照会結果',
    'CIS-IF-111': '自施設宛文書情報一覧取得要求', 'CIS-IF-112': '自施設宛文書情報一覧取得結果',
    'CIS-IF-113': '文書情報取得要求', 'CIS-IF-114': '文書情報取得結果',
    'CIS-IF-115': '添付情報登録要求', 'CIS-IF-116': '添付情報登録結果',
    'CIS-IF-117': '添付情報取得要求', 'CIS-IF-118': '添付情報取得結果',
    'CIS-IF-119': '自施設宛文書情報閲覧同意登録結果',
    'CIS-IF-120': '健診文書登録要求', 'CIS-IF-121': '健診文書登録結果',
    'CIS-IF-122': '健診文書取消要求', 'CIS-IF-123': '健診文書取消結果',
    'CIS-IF-124': '健診文書変更要求', 'CIS-IF-125': '健診文書変更結果',
    'CIS-IF-126': '患者サマリー登録要求', 'CIS-IF-127': '患者サマリー登録結果',
    'CIS-IF-128': '患者サマリー取消要求', 'CIS-IF-129': '患者サマリー取消結果',
    'CIS-IF-130': '患者サマリー変更要求', 'CIS-IF-131': '患者サマリー変更結果',
    'CIS-IF-201': 'カルテ臨床情報登録要求', 'CIS-IF-202': 'カルテ臨床情報登録結果',
    'CIS-IF-203': 'カルテ臨床情報取消要求', 'CIS-IF-204': 'カルテ臨床情報取消結果',
    'CIS-IF-207': 'カルテ臨床情報変更要求', 'CIS-IF-208': 'カルテ臨床情報変更結果',
    'CIS-IF-301': 'マスタファイル取得要求', 'CIS-IF-302': 'マスタファイル取得結果',
}

NAME_MAP = {**OQS_NAMES, **EPS_NAMES, **CIS_NAMES}


# ============================================================
# PDF → テキスト変換
# ============================================================
def pdf_to_text(pdf_path: str) -> str:
    """pdftotext (poppler) でPDFをテキスト変換する"""
    result = subprocess.run(
        ['pdftotext', '-layout', pdf_path, '-'],
        capture_output=True, text=True, encoding='utf-8'
    )
    if result.returncode != 0:
        print(f"[ERROR] pdftotext failed: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    return result.stdout


# ============================================================
# XMLレイアウト別紙からIF情報を抽出
# ============================================================
def extract_tags_from_page(page_text: str) -> list[str]:
    """ページテキストから主要XMLタグを抽出する"""
    tags = []
    for line in page_text.split('\n'):
        m = re.match(
            r'^\s*(\d{2})\s+([\d\s]{2,20})\s{2,}(\S[^\t\n]{3,40}?)\s{3,}([A-Z][A-Za-z0-9]{3,})\s',
            line
        )
        if m:
            item_name = m.group(3).strip()
            tag_name = m.group(4).strip()
            if tag_name in ('XML', 'XmlMsg', 'MessageHeader', 'MessageBody', 'QualificationInfo'):
                continue
            entry = f"{item_name} [{tag_name}]"
            if entry not in tags:
                tags.append(entry)
    return tags[:8]


def extract_if_data_from_xml_layout(pdf_path: str) -> list[dict]:
    """
    別紙3-1 XMLレイアウトPDFから全IF情報を抽出する。
    Returns: list of {if_id, if_name, api_id, file_ex, prefix, tags}
    """
    print(f"[INFO] PDFテキスト抽出中: {pdf_path}")
    text = pdf_to_text(pdf_path)
    pages = text.split('\f')
    print(f"[INFO] 総ページ数: {len(pages)}")

    results = []
    seen_ids = set()

    for i, page in enumerate(pages):
        if 'API識別ID' not in page or 'XMLレイアウト' not in page:
            continue

        # IF_IDを検索
        m = re.search(r'((?:OQS|CIS|EPS|EMS|PMH)-IF-[\w]+)', page)
        if not m:
            continue
        if_id = m.group(1)

        # 重複スキップ（同じIDが複数ページにまたがる場合は最初だけ）
        if if_id in seen_ids:
            continue
        seen_ids.add(if_id)

        # IF名を抽出
        name_m = re.search(r'XMLレイアウト\s+([\S][^\n]{2,60}?)\s{3,}', page)
        if_name_raw = name_m.group(1).strip() if name_m else ''
        if_name_raw = re.sub(r'\s+', ' ', if_name_raw)

        # 既知マッピングで上書き、またはガベージ名を補正
        if if_id in NAME_MAP:
            if_name = NAME_MAP[if_id]
        elif if_name_raw.startswith('（') or if_name_raw.startswith('名の例') \
                or if_name_raw.startswith('外部インターフェイス名') or len(if_name_raw) < 3:
            if_name = if_id  # フォールバック
        else:
            if_name = if_name_raw

        # API識別IDを抽出
        api_m = re.search(r'((?:OQS|CIS|EPS|EMS|PMH)si\w+(?:req|res))', page, re.IGNORECASE)
        api_id = api_m.group(1) if api_m else ''

        # ファイル名例を抽出
        file_m = re.search(r'(\w{8,}(?:req|res)_[x\w]+\.(?:xml|zip|pdf))', page, re.IGNORECASE)
        file_ex = file_m.group(1) if file_m else ''

        prefix = if_id.split('-')[0]
        tags = extract_tags_from_page(page)

        results.append({
            'if_id': if_id,
            'if_name': if_name,
            'api_id': api_id,
            'file_ex': file_ex,
            'prefix': prefix,
            'tags': tags,
        })

    print(f"[INFO] 抽出完了: {len(results)}件")
    by_prefix = {}
    for r in results:
        by_prefix[r['prefix']] = by_prefix.get(r['prefix'], 0) + 1
    print(f"[INFO] 内訳: {by_prefix}")
    return results


# ============================================================
# HTMLへの注入
# ============================================================
def build_if_js(if_data: list[dict]) -> str:
    """IF_DATAのJavaScript定数文字列を生成する"""
    compact = [
        {
            'id': r['if_id'],
            'name': r['if_name'],
            'api': r['api_id'],
            'file': r['file_ex'],
            'sys': r['prefix'],
            'tags': r['tags'],
        }
        for r in if_data
    ]
    return 'const IF_DATA = ' + json.dumps(compact, ensure_ascii=False, separators=(',', ':')) + ';'


def inject_into_html(html_path: str, if_data: list[dict]) -> None:
    """
    既存HTMLのIF_DATAを新しいデータで置き換える。
    HTMLに 'const IF_DATA = ' が含まれていることが前提。
    """
    with open(html_path, 'r', encoding='utf-8') as f:
        html = f.read()

    new_js = build_if_js(if_data)

    # 既存の IF_DATA 定数を置換
    html_new = re.sub(
        r'const IF_DATA = \[.*?\];',
        new_js,
        html,
        flags=re.DOTALL
    )

    if html_new == html:
        print("[WARN] HTMLにIF_DATAが見つかりませんでした。注入をスキップします。")
        return

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_new)
    print(f"[INFO] HTMLを更新しました: {html_path}")


# ============================================================
# エントリーポイント
# ============================================================
def main():
    parser = argparse.ArgumentParser(
        description='外部I/F仕様書PDFからデータを抽出してJSON/HTMLに出力する'
    )
    parser.add_argument(
        '--xml-layout', required=True,
        help='別紙3-1 XMLレイアウトのPDFパス'
    )
    parser.add_argument(
        '--output', default='if_data.json',
        help='出力JSONファイルパス（デフォルト: if_data.json）'
    )
    parser.add_argument(
        '--inject-html',
        help='IF_DATAを注入するHTMLポータルファイルパス（省略可）'
    )
    args = parser.parse_args()

    # 抽出
    if_data = extract_if_data_from_xml_layout(args.xml_layout)

    # JSON出力
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(if_data, f, ensure_ascii=False, indent=2)
    print(f"[INFO] JSONを保存しました: {args.output}")

    # HTML注入（指定がある場合）
    if args.inject_html:
        if not os.path.exists(args.inject_html):
            print(f"[ERROR] HTMLファイルが見つかりません: {args.inject_html}", file=sys.stderr)
            sys.exit(1)
        inject_into_html(args.inject_html, if_data)


if __name__ == '__main__':
    main()
