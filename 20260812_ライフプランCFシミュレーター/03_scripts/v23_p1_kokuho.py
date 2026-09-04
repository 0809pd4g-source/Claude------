# -*- coding: utf-8 -*-
r"""v23 patch C：P1-1（概算警告がAND条件で消える）＋P1-2（新宿区・令和8年度の整合セットへ）。

**P1-1 何が起きていたか**

    && !paramConfirmed(P, "tax.kokuhoMedRate")
    && !paramConfirmed(P, "tax.kokuhoMedPer")

AND なので、**どちらか1つを確認しただけで警告が消える。**
実測：何も確認しない→警告あり／医療分所得割だけ→**なし**／医療分均等割だけ→**なし**／
介護分だけ→あり。支援分・介護分・子ども支援分・上限・平等割・軽減基準が仮のままでも消える。

★2項目のANDを「全部仮のままか」の代わりに使っていた。**代用した条件は、いつか外れる。**

**直し方（2つの意味を分ける）**
  - `KOKUHO_REF.sourceVerified` … 参照セットを一次資料で確かめたか（作り手の話）
  - `P.tax.kokuhoMunicipalityConfirmed` … **利用者が自分の自治体・年度として確かめたか**
一次資料で検証済みでも、利用者が新宿区在住とは限らない。**後者が立つまで警告は消さない。**

**P1-2 新宿区・令和8年度へ**
v22は「複数年度・複数自治体の混在」と正直に名乗るところまでだった。
今回、**一次資料（新宿区の公式ページ）を実際に取得して全値を確認**した。

  医療 7.51% / 47,600円 / 670,000円
  後期支援 2.80% / 17,600円 / 260,000円
  介護 2.43% / 17,800円 / 170,000円（40〜64歳）
  子ども・子育て支援 0.27% / 1,873円（18歳以上）/ 30,000円

★v22の既定（医療8.69%・47,300円、支援16,800円、介護2.44%・16,600円）は
  どれも新宿区・令和8年度の値ではなかった。混在という自己申告は正しかった。
"""
import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parent.parent
P = ROOT / "02_output" / "20260831_ライフプランCFシミュレーター汎用版_v23.html"
t = P.read_text(encoding="utf-8")
ng = []


def sub(old, new, label, count=1):
    global t
    c = t.count(old)
    if c == count:
        t = t.replace(old, new, count)
    else:
        ng.append(f"{label} ({c}件/期待{count})")


# ---- 1. KOKUHO_REF を実在のセットにする ----
sub('''const KOKUHO_REF = {
  label:"複数年度・複数自治体の混在した仮の値",
  detail:"東京都区部のいくつかの年度の値を寄せ集めたもので、"
       + "特定の自治体・特定の年度のセットではありません。",
  verified:false,
  method:"2方式（所得割＋均等割）。平等割のある自治体（3方式・4方式）では不足します。",
};''',
    '''const KOKUHO_REF = {
  municipality:"東京都新宿区",
  fiscalYear:"令和8年度",
  label:"東京都新宿区・令和8年度の参考値",
  detail:"新宿区の公式ページで確認した、単一自治体・単一年度の一貫したセットです。"
       + "お住まいが新宿区でない場合は、この値のままでは合いません。",
  method:"2方式（所得割＋均等割）。平等割のある自治体（3方式・4方式）では不足します。",
  /** 作り手が一次資料で値を確かめたか。**利用者の自治体と一致するかとは別。** */
  sourceVerified:true,
  checkedOn:"2026-08-31",
  src:[
    "https://www.city.shinjuku.lg.jp/hoken/hoken01_001028.html",
    "https://www.city.shinjuku.lg.jp/hoken/hoken01_002030.html",
    "https://www.city.shinjuku.lg.jp/hoken/hoken01_002029.html",
  ],
};''',
    "KOKUHO_REF を新宿区・令和8年度に")

# ---- 2. 既定値を新宿区・令和8年度へ ----
for old, new, lbl in [
    ("kokuhoMedRate:8.69,           // 医療分 所得割(%)",
     "kokuhoMedRate:7.51,           // 医療分 所得割(%)", "医療 所得割"),
    ("kokuhoMedPer:47300,           // 医療分 均等割（1人あたり・円/年）",
     "kokuhoMedPer:47600,           // 医療分 均等割（1人あたり・円/年）", "医療 均等割"),
    ("kokuhoSupPer:16800,           // 同 均等割",
     "kokuhoSupPer:17600,           // 同 均等割", "支援 均等割"),
    ("kokuhoCareRate:2.44,          // 介護分 所得割(%)（40〜64歳）",
     "kokuhoCareRate:2.43,          // 介護分 所得割(%)（40〜64歳）", "介護 所得割"),
    ("kokuhoCarePer:16600,          // 同 均等割",
     "kokuhoCarePer:17800,          // 同 均等割", "介護 均等割"),
]:
    sub(old, new, lbl)

# ---- 3. 自治体確認のフラグを params に足す ----
sub('''    kokuhoPrevIncH:0,             // あなたの前年の所得（円）''',
    '''    /* ★「作り手が一次資料で確かめた」と「利用者の自治体・年度として正しい」は別。
       既定は新宿区・令和8年度なので、それ以外の人には合わない。
       ここが true になるまで「概算です」の警告を消さない（v23 P1-1）。 */
    kokuhoMunicipalityConfirmed:false,
    kokuhoPrevIncH:0,             // あなたの前年の所得（円）''',
    "自治体確認フラグを追加")

