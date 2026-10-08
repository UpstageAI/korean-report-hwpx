"""참고·붙임 쪽 머리 표 서식 수치 추출 (유지보수용, 공개판 실행에는 필요 없음). 작성 Mia(윤승미)

원본 보도자료 HWPX(공개판에 포함하지 않음)에서 참고 구간을 여는 첫 표(「붙임 1」「참고 1」 머리)를 찾아
칸 수·칸 폭 비율·칸별 선(변별 종류·굵기)·라벨 칸 바탕색·글꼴·크기·굵기·글자색만 뽑아
rules_report/_참고머리.json에 쓴다. 원본 문서 번호·제목·XML 조각은 담지 않는다.
- 공통값: 기관별 최빈 형태의 기관 간 최빈값
- 기관값: 표본 5건 이상이고 공통값과 다른 항목만

사용: python scripts/extract_appx_head.py <원본 samples 폴더(pool, pool2 …)> [출력 json]
구간 판정은 전수 조사(census.zones_of)와 같은 규칙: 본문 시작 뒤 '참고/붙임/별첨 N'으로 시작하는 1~2행 표.
"""
import collections as C
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "korean_gov_docs" / "engine"))
from hwpx_doc import Hwpx, first_tbl, rows_of, tcs_of, paras_of  # noqa: E402

APPX = re.compile(r"^[\s<〈《\[［【(「]*(참\s*고|붙\s*임|별\s*첨)\s*(\d{0,2})\s*[>〉》\]］】)」.:：]?")
CONTACT = re.compile(r"담당\s*부서|책임자|담당자")
PHONE = re.compile(r"\(?0\d{1,2}-\d{3,4}-\d{4}")


def head_index(ps):
    T = [Hwpx.text(p, True).strip() for p in ps]
    first = next((i for i, p in enumerate(ps) if "<hp:tbl" not in p and len(Hwpx.text(p).strip()) >= 25), len(ps))
    for i in range(first, len(ps)):
        if "<hp:tbl" not in ps[i] or not APPX.match(T[i]) or (CONTACT.search(T[i]) and PHONE.search(T[i])): continue
        r = re.search(r'rowCnt="(\d+)"', ps[i])
        if r and int(r.group(1)) <= 2 and len(T[i]) < 120: return i
    return None


def border(header, bf):
    m = re.search(r'<hh:borderFill id="%s".*?</hh:borderFill>' % bf, header, re.S); s = m.group(0) if m else ""
    sides = {}
    for k, t, w, c in re.findall(r'<hh:(left|right|top|bottom)Border type="(\w+)" width="([\d.]+) mm" color="(#\w+)"', s):
        sides[k] = 0.0 if t == "NONE" or c.upper() == "#FFFFFF" else float(w)
    c = re.search(r'faceColor="(#[0-9A-Fa-f]{6})"', s)
    fill = c.group(1).upper() if c and c.group(1).upper() != "#FFFFFF" else None
    return sides, fill


def measure(path):
    d = Hwpx(path); ps = [p for *_, p in d.paragraphs()]
    i = head_index(ps)
    if i is None: return None
    tb = first_tbl(ps[i]); rows = rows_of(tb)
    if not rows: return None
    cells = []
    for tc in tcs_of(rows[0]):
        sides, fill = border(d.header, re.search(r'borderFillIDRef="(\d+)"', tc).group(1))
        qs = [q for q in paras_of(tc) if Hwpx.text(q).strip()]
        ch = d.char(Hwpx.ids(qs[0])[1]) if qs else {}
        cells.append({"w": int(re.search(r'<hp:cellSz width="(\d+)"', tc).group(1)), "sides": sides, "fill": fill,
                      "font": ch.get("font"), "pt": ch.get("pt"), "bold": ch.get("bold"), "color": ch.get("color")})
    return cells if len(cells) in (2, 3) and len(rows) == 1 else None


