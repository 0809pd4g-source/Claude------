#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
エジプト・ギリシャ新婚旅行 フォトブックデータ
============================================
写真を 01_input/photos/ に入れてから、
各ページの "image" フィールドにファイル名を書いて実行する。

実行方法:
    cd C:/Users/masato.nakazawa/Downloads/Claudeプロジェクト/20260901_新婚旅行しおり
    python 03_scripts/album_egypt_greece.py

写真ファイル命名例:
    01_input/photos/day2_gem.jpg
    01_input/photos/day3_pyramid.jpg
    ...
    （どんなファイル名・形式でも可。見つからない場合はプレースホルダーを表示）

ページ構成を変えるには:
    - type: "full" / "grid_2" / "grid_4" / "divider" / "blank"
    - 順番を入れ替えたり、ページを追加・削除するだけでOK
    - "image" パスはプロジェクトルートからの相対パス
"""
from pathlib import Path

OUTPUT_PATH = Path("C:/Users/masato.nakazawa/Downloads/Claudeプロジェクト/"
                   "20260901_新婚旅行しおり/02_output/"
                   "20260929_エジプトギリシャフォトブック_v1.pdf")

# ══════════════════════════════════════════════════════
# ALBUM CONFIG
# ══════════════════════════════════════════════════════
ALBUM = {

    # ── 表紙 ─────────────────────────────────────
    "meta": {
        "title":    "Egypt  x  Greece",   # ASCII 推奨（日本語フォント次第）
        "subtitle": "Honeymoon 2026",
        "dates":    "September 13 - 27, 2026",
        "theme":    "a",
        # 表紙に写真を入れる場合はコメントを外す:
        # "image": "01_input/photos/cover.jpg",
    },

    # ── ページ定義 ────────────────────────────────
    # 写真を入れ替える手順:
    # 1. 01_input/photos/ にファイルを置く
    # 2. "image": のパスを書き換える
    # 3. python 03_scripts/album_egypt_greece.py を再実行
    "pages": [

        # ─────────────────────────────────────────
        # EGYPT
        # ─────────────────────────────────────────
        {"type": "divider",
         "title": "EGYPT",
         "subtitle": "September 14 - 20, 2026",
         "theme": "a"},

        # DAY 2: カイロ着・GEM・ピラミッド初見
        {"type": "full",
         "image": "01_input/photos/day2_gem.jpg",
         "caption": "Grand Egyptian Museum (GEM)"},

        {"type": "full",
         "image": "01_input/photos/day2_pyramid_sunset.jpg",
         "caption": "Giza Pyramids at sunset"},

        # DAY 3: ピラミッド1日ツアー
        {"type": "grid_2",
         "images": [
             {"image": "01_input/photos/day3_sphinx.jpg",   "caption": "The Great Sphinx"},
             {"image": "01_input/photos/day3_sakkara.jpg",  "caption": "Step Pyramid of Saqqara"},
         ]},

        # ─────────────────────────────────────────
        # WHITE DESERT
        # ─────────────────────────────────────────
        {"type": "divider",
         "title": "White Desert",
         "subtitle": "September 16 - 17, 2026",
         "theme": "a"},

        {"type": "full",
         "image": "01_input/photos/day4_desert_sunset.jpg",
         "caption": "White Desert at sunset"},

        {"type": "full",
         "image": "01_input/photos/day5_desert_sunrise.jpg",
         "caption": "Dawn in the White Desert"},

        {"type": "grid_2",
         "images": [
             {"image": "01_input/photos/day4_camp.jpg",  "caption": "Private desert camp"},
             {"image": "01_input/photos/day4_stars.jpg", "caption": "Starry night sky"},
         ]},

        # ─────────────────────────────────────────
        # LUXOR
        # ─────────────────────────────────────────
        {"type": "divider",
         "title": "Luxor",
         "subtitle": "September 18 - 20, 2026",
         "theme": "a"},

        {"type": "full",
         "image": "01_input/photos/day6_luxor_temple_night.jpg",
         "caption": "Luxor Temple at night"},

        {"type": "grid_4",
         "images": [
             {"image": "01_input/photos/day7_valley.jpg",      "caption": "Valley of the Kings"},
             {"image": "01_input/photos/day7_hatshepsut.jpg",  "caption": "Temple of Hatshepsut"},
             {"image": "01_input/photos/day8_karnak.jpg",      "caption": "Great Hypostyle Hall"},
             {"image": "01_input/photos/day8_luxor_dawn.jpg",  "caption": "Luxor Temple at dawn"},
         ]},

        # ─────────────────────────────────────────
        # GREECE
        # ─────────────────────────────────────────
        {"type": "divider",
         "title": "GREECE",
         "subtitle": "September 21 - 26, 2026",
         "theme": "b"},

        # ─────────────────────────────────────────
        # SANTORINI
        # ─────────────────────────────────────────
        {"type": "divider",
         "title": "Santorini",
         "subtitle": "September 21 - 24, 2026",
         "theme": "b"},

        {"type": "full",
         "image": "01_input/photos/day9_oia_arrival.jpg",
         "caption": "Arriving in Oia, Santorini"},

        {"type": "full",
         "image": "01_input/photos/day10_oia_sunset.jpg",
         "caption": "The famous Oia sunset"},

        # ブライダルフォト（見開き感で2ページ連続）
        {"type": "full",
         "image": "01_input/photos/day11_bridal_1.jpg",
         "caption": "Bridal photo shoot — Oia"},

        {"type": "full",
         "image": "01_input/photos/day11_bridal_2.jpg",
         "caption": "Blue dome church"},

        {"type": "grid_2",
         "images": [
             {"image": "01_input/photos/day11_caldera.jpg", "caption": "Caldera view"},
             {"image": "01_input/photos/day12_winery.jpg",  "caption": "Santo Wines winery"},
         ]},

        # ─────────────────────────────────────────
        # ATHENS
        # ─────────────────────────────────────────
        {"type": "divider",
         "title": "Athens",
         "subtitle": "September 25 - 26, 2026",
         "theme": "b"},

        {"type": "full",
         "image": "01_input/photos/day13_acropolis.jpg",
         "caption": "Acropolis — Parthenon"},

        {"type": "grid_2",
         "images": [
             {"image": "01_input/photos/day13_parthenon.jpg",  "caption": "Parthenon columns"},
             {"image": "01_input/photos/day13_areopagus.jpg",  "caption": "View from Areopagus Hill"},
         ]},

        # ─────────────────────────────────────────
        # エンディング
        # ─────────────────────────────────────────
        {"type": "divider",
         "title": "Thank you for the memories",
         "subtitle": "September 2026",
         "theme": "b"},

        {"type": "blank"},  # 裏表紙（白紙）
    ],
}

# ══════════════════════════════════════════════════════
# 実行
# ══════════════════════════════════════════════════════
if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from build_photobook import build
    build(ALBUM["meta"], ALBUM["pages"], OUTPUT_PATH)
