"""選挙公報の文字起こし(transcribe_*.json)と選管の候補者一覧(data/official.json)を合わせて
data/candidates.json を作る。

使い方: python3 -I tools/merge.py <文字起こしJSONのあるフォルダ>
名前・党派・URL は選管の一覧を正とし、見出し・公約・プロフィールは公報の原文を使う。
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
src = Path(sys.argv[1])

# 公報の表記と選管一覧の表記が違う候補（公報 → 選管）
ALIAS = {"岡田信俊": "岡田のぶとし"}
# 手書きの公報（表記は原文どおり読み取っている旨をページに出す）
HANDWRITTEN = {"山根義雄"}

official = json.loads((ROOT / "data/official.json").read_text())
by_key = {o["name"].replace(" ", ""): o for o in official}

rows = []
for part in ("a", "b", "c"):
    rows += json.loads((src / f"transcribe_{part}.json").read_text())

import re

CIRCLED = re.compile(r"^[①②③④⑤⑥⑦⑧⑨⑩]\s*")


def as_list(v):
    if not v:
        return []
    return v if isinstance(v, list) else [v]


def normalize(r):
    """文字起こし担当ごとに少しずつ違うキーを、共通の形にそろえる（文言は変えない）。"""
    r = dict(r)
    pol = [CIRCLED.sub("", p) for p in as_list(r.get("policies"))]
    det = r.get("policy_details") or []
    # 「見出し — 説明」は文字起こし側で足した区切りなので、見出しと小項目に分け直す
    if any(" — " in p for p in pol):
        det = det or [[] for _ in pol]
        for i, p in enumerate(pol):
            if " — " in p:
                head, tail = p.split(" — ", 1)
                pol[i] = head
                det[i] = [tail] + list(det[i] if i < len(det) else [])
    # 本文が見出しごとの説明（①…②…）になっている場合は小項目へ
    body = r.get("body") or ""
    paras = [x.strip() for x in body.split(" / ")] if body else []
    if pol and len(paras) == len(pol) and all(CIRCLED.match(x) for x in paras):
        det = [[CIRCLED.sub("", x)] for x in paras]
        body = ""
    if r.get("lead"):
        body = " / ".join(x for x in [r["lead"], body] if x)
    groups = r.get("policy_groups") or []
    if not groups and r.get("achievements"):
        groups = [
            {"heading": r.get("achievements_heading") or "", "items": as_list(r["achievements"])},
            {"heading": r.get("policies_heading") or "", "items": pol},
        ]
    other = as_list(r.get("other_text"))
    for k in ("closing", "note_text", "label", "diagram_text"):
        other += as_list(r.get(k))
    r.update(
        policies_heading="" if groups else (r.get("policies_heading") or ""),
        policies=pol,
        policy_details=det,
        policy_groups=groups,
        body=body.replace(" / ", "\n"),
        other_text=other,
        subcopy=r.get("subcopy") or r.get("subheading") or "",
        profile=(r.get("profile") or "").replace(" / ", "\n"),
    )
    return r


out, used, problems = [], set(), []
for i, r in enumerate(rows, 1):
    r = normalize(r)
    key = r["name"].replace(" ", "").replace("　", "")
    key = ALIAS.get(key, key)
    o = by_key.get(key)
    if o is None:
        problems.append(f"{i}: 公報の名前『{r['name']}』が選管一覧に見つからない")
        continue
    used.add(o["no"])
    out.append({
        "order": i,
        "page": int(r["file"][1]),
        "name": o["name"],
        "kana": r.get("kana") or "",
        "party": o["party"],
        "catchcopy": r.get("catchcopy") or "",
        "subcopy": r.get("subcopy") or "",
        "policies_heading": r.get("policies_heading") or "",
        "policies": r.get("policies") or [],
        "policy_details": r.get("policy_details") or [],
        "policy_groups": r.get("policy_groups") or [],
        "other_text": r.get("other_text") or [],
        "handwritten": key in HANDWRITTEN,
        "body": r.get("body") or "",
        "profile": r.get("profile") or "",
        "url": o.get("url"),
        "url_text": o.get("url_text"),
        "sns": o.get("sns"),
    })

missing = [o["name"] for o in official if o["no"] not in used]
if missing:
    problems.append("公報側に無い選管一覧の候補: " + "、".join(missing))
if problems:
    print("\n".join(problems))
    sys.exit(1)

(ROOT / "data/candidates.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
print(f"{len(out)}人を書き出しました")
