"""『その他の測定法』コード（JLAC11の13〜15桁=000／JLAC10=999、ダミーコード）の候補を作る。

作成ツール「電子カルテ情報共有サービス対応JLACコード表作成ツール_20250127.xlsx」の
「ダミーコード生成用」シートと同じ考え方で作る（2026-10-07 本田さんKT・ツールの式を確認）。
  1. 各行のJLAC11コードの13〜15桁を000に、JLAC10コードの13〜15桁を999に置き換える
  2. 置き換えたJLAC11コードが上の行に出ていれば除く（いちばん上の行の内容を使う）
  3. マスタにすでにある000コードは除く
  4. 測定法(JLAC11)・検査方法(JLAC10-測定法)は「その他の測定法」、販売名称は空欄。
     他の列はいちばん上の行を写す
  5. 適用終了日：同じグループに有効な行（99999999）があれば99999999（KA-34）

出力（1つのxlsx）：
  - 説明
  - 000コード候補（値）……追加する行（マスタと同じ32列）＋確認用の列
  - ダミーコード生成用（10月版）……ツールの式を32列のマスタに合わせて直したもの（式で再計算できる）

使い方：python make_sonota_codes.py <マスタxlsx> <出力xlsx>
"""
import sys
from collections import OrderedDict

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

SONOTA = "その他の測定法"
OPEN_END = "99999999"


def s(v):
    return "" if v is None else str(v)


def load_master(path):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.worksheets[0]
    rows = list(ws.iter_rows(values_only=True))
    header = list(rows[0][:32])
    data = [list(r[:32]) + [None] * (32 - len(r[:32])) for r in rows[1:]]
    while data and all(v in (None, "") for v in data[-1]):
        data.pop()
    return ws.title, header, data


def build_candidates(header, data):
    ix = {h: i for i, h in enumerate(header)}
    m, t = ix["JLAC11コード"], ix["JLAC10コード"]
    st, en = ix["適用開始日"], ix["適用終了日"]
    existing = {s(r[m]) for r in data if s(r[m])[12:15] == "000"}
    groups = OrderedDict()
    for n, r in enumerate(data, start=2):
        c = s(r[m])
        if not c or c[12:15] == "000":
            continue
        groups.setdefault(c[:12] + "000" + c[15:], []).append((n, r))
    out = []
    for key, members in groups.items():
        if key in existing:
            continue
        n0, first = members[0]
        row = list(first)
        row[ix["販売名称"]] = None
        row[ix["測定法(JLAC11)"]] = SONOTA
        row[m] = key
        row[ix["検査方法(JLAC10-測定法)"]] = SONOTA
        c10 = s(first[t])
        row[t] = c10[:12] + "999" + c10[15:] if c10 else None
        alive = [r for _, r in members if s(r[en]) == OPEN_END]
        notes = []
        if alive:
            row[en] = first[en] if s(first[en]) == OPEN_END else int(OPEN_END)
            if s(first[en]) != OPEN_END:
                notes.append("先頭行は終了済み→有効な行があるため終了日を99999999にした（KA-34）")
        else:
            notes.append("元の行がすべて終了済み：作るかどうか要判断")
        starts = {s(r[st]) for _, r in members}
        if s(first[st]) in ("", "0", "00000000"):
            notes.append("開始日が00000000（KA-M1：新規は00000000以外）")
        if len(starts) > 1:
            notes.append("元の行で開始日が違う：" + "／".join(sorted(starts)))
        for col in ("FHIR識別文字列", "FHIR項目名称", "表示用単位", "表示用単位2", "XML用単位", "XML用単位2", "材料(JLAC10)"):
            vals = {s(r[ix[col]]) for _, r in members}
            if len(vals) > 1:
                notes.append(f"元の行で{col}が違う（先頭行の値を使用）")
        out.append({
            "row": row,
            "src_row": n0,
            "src_code": s(first[m]),
            "members": [s(r[m]) for _, r in members],
            "notes": notes,
        })
    return out, len(existing), len(groups)


HEAD_FILL = PatternFill("solid", fgColor="DDEBF7")
NOTE_FILL = PatternFill("solid", fgColor="FFF2CC")
BOLD = Font(bold=True)


