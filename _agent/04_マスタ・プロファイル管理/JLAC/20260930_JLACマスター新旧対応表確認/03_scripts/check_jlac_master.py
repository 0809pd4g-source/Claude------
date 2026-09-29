"""
JLAC マスター新旧対応表 ダブルチェックスクリプト
------------------------------------------------------
入力:
  FILE_1: ① JLAC新旧コード対応表_v1.0.2.xlsx（電子カルテ情報共有サービスからDL）
  FILE_2: ② jlac11_3_1.1b.xlsx（日本臨床検査医学会からDL）

チェック内容:
  ①「変更区分」=「削除」かつ「削除理由」に「販売終了」を含む行について、
  ②「更新区分」が「S」（削除）またはコードが存在しないかを確認する。
  該当しない（=②に存在かつS以外）場合は復活している可能性として要確認フラグを立てる。

  内訳:
    - 削除理由=「販売終了」: 1935件
    - 削除理由=「販売終了(付け替え先見直し中)」: 535件（元の依頼対象）
    - 合計: 2470件

出力:
  02_output/確認結果_YYYYMMDD.xlsx
    - ★要確認シート: ②で廃止されていない（復活疑い）の一覧
    - 全件シート: 全対象行の判定結果
"""

import pandas as pd
from pathlib import Path
from datetime import date

BASE = Path(__file__).parent.parent

FILE_1  = BASE / "01_input" / "JLAC新旧コード対応表_v1.0.2.xlsx"
FILE_2  = BASE / "01_input" / "jlac11_3_1.1b.xlsx"
OUTPUT  = BASE / "02_output" / f"確認結果_{date.today().strftime('%Y%m%d')}.xlsx"
OUTPUT.parent.mkdir(exist_ok=True)

# ① 対応表の設定
SHEET_1         = "対応表"
HEADER_1        = 2          # 3行目（0始まり）がヘッダー
COL_CODE_1      = "JLAC11コード"
COL_CHANGE_TYPE = "変更区分"
COL_DEL_REASON  = "削除理由"
CHANGE_TYPE_DEL = "削除"     # 変更区分=削除を対象
DEL_REASON_KW   = "販売終了" # 削除理由に「販売終了」を含む行を対象

# ② JLACマスタの設定
SHEET_2    = "JLAC11_17桁コードリスト"
HEADER_2   = 0
COL_CODE_2 = "JLAC11-17桁コード"
COL_AQ     = "更新区分（T：登録、S：削除、H：変更）"
AQ_OK      = "S"        # これが廃止済みを示す値

def normalize(code: str) -> str:
    """ハイフンを除去してコードを正規化（①と②の形式差を吸収）"""
    return str(code).replace("-", "").strip()


def main():
    print("ファイル読み込み中...")
    df1 = pd.read_excel(FILE_1, sheet_name=SHEET_1, header=HEADER_1, dtype=str).fillna("")
    df2 = pd.read_excel(FILE_2, sheet_name=SHEET_2, header=HEADER_2, dtype=str).fillna("")

    # 対象行を抽出（変更区分=削除 かつ 削除理由に「販売終了」を含む）
    mask = (
        (df1[COL_CHANGE_TYPE].str.strip() == CHANGE_TYPE_DEL) &
        (df1[COL_DEL_REASON].str.contains(DEL_REASON_KW, na=False))
    )
    target = df1[mask].copy()
    n_mitaoshi = (target[COL_DEL_REASON].str.contains("付け替え先見直し中", na=False)).sum()
    print(f"  ① 対象行数: {len(target)} 件（うち付け替え先見直し中: {n_mitaoshi} 件）")

    # ② コード正規化→更新区分のマップ
    df2["_code_norm"] = df2[COL_CODE_2].apply(normalize)
    code_to_aq = dict(zip(df2["_code_norm"], df2[COL_AQ].str.strip()))

    # チェック
    rows = []
    for _, r in target.iterrows():
        code_raw = r[COL_CODE_1].strip()
        code_norm = normalize(code_raw)
        aq = code_to_aq.get(code_norm)          # None = ②に存在しない

        if aq is None:
            status = "OK（②に存在しない＝削除済み）"
            flag = ""
        elif aq == AQ_OK:
            status = f"OK（更新区分=S：削除）"
            flag = ""
        else:
            label = {"T": "T：登録（復活疑い）", "H": "H：変更"}.get(aq, aq)
            status = f"⚠️ 要確認（更新区分={label}）"
            flag = "★"

        rows.append({
            "JLAC11コード（①）": code_raw,
            "販売名称（①）":     r.get("販売名称", ""),
            "材料（①）":         r.get("材料(JLAC11)", ""),
            "測定法（①）":       r.get("測定法(JLAC11)", ""),
            "削除理由（①）":     r.get("削除理由", ""),
            "②更新区分":         aq if aq is not None else "（存在しない）",
            "判定":              status,
            "要確認":            flag,
        })

    df_result = pd.DataFrame(rows)
    flagged   = df_result[df_result["要確認"] == "★"]

    print(f"  結果: 全{len(df_result)}件中 要確認 {len(flagged)} 件")

    with pd.ExcelWriter(OUTPUT, engine="openpyxl") as w:
        flagged.to_excel(w, sheet_name="★要確認", index=False)
        df_result.to_excel(w, sheet_name="全件", index=False)

    print(f"  出力: {OUTPUT}")

    if len(flagged) == 0:
        print("\n✅ 要確認項目なし。全件②で廃止済み（または削除済み）。")
    else:
        print(f"\n⚠️  {len(flagged)} 件が要確認です。②で廃止されていない可能性があります。")
        print(flagged[["JLAC11コード（①）", "販売名称（①）", "②更新区分", "判定"]].to_string(index=False))


if __name__ == "__main__":
    main()
