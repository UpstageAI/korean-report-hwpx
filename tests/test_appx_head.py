"""참고·붙임 쪽 머리 표 구조(원본 실측 형태)와 계층별 글자 크기 단조성 회귀 테스트. 작성 Mia(윤승미)"""
import json, re, zipfile

import pytest

import compose as C
import report as R
from sample_release import SAMPLE
from sample_report import SAMPLE_REPORT

RULE = json.loads((C.ROOT / "rules_report/_참고머리.json").read_text("utf-8"))
PRESS = C.ministries()
REPORT = R.ministries() + [""]


def _sides(header, bf):
    blk = re.search(r'<hh:borderFill id="%s".*?</hh:borderFill>' % bf, header, re.S).group(0)
    return {k: (0.0 if t == "NONE" else float(w)) for k, t, w in re.findall(r'<hh:(left|right|top|bottom)Border type="(\w+)" width="([\d.]+) mm"', blk)}


def _head_tbl(sec):
    m = re.search(r'<hp:p\b[^>]*pageBreak="1"[^>]*>.*?(<hp:tbl\b.*?</hp:tbl>)', sec, re.S)
    return m.group(1)


def _check(c, sec, header):
    tbl = _head_tbl(sec)
    assert 'rowCnt="1" colCnt="3"' in tbl
    tcs = re.findall(r'<hp:tc\b.*?</hp:tc>', tbl, re.S)
    assert len(tcs) == 3
    bfs = [re.search(r'borderFillIDRef="(\d+)"', t).group(1) for t in tcs]
    ws = [int(re.search(r'<hp:cellSz width="(\d+)"', t).group(1)) for t in tcs]
    A = c.appx_rule()
    # 라벨 칸 | 간격 칸 | 제목 칸: 라벨과 제목이 붙지 않음(간격 칸 폭 > 0), 제목 칸이 가장 넓음
    assert ws[1] >= 400 and ws[2] > 5 * ws[0]
    gap = _sides(header, bfs[1])
    assert gap["top"] == 0 and gap["bottom"] == 0           # 간격 칸 위아래 선 없음
    head = _sides(header, bfs[2])
    want = set(C.Composer.head_lines(A["heading"]["lines"]))
    assert {k for k, v in head.items() if v > 0} == want
    for k in want: assert head[k] == pytest.approx(A["heading"]["line"])
    assert re.sub(r"<[^>]+>", "", tcs[0]).strip().startswith(("참고", "붙임"))
    # 표 바깥 테두리 없음
    tbf = re.search(r'<hp:tbl\b[^>]*borderFillIDRef="(\d+)"', tbl).group(1)
    assert all(v == 0 for v in _sides(header, tbf).values())


@pytest.mark.parametrize("org", PRESS)
def test_press_appx_head(org, tmp_path):
    c = C.compose(org, SAMPLE, tmp_path / "a.hwpx")
    z = zipfile.ZipFile(tmp_path / "a.hwpx")
    _check(c, z.read("Contents/section0.xml").decode(), z.read("Contents/header.xml").decode())


@pytest.mark.parametrize("org", REPORT)
def test_report_appx_head(org, tmp_path):
    c = R.compose(org, SAMPLE_REPORT, tmp_path / "a.hwpx")
    z = zipfile.ZipFile(tmp_path / "a.hwpx")
    _check(c, z.read("Contents/section0.xml").decode(), z.read("Contents/header.xml").decode())


def test_rule_common_is_measured_mode():
    cm = RULE["common"]
    assert cm["cols"] == 3 and cm["heading"]["lines"] == "box" and abs(sum(cm["ratio"]) - 1) < 0.01
    assert RULE["orgs"]["과학기술정보통신부"]["heading"]["lines"] == "topbottom"   # 기관값: 위아래 선만
    assert RULE["orgs"]["관세청"]["heading"]["lines"] == "bottom"


def test_topbottom_org_has_no_vertical_lines(tmp_path):
    c = C.compose("과학기술정보통신부", SAMPLE, tmp_path / "a.hwpx")
    z = zipfile.ZipFile(tmp_path / "a.hwpx"); h = z.read("Contents/header.xml").decode()
    tcs = re.findall(r'<hp:tc\b.*?</hp:tc>', _head_tbl(z.read("Contents/section0.xml").decode()), re.S)
    s = _sides(h, re.search(r'borderFillIDRef="(\d+)"', tcs[2]).group(1))
    assert s["left"] == 0 and s["right"] == 0 and s["top"] > 0 and s["bottom"] > 0


def _monotone(c):
    pts = [c.level(lv)["pt"] for lv in ("l1", "l2", "l3")]
    assert pts[0] >= pts[1] >= pts[2], (c.org, pts)


@pytest.mark.parametrize("org", PRESS)
def test_press_level_size_monotone(org):
    _monotone(C.Composer(org))


@pytest.mark.parametrize("org", REPORT)
def test_report_level_size_monotone(org):
    _monotone(R.ReportComposer(org))


