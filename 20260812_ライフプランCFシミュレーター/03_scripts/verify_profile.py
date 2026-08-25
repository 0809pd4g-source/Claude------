# -*- coding: utf-8 -*-
"""参照PDFの世帯を、汎用版のエンジンに読み込ませるための共通処理。

なぜ要るか
----------
成果物は2系統ある。

  個人版 … 参照PDFの世帯（p1〜p4のプリセット・収入・生活費など）を本体に持つ。
  汎用版 … 誰の家計でも使えるようにするため、**個人データを一切持たない。**

そのままでは汎用版のエンジンをPDFと突き合わせられない。
そこでPDFの世帯だけを 04_reference/verify_profile.json に外出しし、
汎用版を照合するときは setProfile() で流し込む。

  ・配布するHTMLには個人データが入らない（汎用版の方針を守れる）
  ・それでも汎用版のエンジンがPDFを再現できることを確かめられる

このJSONは検証専用で、01_input と同じ「配布しないもの」の扱い。
作り直すときは 03_scripts/make_verify_profile.py を使う。
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROFILE = ROOT / "04_reference" / "verify_profile.json"


def is_generic(engine_js):
    """そのエンジンが汎用版か（プロフィール層とサンプル世帯を持つか）"""
    return "function setProfile(" in engine_js and "SAMPLE_PROFILES" in engine_js


def with_pdf_profile(engine_js):
    """汎用版なら、参照PDFの世帯を読み込む1行を足して返す。個人版はそのまま返す。"""
    if not is_generic(engine_js):
        return engine_js
    if not PROFILE.exists():
        raise SystemExit(
            f"汎用版を参照PDFと照合するには {PROFILE} が必要です。\n"
            f"次で作れます:  python 03_scripts/make_verify_profile.py")
    return engine_js + "\nsetProfile(" + PROFILE.read_text(encoding="utf-8") + ");\n"