# ---- 4. 警告の条件を直す ----
sub('''  if(!KOKUHO_REF.verified
     && (workTypeOf(P, "h") === "self"
         || (P.family.hasSpouse && workTypeOf(P, "w") === "self"))
     && !paramConfirmed(P, "tax.kokuhoMedRate")
     && !paramConfirmed(P, "tax.kokuhoMedPer"))
    add("warn", "国民健康保険の料率が仮の値のままです。この結論は概算です。",
      `既定は${KOKUHO_REF.label}で、${KOKUHO_REF.detail}`
      + `${KOKUHO_REF.method}`
      + "「税・社会保険」の設定で、お住まいの自治体の料率に入れ替えてください。"
      + "自営業の年は、ここが結果をいちばん大きく動かします。");''',
    '''  /* ★v22は「医療分の所得割 AND 均等割が未確認なら警告」だった。
       ANDなので**どちらか1つを確認しただけで消える**（実測で確認）。
       支援分・介護分・子ども支援分・上限・軽減基準が仮のままでも消えてしまう。
       2項目の確認状態を「全部仮のままか」の代用にしていたのが誤り。
       **利用者が自治体・年度として確かめたか**という1つの旗で判定する（v23 P1-1）。 */
  if(!P.tax.kokuhoMunicipalityConfirmed
     && (workTypeOf(P, "h") === "self"
         || (P.family.hasSpouse && workTypeOf(P, "w") === "self")))
    add("warn", "国民健康保険の料率が、お住まいの自治体のものか未確認です。この結論は概算です。",
      `既定は${KOKUHO_REF.label}（${KOKUHO_REF.checkedOn}に公式ページで確認）です。`
      + `${KOKUHO_REF.detail}${KOKUHO_REF.method}`
      + "「税・社会保険」の設定で、お住まいの自治体・年度の料率に入れ替え、"
      + "「自治体と年度を確認した」にチェックを入れてください。"
      + "自営業の年は、ここが結果をいちばん大きく動かします。");''',
    "概算警告の条件を1つの旗に")

# ---- 5. 画面に確認チェックを置く ----
sub('''          + chkField("軽減を計算に入れる", "tax.kokuhoReduceOn")''',
    '''          + chkField("お住まいの自治体・年度の料率を確認した",
                     "tax.kokuhoMunicipalityConfirmed",
                     "ここにチェックを入れるまで、結果に「概算です」と表示します")
          + chkField("軽減を計算に入れる", "tax.kokuhoReduceOn")''',
    "自治体確認のチェック欄")

# ---- 6. 説明文を新宿区セットに合わせる ----
sub('''       ★国民健康保険の料率と均等割は自治体ごとに毎年決まり、差が非常に大きい。
         **下の既定は複数年度・複数自治体の混在した仮の値**で、
         単一の自治体・単一の年度として整合していない（`KOKUHO_REF`）。
         推奨値でも全国の平均でもない。
         v21まで「東京23区の令和7年度の水準に近い置き」と書いていたが、
         **その説明は実態と違っていた**（外部レビューで判明）。''',
    '''       ★国民健康保険の料率と均等割は自治体ごとに毎年決まり、差が非常に大きい。
         **下の既定は東京都新宿区・令和8年度の実際の値**（`KOKUHO_REF` に出典）。
         2026-08-31に公式ページで全値を確認した。
         **推奨値でも全国の平均でもなく、新宿区以外では合わない。**
         v22までは複数年度・複数自治体の混在だった（外部レビューで指摘され、今回そろえた）。''',
    "既定値のコメント")

sub('''    /* ★令和8年度から、国保に「子ども・子育て支援金分」が加わる（4区分目）。
       東京都区部の例。**上の医療・支援・介護とは年度がそろっていない。**
       自治体差が大きいので利用者が変えられる。 */''',
    '''    /* ★令和8年度から、国保に「子ども・子育て支援金分」が加わる（4区分目）。
       新宿区・令和8年度の値。自治体差が大きいので利用者が変えられる。 */''',
    "子ども支援分のコメント")

sub('''    /* ★令和8年度に67万円としている自治体がある（板橋区など）。
       自治体差があるので、既定は67万円にしたうえで画面で確認をうながす。 */''',
    '''    /* ★新宿区・令和8年度の医療分 賦課限度額。自治体差があるので画面で確認をうながす。 */''',
    "医療上限のコメント")

sub('''          + '既定は<b>' + esc(KOKUHO_REF.label) + '</b>で、'
          + esc(KOKUHO_REF.detail)
          + esc(KOKUHO_REF.method)
          + '「◯◯市 国民健康保険料 料率」で調べて、下の欄を入れ替えてください。<br>' ''' .rstrip(),
    '''          + '既定は<b>' + esc(KOKUHO_REF.label) + '</b>（'
          + esc(KOKUHO_REF.checkedOn) + 'に公式ページで確認）です。'
          + esc(KOKUHO_REF.detail)
          + esc(KOKUHO_REF.method)
          + '「◯◯市 国民健康保険料 料率」で調べて、下の欄を入れ替えてください。<br>' ''' .rstrip(),
    "自営業の注意書き")

if ng:
    print("NG:", " / ".join(ng))
    sys.exit(1)
P.write_text(t, encoding="utf-8")
print("OK v23 patch C（概算警告の条件／新宿区・令和8年度セット）")
