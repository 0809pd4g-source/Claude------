#!/usr/bin/env bash
# 自動作成の回帰試験：作成ツール（9/15）から書き出した9月のインプットで、9月公開版5点をバイト一致で再現できるか
# 使い方: bash 00_共通/03_scripts/regression_test.sh   （薬剤関連マスタ月次作成/ で実行）
set -e
D=00_共通/03_scripts; R=00_共通/01_input/回帰試験_202609; P=202610作成分/01_input/前月公開版_202609
OUT=$(mktemp -d)
python -I $D/generate_yakuzai_master.py --state $R --yj "$P/個別医薬品コード(YJコード)リスト_202609_20260915.csv" \
  --prev-gcm $R/前回GCM.csv --ym 202609 --ymd 20260915 --date 20260915 --out "$OUT"
python -I $D/make_expected.py --compare "$P" "$OUT" && echo "回帰試験 OK：9月公開版5点と一致" || { echo "回帰試験 NG"; exit 1; }
