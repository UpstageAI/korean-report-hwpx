"""보도시점·배포 칸 정렬 실측 (유지보수용, 공개판 실행에는 필요 없음). 작성 Mia(윤승미)

원본 보도자료 HWPX(공개판에 포함하지 않음)의 머리 표 가운데 '보도시점/보도일시/배포' 이름표가 있는 첫 표를 찾아
첫 행 칸마다 역할(이름표·값·한 칸 묶음)과 문단 정렬만 뽑는다. 원본 번호·본문은 담지 않는다.
- 줄 구성: split(이름표 칸 + 값 칸), inline(한 칸에 '보도시점 : 값'), stacked(한 칸에 이름표 문단 + 값 문단)
- 기관별 최빈 정렬을 templates/<기관>.json release.cells[].align 에 반영(표본 5건 이상), 요약은 rules/_보도시점정렬.json

사용: python scripts/extract_release_align.py <원본 samples 폴더(pool, pool2 …)> [--write]
"""
import collections as C
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "korean_report_hwpx" / "engine"))
from hwpx_doc import Hwpx, first_tbl, rows_of, tcs_of, paras_of  # noqa: E402

LABEL = re.compile(r"^[/\s]*(보도\s*(시점|일시)|배\s*포(\s*(일시|시점))?)\s*[:：]?\s*$")
INLINE = re.compile(r"^\s*(보도\s*(시점|일시)|배\s*포(\s*(일시|시점))?)\s*[:：]\s*\S")
REL = re.compile(r"보\s*도\s*(시점|일시)|배\s*포")


def align(d, p):
    m = re.search(r'paraPrIDRef="(\d+)"', p)
    return d.para(m.group(1)).get("align", "CENTER") if m else "CENTER"


def measure(path):
    d = Hwpx(path); ps = [p for *_, p in d.paragraphs()]
    for p in ps[:12]:
        if "<hp:tbl" not in p or not REL.search(Hwpx.text(p, True)): continue
        rows = rows_of(first_tbl(p))
        out = []
        for tc in tcs_of(rows[0]) if rows else []:
            qs = [q for q in paras_of(tc) if Hwpx.text(q).strip()]
            t = re.sub(r"\s+", " ", Hwpx.text(tc, True)).strip()
            if not qs: continue
            q0 = re.sub(r"\s+", " ", Hwpx.text(qs[0], True)).strip()
            kind = "보도" if re.search(r"보\s*도", q0) else "배포"
            if LABEL.match(q0) and len(qs) > 1:
                out.append(("stacked", kind, align(d, qs[0]), align(d, qs[1])))
            elif LABEL.match(q0):
                out.append(("label", kind, align(d, qs[0]), None))
            elif INLINE.match(t):
                out.append(("inline", kind, align(d, qs[0]), None))
            elif out and out[-1][0] == "label":
                out.append(("value", out[-1][1], align(d, qs[0]), None))
        if any(c[0] in ("label", "inline", "stacked") for c in out): return out
    return None


def main(src, write):
    by = C.defaultdict(list); seen = set()
    for meta in [Path(src) / p / "_meta.jsonl" for p in ("pool", "pool2") if (Path(src) / p / "_meta.jsonl").exists()]:
        for l in meta.read_text("utf-8").splitlines():
            if not l.strip(): continue
            j = json.loads(l)
            if not j.get("files") or j["id"] in seen: continue
            f = meta.parent / j["files"][0][0]
            if f.suffix != ".hwpx" or not f.exists(): continue
            seen.add(j["id"])
            try: m = measure(f)
            except Exception: m = None
            if m: by[j["org"]].append(m)
    mode = lambda xs: C.Counter(xs).most_common(1)[0] if xs else (None, 0)
    allc = [c for ms in by.values() for m in ms for c in m]
    layout = lambda m: "inline" if any(c[0] == "inline" for c in m) else "stacked" if any(c[0] == "stacked" for c in m) else "split"
    share = lambda xs: {k: round(v / len(xs), 3) for k, v in C.Counter(xs).most_common()}
    common = {"n_docs": sum(map(len, by.values())), "layout": share([layout(m) for ms in by.values() for m in ms]),
              "보도_label": share([c[2] for c in allc if c[:2] == ("label", "보도")]),
              "보도_value": share([c[2] for c in allc if c[:2] == ("value", "보도")]),
              "배포_label": share([c[2] for c in allc if c[:2] == ("label", "배포")]),
              "배포_value": share([c[2] for c in allc if c[:2] == ("value", "배포")]),
              "inline": share([c[2] for c in allc if c[0] == "inline"])}
    orgs = {}
    for o, ms in sorted(by.items()):
        if len(ms) < 5: continue
        cs = [c for m in ms for c in m]
        pick = lambda role, kind: mode([c[2] for c in cs if c[:2] == (role, kind)])
        orgs[o] = {"n": len(ms), "layout": mode([layout(m) for m in ms])[0],
                   **{f"{k}_{r}": pick(r, k)[0] for k in ("보도", "배포") for r in ("label", "value", "inline") if pick(r, k)[0]}}
    out = {"_설명": "보도시점·배포 칸 정렬 실측. layout: split=이름표·값 별도 칸, inline=한 칸 '보도시점 : 값', stacked=한 칸 두 문단. 값은 비율(공통) 또는 최빈값(기관).",
           "common": common, "orgs": orgs}
    (ROOT / "korean_report_hwpx/rules/_보도시점정렬.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), "utf-8")
    print(json.dumps(common, ensure_ascii=False))
    for o, s in orgs.items(): print(o, s)
    if write:
        ROLE = {"release_label": ("보도", "label"), "release": ("보도", "value"), "distribute_label": ("배포", "label"),
                "distribute": ("배포", "value"), "release_inline": ("보도", "inline")}
        top = lambda k: max(common[k], key=common[k].get) if common[k] else "CENTER"
        for f in sorted((ROOT / "korean_report_hwpx/templates").glob("*.json")):
            t = json.loads(f.read_text("utf-8")); r = t.get("release")
            if not r: continue
            s = orgs.get(t["org"], {}); ch = 0
            for c in r["cells"]:
                if c["role"] not in ROLE: continue
                kind, role = ROLE[c["role"]]
                a = s.get(f"{kind}_{role}") or top(f"{kind}_{role}" if role != "inline" else "inline")
                if c.get("align") != a: c["align"] = a; ch += 1
            r["align_source"] = f"실측 {s['n']}건 최빈값" if s else "공통 최빈값(기관 표본 5건 미만)"
            f.write_text(json.dumps(t, ensure_ascii=False, indent=1), "utf-8")
            if ch: print("갱신", t["org"], [(c["role"], c["align"]) for c in r["cells"]])


if __name__ == "__main__":
    main(sys.argv[1], "--write" in sys.argv)
