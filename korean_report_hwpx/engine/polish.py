"""자간 다듬기 — 공무원이 한글에서 하는 줄 끝 정리를 자동으로. 작성 Mia(윤승미)
문제 문단(단어 중간 끊김 / 마지막 줄이 너무 짧음)마다 자간 후보(0~-10)를 실제 한글 줄 배치로 시험하고 가장 깔끔한 값을 고른다.
문단끼리는 독립이라 한 번 배치에 여러 문단의 후보를 동시에 시험한다.
- macOS + 한컴오피스 한글 필요. Windows·리눅스에서는 polish=True여도 다듬기 없이 생성만 수행."""
import os, re, sys, platform
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from hwpx_doc import Hwpx
import compose as C

IS_MAC = platform.system() == "Darwin"

CANDS = [(sp, 100) for sp in range(0, -11, -1)] + [(sp, 100) for sp in (1, 2, 3)] + [(sp, ra) for ra in (98, 96) for sp in (0, -2, -4, -6, 2)]  # 자간(조이기→넓히기), 안 되면 장평


def score(sec, pno):
    m = re.search(r'<hp:p id="%s"[^>]*>.*?</hp:p>' % pno, sec, re.S)
    if not m: return None
    p = m.group(0); txt = Hwpx.text(p)
    starts = [int(x) for x in re.findall(r'<hp:lineseg textpos="(\d+)"', p)]
    if len(starts) < 2: return (0, 0, len(starts))
    lines = [txt[a:b] for a, b in zip(starts, starts[1:] + [len(txt)])]
    mid = sum(1 for a, c in zip(lines, lines[1:]) if a and c and a[-1].strip() and c[0].strip() and a[-1].isalnum() and c[0].isalnum())
    full = max(len(l) for l in lines[:-1])
    short = int(len(lines[-1].strip()) / max(1, full) < 0.2)
    return (mid, short, len(lines))


def polish(org, doc, dst, max_rounds=12, log=print, build=None, **kw):
    """자간 다듬기(맥락 한컴오피스 한글 필요).
    macOS가 아니면 다듬기 없이 생성만 수행하고 빈 결과를 반환."""
    if not IS_MAC:
        log("polish는 macOS + 한컴오피스 한글 필요 — Windows/리눅스에서는 생략")
        build = build or C.compose
        c = build(org, doc, dst, **kw)
        return dst, {}, {}
    import hancom
    build = build or C.compose   # 보고서는 report.compose
    override, best, tried = {}, {}, {}
    for r in range(max_rounds):
        c = build(org, doc, dst, override, **kw)
        sec = hancom.layout(dst)
        todo = 0
        for pno, it in c.items.items():
            s = score(sec, pno); sp = it["sp"]
            if s is None: continue
            tried.setdefault(pno, set()).add(tuple(sp)[:2])
            sp = tuple(sp)[:2]
            key = (s[0] * 10 + s[1] * 3 + s[2] * 0.5, 100 - sp[1], abs(sp[0]) + (2 if sp[0] > 0 else 0))
            if pno not in best or key < best[pno][0]: best[pno] = (key, sp, s)
            if best[pno][2][0] == 0 and best[pno][2][1] == 0:
                override[pno] = best[pno][1]; continue
            nxt = next((v for v in CANDS if v not in tried[pno]), None)
            override[pno] = nxt if nxt is not None else best[pno][1]
            todo += nxt is not None
        bad = sum(1 for b in best.values() if b[2][0] or b[2][1])
        log(f"[{r + 1}회] 남은 문제 문단 {bad}개 (시험 중 {todo})")
        if not todo: break
    final = {p: b[1] for p, b in best.items()}
    for p_, b in best.items():   # 끝까지 단어가 갈리는 문단: 그 문단만 어절 단위 줄 나눔 + 벌어짐 최소 자간
        if b[2][0]: final[p_] = (0, 100, "auto")
    c = build(org, doc, dst, final, **kw); sec = hancom.layout(dst)
    remain = {p: score(sec, p) for p in c.items if score(sec, p) and (score(sec, p)[0] or score(sec, p)[1])}
    log(f"[완료] 남은 문제 문단 {len(remain)}개")
    import json
    Path(str(dst) + ".polish.json").write_text(json.dumps({k: list(v) for k, v in final.items()}, ensure_ascii=False), "utf-8")  # 다듬은 자간 저장(재생성 시 재사용)
    return dst, final, remain
