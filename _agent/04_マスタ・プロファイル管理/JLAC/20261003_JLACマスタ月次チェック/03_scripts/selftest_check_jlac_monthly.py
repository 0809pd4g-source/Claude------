"""【凍結・参照実装】check_jlac_monthly.py の検出力テスト。現行のテストは selftest.mjs を使う。"""
import sys, copy
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import check_jlac_monthly as m

T = m.load_tables()
H, rows = m.load(m.NEW_FILE, m.NEW_SHEETS[0])
_, base = m.load(m.PREV_FILE, m.PREV_SHEET_NEWONLY)
good = next(r for r in rows if m.date_norm(r.s[m.START]) == '00000000' and r.s[m.DTYPE] == 'PQ'
            and not m.row_checks(r, H, T) is None)
good.s[m.START] = '00000000'
assert not [c for c in m.row_checks(good, H, T) if c[1] == 'strict'], m.row_checks(good, H, T)


def mutate(col, val):
    r = copy.deepcopy(good)
    r.s[col] = val
    r.code = r.s[m.JLAC11]
    return r


def code_with(pos, val):
    c = good.s[m.JLAC11]
    return c[:pos[0]] + val + c[pos[1]:]


cases = [
    ('KA-01', mutate(m.FLG_L, 'L')), ('KA-02', mutate(m.JLAC11, good.code[:16])),
    ('KA-03', mutate(m.KYUKYU, '2')), ('KA-04', mutate(m.DATAKUBUN, '3')),
    ('KA-06', mutate(m.UNIT, good.s[m.UNIT].upper() + 'x')), ('KA-07', mutate(m.MAT11, '尿')),
    ('KA-08', mutate(m.METH11, 'でたらめ試薬')),
    ('KA-13', mutate(m.DTYPE, 'ST')), ('KA-18', mutate(m.START, '0')), ('KA-18', mutate(m.START, '20261340')),
    ('KA-19', mutate(m.END, '9999999')), ('KA-20', mutate(m.JLAC10, good.s[m.JLAC10][:16])),
    ('KA-21', mutate(m.JLAC10, 'ZZZZZ' + good.s[m.JLAC10][5:])), ('KA-22', mutate(m.MAT10, '尿')),
    ('KA-23', mutate(m.METH10, 'でたらめ法')), ('KA-25', mutate(m.FHIRNAME, '#N/A')),
    ('KA-27', mutate(m.KUBUN, '')), ('KA-28', mutate(m.DAIKOMOKU, ' ')), ('KA-29', mutate(m.FHIRNAME, '')),
    ('KA-30', mutate(m.FHIRID, '')), ('KA-DUMMY', mutate(m.JLAC11, good.code[:12] + 'XXX' + good.code[15:])),
    ('KA-K', mutate(m.UNIT, 'K')),
]
cd = mutate(m.DTYPE, 'CD')
cases += [('KA-14', cd), ('KA-15', cd), ('KA-16', cd)]
r26 = copy.deepcopy(good); r26.extra = [33]
cases.append(('KA-26', r26))

fail = 0
for cid, r in cases:
    got = {c[0] for c in m.row_checks(r, H, T)}
    ok = cid in got
    fail += not ok
    print('OK ' if ok else 'NG ', cid, sorted(got))

# グループ・前月比較
g1 = copy.deepcopy(good); g2 = copy.deepcopy(good)
g2.code = g2.s[m.JLAC11] = good.code[:15] + ('00' if good.code[15:] != '00' else '01')
g2.s[m.ORDER] = '99999'; g2.s[m.FHIRID] = 'OTHER'
got = {f[1] for f in m.group_findings([g1, g2], [good])}
for cid in ('KA-17', 'KA-32', 'KA-10'):
    print('OK ' if cid in got else 'NG ', cid, sorted(got)); fail += cid not in got
d1 = copy.deepcopy(good)
got = {f[1] for f in m.group_findings([good, d1], [good])}
print('OK ' if 'KA-31' in got else 'NG ', 'KA-31'); fail += 'KA-31' not in got
o = copy.deepcopy(good); o.code = o.s[m.JLAC11] = good.code[:12] + '000' + good.code[15:]
got = {f[1] for f in m.group_findings([o], [])}
print('OK ' if 'KA-33' in got else 'NG ', 'KA-33'); fail += 'KA-33' not in got
e1 = copy.deepcopy(good); e1.s[m.END] = '20261014'
o2 = copy.deepcopy(o); o2.s[m.END] = '20261014'
got = {f[1] for f in m.group_findings([e1, o2], [])}
print('OK ' if 'KA-34' in got else 'NG ', 'KA-34'); fail += 'KA-34' not in got
for cid, n, p in (('KA-M2', mutate(m.START, '20261015'), good), ('KA-M3', good, mutate(m.END, '20261014')),
                  ('STEP1-END', mutate(m.END, '20261001'), good), ('STEP1-DIFF', mutate(m.HANBAI, '別名'), good)):
    got = {c[0] for c in m.compare_prev(n, p, H)}
    print('OK ' if cid in got else 'NG ', cid, sorted(got)); fail += cid not in got
print('FAIL', fail)
sys.exit(1 if fail else 0)