def _para_pts(path):
    from hwpx_doc import Hwpx
    d = Hwpx(path); out = []
    for *_, p in d.paragraphs():   # 최상위 문단(표 안 문단 제외)
        if "<hp:tbl" in p: continue
        runs = re.findall(r'<hp:run charPrIDRef="(\d+)"[^>]*>(.*?)</hp:run>', p, re.S)
        m = re.match(r"\s*(□|ㅇ|○|◦|❍|-)\s", Hwpx.text(p))
        if m and runs: out.append((m.group(1), d.char(runs[0][0])["pt"]))
    return out


@pytest.mark.parametrize("org", ["행정안전부", "국세청", "과학기술정보통신부"])
def test_generated_child_not_larger(org, tmp_path):
    """본문·참고 쪽 모두: 하위 기호 문단 글자가 바로 위 상위 기호 문단보다 크지 않음."""
    C.compose(org, SAMPLE, tmp_path / "p.hwpx"); R.compose(org, SAMPLE_REPORT, tmp_path / "r.hwpx")
    rank = {"□": 0, "ㅇ": 1, "○": 1, "◦": 1, "❍": 1, "-": 2}
    for f in ("p.hwpx", "r.hwpx"):
        stack = {}
        for mk, pt in _para_pts(tmp_path / f):
            r = rank[mk]; stack[r] = pt
            for k in range(r):
                if k in stack: assert pt <= stack[k], (f, mk, pt, stack)
            for k in [k for k in stack if k > r]: del stack[k]


def test_inline_ref_not_attached(tmp_path):
    """문장 끝 「참고 1」 표시 앞에 묶음 빈칸."""
    C.compose("행정안전부", SAMPLE, tmp_path / "a.hwpx")
    sec = zipfile.ZipFile(tmp_path / "a.hwpx").read("Contents/section0.xml").decode()
    assert re.search(r'<hp:nbSpace/></hp:t></hp:run><hp:run charPrIDRef="\d+"><hp:rect\b', sec)


# ── 문단 앞머리 라벨·장평 ──
def _label_runs(path):
    from hwpx_doc import Hwpx
    d = Hwpx(path); out = []
    for *_, p in d.paragraphs():
        if "<hp:tbl" in p: continue
        runs = re.findall(r'<hp:run charPrIDRef="(\d+)"[^>]*><hp:t>(.*?)</hp:t></hp:run>', p, re.S)
        if len(runs) >= 2 and re.fullmatch(r"\s*[□ㅇ○◦❍-]\s+", runs[0][1]) and C.HEAD_LABEL.fullmatch(runs[1][1]):
            out.append((runs[0][1].strip(), runs[1][1], d.char(runs[1][0]), runs[1][0]))
    return out


@pytest.mark.parametrize("org", ["행정안전부", "국세청", ""])
def test_head_label_fixed_width(org, tmp_path):
    """(목적)·(대상) 같은 앞머리 라벨: 자간 0·장평 100 고정 → 같은 계층·같은 글자 수 라벨은 같은 글자 모양(같은 폭)."""
    files = [tmp_path / "r.hwpx"]; R.compose(org, SAMPLE_REPORT, files[0])
    if org: files.append(tmp_path / "p.hwpx"); C.compose(org, SAMPLE, files[1])
    found = 0
    for f in files:
        labs = _label_runs(f); found += len(labs)
        for mk, lab, ch, cid in labs: assert ch["spacing"] == 0 and ch["ratio"] == 100, (lab, ch)
        by = {}
        for mk, lab, ch, cid in labs: by.setdefault((mk, len(lab)), set()).add(cid)
        assert all(len(v) == 1 for v in by.values()), by
    assert found >= 4


@pytest.mark.parametrize("org", ["행정안전부", "국세청", "과학기술정보통신부", ""])
def test_ratio_range(org, tmp_path):
    """본문 문단 장평은 95~100%, 기호·라벨 조각은 100%."""
    c = R.compose(org, SAMPLE_REPORT, tmp_path / "r.hwpx")
    assert all(95 <= it["sp"][1] <= 100 for it in c.items.values())
    if org:
        c = C.compose(org, SAMPLE, tmp_path / "p.hwpx")
        assert all(95 <= it["sp"][1] <= 100 for it in c.items.values())


def test_ratio_used_when_it_saves_a_line():
    """한 줄을 조금 넘는 문단은 장평·자간으로 한 줄에 들어감."""
    c = C.Composer("행정안전부"); L_ = c.level("l2")
    w = C.WIDTHS.get(L_["font"]) or C.WIDTHS["바탕"]
    base = "가" * int(c.text_w / (L_["pt"] * 100 * w.get("hangul", 1.0)))
    txt = base[:-2] + " 나다라마"   # 1줄 + 2~3자 넘침
    sp, ra = c.pick_spacing(txt, L_, 0)
    from fit import wrap
    assert len(wrap(txt, L_["pt"], sp, c.text_w, c.text_w, ra, w, True)) == 1 and 95 <= ra <= 100