def pattern(sides):
    on = {k for k, v in sides.items() if v > 0}
    return ("box" if on == {"top", "bottom", "left", "right"} else "topbottom" if on == {"top", "bottom"}
            else "bottom" if on == {"bottom"} else "none" if not on else "+".join(sorted(on)))


def summarize(ms):
    """한 기관(또는 전체)의 표본 → 최빈 형태."""
    mode = lambda xs: C.Counter(xs).most_common(1)[0][0]
    med = lambda xs: sorted(xs)[len(xs) // 2]
    cols = mode(len(m) for m in ms); ms = [m for m in ms if len(m) == cols]
    tot = lambda m: sum(c["w"] for c in m)
    lab, head = [m[0] for m in ms], [m[-1] for m in ms]
    hp = mode(pattern(c["sides"]) for c in head)
    hw = med([max(c["sides"].values() or [0]) for c in head if pattern(c["sides"]) == hp])
    return {"n": len(ms), "cols": cols,
            "ratio": [round(med([m[k]["w"] / tot(m) for m in ms]), 3) for k in range(cols)],
            "label": {"fill": mode(c["fill"] for c in lab), "font": mode(c["font"] for c in lab if c["font"]),
                      "pt": mode(c["pt"] for c in lab if c["pt"]), "bold": mode(bool(c["bold"]) for c in lab),
                      "color": mode((c["color"] or "#000000").upper() for c in lab),
                      "line": med([max(c["sides"].values() or [0]) for c in lab])},
            "heading": {"font": mode(c["font"] for c in head if c["font"]), "pt": mode(c["pt"] for c in head if c["pt"]),
                        "bold": mode(bool(c["bold"]) for c in head), "lines": hp, "line": hw},
            "share": round(sum(pattern(c["sides"]) == hp for c in head) / len(head), 2)}


def main(src, dst):
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
    orgs = {o: summarize(ms) for o, ms in by.items() if len(ms) >= 5}
    mode = lambda xs: C.Counter(xs).most_common(1)[0][0]
    med = lambda xs: sorted(xs)[len(xs) // 2]
    S = list(orgs.values())
    common = {"cols": mode(s["cols"] for s in S),
              "ratio": [round(med([s["ratio"][k] for s in S if s["cols"] == 3]), 3) for k in range(3)],
              "label": {k: mode(s["label"][k] for s in S) for k in ("fill", "font", "pt", "bold", "color", "line")},
              "heading": {k: mode(s["heading"][k] for s in S) for k in ("font", "pt", "bold", "lines", "line")}}
    out = {"_설명": "참고·붙임 쪽 머리 표 실측(보도자료 원본 참고 구간 첫 표). 비율=칸 폭/표 폭, line=선 굵기(mm), "
                    "heading.lines: box=네 변, topbottom=위아래만, bottom=아래만, a+b=그 변들만. 기관값은 공통과 다른 항목만.",
           "n_docs": sum(len(v) for v in by.values()), "n_orgs": len(orgs),
           "pattern_orgs": dict(C.Counter(s["heading"]["lines"] for s in S)), "common": common, "orgs": {}}
    for o, s in sorted(orgs.items()):
        diff = {"n": s["n"], "share": s["share"]}
        if s["cols"] != common["cols"]: diff["cols"] = s["cols"]
        if any(abs(a - b) > 0.01 for a, b in zip(s["ratio"], common["ratio"])) and s["cols"] == 3: diff["ratio"] = s["ratio"]
        for part in ("label", "heading"):
            dd = {k: v for k, v in s[part].items() if v != common[part][k]}
            if dd: diff[part] = dd
        out["orgs"][o] = diff
    Path(dst).write_text(json.dumps(out, ensure_ascii=False, indent=1), "utf-8")
    print("문서", out["n_docs"], "기관", out["n_orgs"], "공통", common)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else ROOT / "korean_gov_docs/rules_report/_참고머리.json")
