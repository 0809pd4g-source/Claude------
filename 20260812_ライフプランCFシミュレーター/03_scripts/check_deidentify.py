# -*- coding: utf-8 -*-
"""匿名化の検査。**汎用版に個人・物件が特定できるものが残っていないか**を機械的に見る。

なぜ必要か（2026-08-25にChatGPT版V59を査読して分かったこと）：
  V59は禁止語リスト（西小岩・平井6丁目・板橋区栄町など）を0件にしていたが、
  **同じ物件を特定できる駅名・路線名が残っていた**
  （`station:'東武東上線 大山駅・中板橋駅…都営三田線 板橋区役所前駅…'`）。
  3物件のうち2件だけ架空名に置換され、**同じレコード内で架空名と実名が混在**していた。
  価格・築年月・面積・私道持分も残っており、**名前だけ架空にした状態**だった。

  **禁止語を0件にすることと、匿名化することは別である。**
  検査の条件を「特定の語が無いこと」ではなく
  **「実在の地名・駅名・路線名・行政区名・地番・掲載URL・実測値が無いこと」**にする。

★`innerText` だけを見てはいけない（V57の教訓）。
  `<option>` の文字は `innerText` に出ないため、選択肢に残った語を見逃す。
  このスクリプトは**ソース全体**を見るので、その穴は無い。

★官公庁のURLと、制度の参考としての地名（「東京都は2025年9月から無償」など）は
  汎用版に必要なものなので、除外リストで通す。

使い方:
  python 03_scripts/check_deidentify.py                    # 汎用版の最新
  python 03_scripts/check_deidentify.py 02_output/xxx.html  # 対象を指定
  ※個人版は個人データを持つのが正しいので、既定では汎用版だけを見る。
"""
import io
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def pick_html():
    if len(sys.argv) > 1:
        p = Path(sys.argv[1])
        return p if p.is_absolute() else (ROOT / p)
    cands = [p for p in sorted((ROOT / "02_output").glob("*_v*.html")) if "汎用版" in p.name]
    if not cands:
        raise SystemExit("汎用版のHTMLが 02_output に見つかりません")
    # 版番号の大きいものを選ぶ（名前順だと v10 が v9 より前に来るため）
    def ver(p):
        m = re.search(r"_v(\d+)\.html$", p.name)
        return int(m.group(1)) if m else 0
    return max(cands, key=ver)


# ---- 検査項目 ----
# (ラベル, 正規表現, 説明)
CHECKS = [
    ("旧物件名・旧呼称",
     r"西小岩|平井\s*6\s*丁目|板橋区栄町|奥様|妻確認|妻年収|妻向け",
     "個人版に由来する固有名詞・呼称"),

    ("実在の鉄道路線名",
     r"東武東上線|東武伊勢崎線|都営三田線|都営新宿線|京成[^\s]{0,4}線|"
     r"JR総武線|中央総武線|東京メトロ[^\s]{0,6}線",
     "路線名が分かると物件の場所が絞れる"),

    ("実在の駅名（丁目・徒歩と同居するもの）",
     r"[一-龥ぁ-んァ-ヶ]{2,6}駅\s*(徒歩|・|／)",
     "駅名＋徒歩の組み合わせは物件の特定につながる"),

    ("番地・丁目",
     r"[0-9０-９]+\s*丁目|[0-9０-９]+番[0-9０-９]+号",
     "住所の一部"),

    ("実測の面積・持分",
     r"landArea\s*:\s*[0-9]+\.[0-9]|floorArea\s*:\s*[0-9]+\.[0-9]|"
     r"私道持分\s*(約)?\s*[0-9]+\.[0-9]|持分\s*[0-9]+\.[0-9]+\s*㎡",
     "小数点付きの面積・持分は実在物件の登記値"),

    ("掲載サイトのURL",
     r"https?://[^\s\"'<>]*"
     r"(suumo|athome|homes\.co\.jp|rehouse|nomu|mitsui|tokyu-|開発|bukken)"
     r"[^\s\"'<>]*",
     "物件の掲載ページ"),

    ("築年月（年+月の具体値）",
     r"built\s*:\s*['\"][0-9]{4}年[0-9]{1,2}月",
     "築年月は面積と組み合わせると物件が絞れる"),
]

# 官公庁ドメインは出典として必要なので通す
GOV = re.compile(r"https?://[^\s\"'<>]*\.(go\.jp|lg\.jp)")

# 制度の参考として地名を出すのは汎用版に必要（出典つきで書いている箇所）
ALLOW_CONTEXT = [
    "無償", "出典", "助成", "自治体", "地震保険", "地域", "23区",
    "重要事項説明書", "登記事項証明書", "確認すること",
]


def context(text, m, width=46):
    a = max(0, m.start() - width)
    b = min(len(text), m.end() + width)
    return text[a:b].replace("\n", " ").replace("\r", " ")


def main():
    path = pick_html()
    src = path.read_text(encoding="utf-8", errors="replace")
    print(f"匿名化の検査: {path.name}")
    print("=" * 86)

    total = 0
    for label, pat, why in CHECKS:
        hits = []
        for m in re.finditer(pat, src):
            ctx = context(src, m)
            # 官公庁URLは通す
            if GOV.search(m.group(0)):
                continue
            # 制度の参考として書いている箇所は通す
            if any(w in ctx for w in ALLOW_CONTEXT):
                continue
            hits.append((m.group(0)[:44], ctx))
        if hits:
            total += len(hits)
            print(f"\nNG {label}  {len(hits)}件   （{why}）")
            for g, ctx in hits[:6]:
                print(f"    「{g}」")
                print(f"      …{ctx.strip()[:96]}…")
            if len(hits) > 6:
                print(f"    ほか {len(hits)-6}件")
        else:
            print(f"OK {label}")

    print("\n" + "=" * 86)
    if total == 0:
        print("結果: 個人・物件を特定できるものは見つかりませんでした")
        return 0
    print(f"結果: {total}件見つかりました。汎用版には残さないこと")
    print("※ 制度の参考として地名を出す場合は、出典を添えてこのスクリプトの")
    print("   ALLOW_CONTEXT に通す語（「無償」「出典」等）を文中に含めること")
    return 1


if __name__ == "__main__":
    sys.exit(main())
