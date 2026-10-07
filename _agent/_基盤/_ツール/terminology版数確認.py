"""terminology（jpfhir-terminology）の収載マスタ版数を確認し、DX機構（芳原さん）への回答表を出力する。

使い方:
    python terminology版数確認.py 2.2609.0            # 前月版（2.2608.0）と自動で比較
    python terminology版数確認.py 2.2609.0 2.2607.0   # 比較する版を指定

やること:
    1. https://jpfhir.jp/fhir/core/terminology/jpfhir-terminology.r4-<版>.tgz を今月版・比較版の両方ダウンロード
    2. 下の MAPPING に書いたファイルの `version` を読み、回答表の表記にそろえる
    3. 比較版から変わったものに ★（＝回答の赤字）を付けて Markdown 表で出力
    4. 回答対象外のCodeSystemで、比較版から増えた・消えた・版が変わったものも参考に出す（MAPPINGの見直し用）
       ※「版が変わった」に出ても回答表に無いもの（例：J-FAGY非食物）は回答に入れない。見るのは「増えた・消えた」

手順の正本: 定常業務マニュアル 最新版 Section 8-3
"""
import io
import json
import re
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

URL = "https://jpfhir.jp/fhir/core/terminology/jpfhir-terminology.r4-{v}.tgz"


def ym(v):  # 2026.9.15 / 2026.09 -> 202609
    y, m = v.split(".")[:2]
    return f"{y}{int(m):02d}"


def ymd(v):  # 2026.9.25 -> 20260925
    y, m, d = v.split(".")[:3]
    return f"{y}{int(m):02d}{int(d):02d}"


def major_minor(v):  # 5.18.0 -> 5.18
    return ".".join(v.split(".")[:2])


# 回答表の行（2026-10 回答の形）。files は package/ 内のファイル名。複数あるときは全部同じ版であることを確認する
MAPPING = [
    ("diseasekanricodes", "傷病名：傷病名", "標準病名履歴マスタ",
     ["CodeSystem-medis-codesystem-diseasekanricodes.json"], major_minor),
    ("modifiers", "傷病名：修飾語", "修飾語マスタ",
     ["CodeSystem-medis-codesystem-diseasenamecodes-modifiers.json"], major_minor),
    ("allergenYCM", "薬剤アレルギー等", "薬剤アレルギー用コードマスタ",
     ["CodeSystem-jp-jfagy-medication-allergenYCM-cs.json"], ym),
    ("allergenGCM", "薬剤アレルギー等", "剤形・規格・銘柄不明コードマスタ",
     ["CodeSystem-jp-jfagy-medication-allergenGCM-cs.json"], ym),
    ("jfagy-food-allergen", "その他アレルギー等", "J-FAGYアレルゲンコードマスタ",
     ["CodeSystem-jp-jfagy-food-allergen-cs.json"], ymd),
    ("jlac", "検査・感染症", "電子カルテ情報共有サービス対応JLACコード表(共有項目JLACコードマスタ)",
     ["CodeSystem-jp-clins-codesystem-JLAC10-corelabo-cs.json",
      "CodeSystem-jp-clins-codesystem-JLAC10-infectionlabo-cs.json",
      "CodeSystem-jp-clins-codesystem-JLAC11-corelabo-cs.json",
      "CodeSystem-jp-clins-codesystem-JLAC11-infectionlabo-cs.json"], ym),
    ("yj", "処方：医薬品", "個別医薬品コード(YJコード)リスト",
     ["CodeSystem-jp-medicationcode-yj-cs.json"], ym),
    ("（用法）", "処方：用法", "電子処方箋管理サービスの処方箋情報等を記録するための用法マスタ",
     ["CodeSystem-mhlw-medication-usage-jami-cs.json"], ym),
]
# パッケージに含まれないため、別の場所で確認するもの
OUTSIDE = [("健診文書", "電子カルテ情報共有サービス向け健診マスタ")]


def prev_version(v):  # 2.2609.0 -> 2.2608.0 / 2.2601.0 -> 2.2512.0
    a, b, c = v.split(".")
    yy, mm = int(b[:2]), int(b[2:])
    yy, mm = (yy - 1, 12) if mm == 1 else (yy, mm - 1)
    return f"{a}.{yy:02d}{mm:02d}.{c}"


def load(v, work):
    d = Path(work) / v
    if not (d / "package").exists():
        tgz = d.with_suffix(".tgz")
        d.mkdir(parents=True, exist_ok=True)
        print(f"ダウンロード中: {URL.format(v=v)}", file=sys.stderr)
        urllib.request.urlretrieve(URL.format(v=v), tgz)
        with tarfile.open(tgz) as tf:
            tf.extractall(d)
    vers = {}
    for f in (d / "package").glob("CodeSystem-*.json"):
        try:
            vers[f.name] = json.load(io.open(f, encoding="utf-8")).get("version")
        except Exception:
            vers[f.name] = None
    return vers


def answer(vers, files, fmt):
    raw = [vers.get(f) for f in files]
    if None in raw:
        missing = [f for f, r in zip(files, raw) if r is None]
        return None, f"⚠️ファイルなし: {', '.join(missing)}"
    shown = {fmt(r) for r in raw}
    if len(shown) > 1:
        return None, f"⚠️ファイル間で版が不一致: {raw}"
    return shown.pop(), " / ".join(sorted(set(raw)))


def main():
    if len(sys.argv) < 2 or not re.fullmatch(r"\d+\.\d{4}\.\d+", sys.argv[1]):
        sys.exit(__doc__)
    cur = sys.argv[1]
    prev = sys.argv[2] if len(sys.argv) > 2 else prev_version(cur)
    work = Path(tempfile.gettempdir()) / "terminology_check"
    vc, vp = load(cur, work), load(prev, work)

    print(f"## terminology Ver. {cur} 収載マスタ版数（比較：Ver. {prev}、★＝更新＝回答の赤字）\n")
    print("| 情報 | 名称 | 版 | 更新 | 根拠（ファイルのversion） |")
    print("|---|---|---|---|---|")
    for key, info, name, files, fmt in MAPPING:
        a, note = answer(vc, files, fmt)
        b, _ = answer(vp, files, fmt)
        mark = "" if a is None else ("★" if a != b else "")
        print(f"| {info} | {name} | {a or '要確認'} | {mark} | {note} |")
    for info, name in OUTSIDE:
        print(f"| {info} | {name} | 要確認 |  | パッケージに含まれない → 毎月個別に確認する |")

    used = {f for *_, files, _ in MAPPING for f in files}
    added = sorted(set(vc) - set(vp))
    removed = sorted(set(vp) - set(vc))
    changed = sorted(f for f in set(vc) & set(vp) if f not in used and vc[f] != vp[f])
    print("\n### 参考：回答対象外のCodeSystemの変化（MAPPINGの見直し用）")
    print(f"- 増えたファイル: {added or 'なし'}")
    print(f"- 消えたファイル: {removed or 'なし'}")
    print(f"- 版が変わったファイル: {[f'{f}（{vp[f]}→{vc[f]}）' for f in changed] or 'なし'}")


if __name__ == "__main__":
    main()
