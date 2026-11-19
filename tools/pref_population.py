"""総務省統計局「人口推計（2024年10月1日現在）」の第2表・第3表から
data/pref_population_2024.json を作る。

使い方: python tools/pref_population.py <05k2024-2.xlsx> <05k2024-3.xlsx>
出典: https://www.stat.go.jp/data/jinsui/2024np/index.html （単位：千人）
"""
import json, sys
from pathlib import Path
import openpyxl

ROOT = Path(__file__).resolve().parent.parent

def rows(path):
    ws = openpyxl.load_workbook(path, data_only=True).worksheets[0]
    for r in ws.iter_rows(values_only=True):
        v = [c for c in r if c is not None]
        if len(v) > 3 and isinstance(v[0], str) and v[0].isdigit() and len(v[0]) == 2:
            yield v[0], v[1].strip().replace("　", ""), v[2:]
        elif v and isinstance(v[0], str) and v[0].replace("　", "").strip() == "全国":
            yield "00", "全国", v[1:]

total = {code: (name, nums[0]) for code, name, nums in rows(sys.argv[1])}
out = []
for code, name, nums in rows(sys.argv[2]):
    young, work, old = nums[0], nums[1], nums[2]
    tname, pop = total[code]
    assert tname == name, (tname, name)
    out.append({"code": code, "name": name, "pop": pop, "young": young, "work": work, "old": old})

assert len(out) == 48, len(out)
doc = {
    "source": "総務省統計局「人口推計（2024年（令和6年）10月1日現在）」第2表・第3表",
    "source_url": "https://www.stat.go.jp/data/jinsui/2024np/index.html",
    "as_of": "2024-10-01",
    "unit": "千人",
    "rows": out,
}
(ROOT / "data/pref_population_2024.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")
print(len(out), "rows")
