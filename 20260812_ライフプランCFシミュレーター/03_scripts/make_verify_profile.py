# -*- coding: utf-8 -*-
"""参照PDFの世帯を、汎用版で読み込めるプロフィールとして書き出す。

汎用版には個人データを一切入れない方針なので、参照PDFの世帯は
04_reference/verify_profile.json に外出しし、照合のときだけ読み込む。
中身は個人版のエンジンから `applyPdfSavings(defaults("p1".."p4"))` を取り出したもの。

使い方:  python 03_scripts/make_verify_profile.py [個人版のHTML]

引数がなければ、02_output のいちばん新しい個人版（汎用版を除く）を使う。
個人版の前提が変わったときは、これを流し直す。
"""
import io
import json
import re
import sys
from pathlib import Path

import dukpy

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "04_reference" / "verify_profile.json"
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

KEYS = ["p1", "p2", "p3", "p4", "rent"]


def pick_src():
    if len(sys.argv) > 1:
        p = Path(sys.argv[1])
        return p if p.is_absolute() else (ROOT / p)
    cands = [p for p in sorted((ROOT / "02_output").glob("*_v*.html"))
             if "汎用版" not in p.name]
    if not cands:
        raise SystemExit("個人版のHTMLが 02_output に見つかりません")
    return cands[-1]


SRC = pick_src()
js = re.search(r"<script>(.*?)</script>", SRC.read_text(encoding="utf-8"), re.S).group(1)
js = 'var window={addEventListener:function(){},alert:function(){},print:function(){}};' + js
eng = js[:js.rfind("/* ", 0, js.find("   状態"))]

dump = json.loads(dukpy.evaljs(eng + """
var out = {params:{}, presets:{}};
/* 参照PDFは「今後は積み立てない」前提なので、積立を0に戻した状態を正とする。 */
out.params = applyPdfSavings(defaults("p1"));
%s.forEach(function(k){
  var p = applyPdfSavings(defaults(k));
  out.presets[k] = {short:PRESETS[k].short, label:PRESETS[k].label, note:PRESETS[k].note,
                    house:p.house, estate:p.estate};
});
JSON.stringify(out);
""" % json.dumps(KEYS)))

params = dump["params"]

# 収入テーブルは選択肢から作り直させない。汎用版の keep／raise10 は
# 「いまの年収から割合で組み立てる」ので、PDFの実額テーブルとは一致しない。
# "custom" にすると defaults() が上書きしない。
params["meta"]["hIncome"] = "custom"
params["meta"]["wScenario"] = "custom"
# 地域は「自分で調べて入れる」（keep:true なので保育料を上書きしない）
params["meta"]["region"] = "manual"
params["meta"]["preset"] = "p1"
params["meta"]["planName"] = "参照PDF ① 7,500万円（検証用）"
params["meta"]["memo"] = "検証専用のプロフィール。参照PDFの世帯を再現する。"

profile = {
    "name": "参照PDFの世帯（検証専用）",
    "note": ("参照PDF 4本の前提を再現するプロフィール。"
             "汎用版のエンジンをPDFと突き合わせるためだけに使う。"
             "配布するHTMLには含めない。"),
    "source": SRC.name,
    "params": params,
    "presets": dump["presets"],
}

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(profile, ensure_ascii=False, indent=1), encoding="utf-8")

f = params["family"]
print(f"元にした個人版: {SRC.name}")
print(f"書き出し      : {OUT.relative_to(ROOT)}  {OUT.stat().st_size:,} バイト")
print(f"住宅プラン    : {list(profile['presets'].keys())}")
print(f"世帯          : あなた{f['ageH']}歳 / パートナー{f['ageW']}歳 / "
      f"子{len(f['children'])}人 {[c['birthYear'] for c in f['children']]}")
print(f"基準年 {params['meta']['baseYear']} / 最終年齢 {params['meta']['endAge']} / "
      f"物価 {params['econ']['inflation']}% / 基礎控除 {params['tax']['basicIT']:,}円")
print(f"積立が0に戻っているか: NISA月額 {params['saving']['nisaMonthlyH']} / "
      f"DC残高 {params['saving']['dcBalanceH']}")
