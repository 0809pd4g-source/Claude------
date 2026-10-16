"""
外部由来の XML（ユーザーの PPTX の中身・SVG）を解析するための共通パーサー。

実体（ENTITY）の展開・DTD の読み込み・ネットワーク取得・巨大ツリーを明示的に無効にする
（XXE によるローカルファイルの読み出しや、実体展開による DoS を防ぐ）。
"""

from lxml import etree

PARSER = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False, huge_tree=False)


def fromstring(data):
    return etree.fromstring(data, PARSER)


def parse(source):
    return etree.parse(source, PARSER)