def style_header(ws, ncol):
    for c in range(1, ncol + 1):
        cell = ws.cell(row=1, column=c)
        cell.font = BOLD
        cell.fill = HEAD_FILL
        cell.alignment = Alignment(wrap_text=True, vertical="top")
    ws.freeze_panes = "A2"


def write_candidates(wb, header, cands, sep_codes):
    ws = wb.create_sheet("000コード候補")
    extra = ["【確認】元にした行（マスタの行番号）", "【確認】元にしたJLAC11コード（先頭行）",
             "【確認】元の行数", "【確認】元の行のJLAC11コード", "【確認】元の行が9月公開版にあったか", "【確認】要確認事項"]
    ws.append(header + extra)
    for c in cands:
        in_sep = "すべてあった" if all(x in sep_codes for x in c["members"]) else "10月の新規を含む"
        if sep_codes and in_sep == "すべてあった":
            c["notes"].append("元の行は9月公開版からある（9月に000版を作っていなかった）：開始日を先頭行のまま写すか、今月の15日にするか要判断")
        ws.append(c["row"] + [c["src_row"], c["src_code"], len(c["members"]), "、".join(c["members"]), in_sep,
                              "\n".join(c["notes"])])
    style_header(ws, len(header) + len(extra))
    for r in range(2, ws.max_row + 1):
        for col in range(len(header) + 1, len(header) + len(extra) + 1):
            ws.cell(row=r, column=col).fill = NOTE_FILL
            ws.cell(row=r, column=col).alignment = Alignment(wrap_text=True, vertical="top")
    for col in range(1, len(header) + len(extra) + 1):
        ws.column_dimensions[get_column_letter(col)].width = 14
    ws.column_dimensions[get_column_letter(header.index("JLAC11コード") + 1)].width = 20
    ws.column_dimensions[get_column_letter(len(header) + len(extra))].width = 60
    return ws


def write_formula_sheet(wb, header, data):
    """ツールの「ダミーコード生成用」を32列のマスタに合わせて直したもの。"""
    ws = wb.create_sheet("ダミーコード生成用（10月版）")
    ix = {h: i for i, h in enumerate(header)}
    L = lambda i: get_column_letter(i + 1)
    M, T = L(ix["JLAC11コード"]), L(ix["JLAC10コード"])
    # A〜AF：マスタ（値）
    work = ["000版JLAC11", "000重複(A)", "999版JLAC10", "999重複(B)", "A&B", "マスタに既存の000", "抽出対象(○)"]
    work_cols = list(range(34, 34 + len(work)))  # AH〜AN（AGは空ける）。出力はAOを空けてAP列から
    ws.append(header + [None] + work + [None] + header)
    last = len(data) + 1
    for n, r in enumerate(data, start=2):
        line = [v for v in r] + [None]
        ah, ai, aj, ak = (get_column_letter(c) for c in work_cols[:4])
        am = get_column_letter(work_cols[5])
        line += [
            f'=IF({M}{n}="","",LEFT({M}{n},12)&"000"&RIGHT({M}{n},2))',
            f'=IF({ah}{n}="","",IF(COUNTIF(${ah}$2:{ah}{n},{ah}{n})>1,"A",""))',
            f'=IF({T}{n}="","",LEFT({T}{n},12)&"999"&RIGHT({T}{n},2))',
            f'=IF({aj}{n}="","",IF(COUNTIF(${aj}$2:{aj}{n},{aj}{n})>1,"B",""))',
            f'={ai}{n}&{ak}{n}',
            f'=IF({ah}{n}="","",IF(COUNTIF(${M}$2:${M}${last},{ah}{n})>0,"既存",""))',
            f'=IF(AND({ah}{n}<>"",{ai}{n}="",{am}{n}=""),"○","")',
        ]
        line += [None]
        for i, h in enumerate(header):
            src = f"{L(i)}{n}"
            if h in ("測定法(JLAC11)", "検査方法(JLAC10-測定法)"):
                line.append(SONOTA)
            elif h == "JLAC11コード":
                line.append(f"={ah}{n}")
            elif h == "JLAC10コード":
                line.append(f"={aj}{n}")
            elif h == "販売名称":
                line.append(None)
            else:
                line.append(f'=IF({src}="","",{src})')
        ws.append(line)
    style_header(ws, len(header) * 2 + len(work) + 2)
    for c in work_cols:
        ws.cell(row=1, column=c).fill = NOTE_FILL
    ws.auto_filter.ref = f"A1:{get_column_letter(len(header) * 2 + len(work) + 2)}{last}"
    return ws, get_column_letter(work_cols[-1]), get_column_letter(work_cols[0])


def write_readme(wb, master_name, sheet_name, n_rows, n_existing, n_groups, cands, filt_col, ah_col):
    ws = wb.active
    ws.title = "説明"
    lines = [
        ["『その他の測定法』コード（ダミーコード）作成　10月版"],
        [],
        ["元にしたマスタ", master_name],
        ["シート", sheet_name],
        ["マスタの行数", n_rows],
        ["000版にまとめたグループ数", n_groups],
        ["マスタにすでにある000コード", n_existing],
        ["新しく作る000コードの候補", len(cands)],
        [],
        ["シート", "中身"],
        ["000コード候補", "追加する行（マスタと同じ32列）。右側の黄色い列は確認用で、マスタに入れるときは除く"],
        ["ダミーコード生成用（10月版）",
         f"作成ツール（20250127）の「ダミーコード生成用」の式を、表示用単位2・XML用単位2のある32列のマスタに合わせて直したもの。"
         f"{filt_col}列（抽出対象）で「○」に絞り、右側の出力列（『区分名称』から）をコピーすると、000コード候補シートと同じ行になる"],
        [],
        ["作り方（ツールの考え方）"],
        ["1", "JLAC11コードの13〜15桁を000、JLAC10コードの13〜15桁を999に置き換える"],
        ["2", "置き換えた000コードが上の行に出ていれば除く（いちばん上の行の名称・FHIR識別文字列・単位・開始日を使う）"],
        ["3", "マスタにすでにある000コードは除く"],
        ["4", "測定法(JLAC11)・検査方法(JLAC10-測定法)は「その他の測定法」、販売名称は空欄"],
        ["5", "適用終了日：同じグループに有効な行があれば99999999（KA-34）"],
        [],
        ["作成ツールからの変更点"],
        ["・", "列の位置を32列のマスタに合わせた（ツールのままだとJLAC10コードの代わりに材料(JLAC10)から999版を作ってしまう）"],
        ["・", "JLAC11コードが空の行は000版を作らない（ツールのままだと「000」だけの行が抽出される）"],
        ["・", f"「マスタに既存の000」列を追加し、手作業の重複削除を式でできるようにした（{filt_col}列の○は、A列の重複と既存の000をどちらも除いたもの）"],
        ["・", "JLAC10の998（測定法を問わず）の列は作っていない"],
        [],
        ["9月公開版で確かめたこと（2026-10-07）"],
        ["・", "9月公開版の000コード1,179件は、名称・FHIR識別文字列などがいちばん上の元の行と一致（材料(JLAC10)の3件だけ、別の元の行と一致）"],
        ["・", "9月に新しく作った3件（LDL-C）は、開始日が元の行と同じ20260915"],
    ]
    for l in lines:
        ws.append(l)
    ws["A1"].font = Font(bold=True, size=13)
    for r in (10, 14, 21, 27):
        ws.cell(row=r, column=1).font = BOLD
    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 110
    for row in ws.iter_rows():
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical="top")


def main():
    master, out = sys.argv[1], sys.argv[2]
    sep_csv = sys.argv[3] if len(sys.argv) > 3 else None
    sheet_name, header, data = load_master(master)
    cands, n_existing, n_groups = build_candidates(header, data)
    sep_codes = set()
    if sep_csv:
        import csv
        with open(sep_csv, encoding="utf-8-sig") as f:
            rd = csv.reader(f)
            h = next(rd)
            k = h.index("JLAC11コード")
            sep_codes = {r[k] for r in rd}
    wb = openpyxl.Workbook()
    write_candidates(wb, header, cands, sep_codes)
    _, filt_col, ah_col = write_formula_sheet(wb, header, data)
    import os
    write_readme(wb, os.path.basename(master), sheet_name, len(data), n_existing, n_groups, cands, filt_col, ah_col)
    wb.calculation.fullCalcOnLoad = True
    wb.save(out)
    print(f"rows={len(data)} groups={n_groups} existing000={n_existing} candidates={len(cands)}")
    for c in cands:
        print(c["row"][header.index("JLAC11コード")], c["src_code"], "|", " / ".join(c["notes"]))


if __name__ == "__main__":
    main()
