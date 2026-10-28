"""기안문 항목 내어쓰기 = 번호 뒤 탭 + 같은 거리 탭 위치 + 같은 거리 내어쓰기 (Claude 작성 2026-10-28) — 수정 금지.
생성 파일의 XML을 직접 읽어 확인한다. 근거: docs/SPEC_official_tab_hang.md, 공문서작성법 「표시위치 및 띄우기」."""
import copy, json, re, zipfile
from pathlib import Path

import pytest

from hwpx_doc import Hwpx
from sample_official import SAMPLE_OFFICIAL as S

RULES = json.loads((Path(__file__).resolve().parents[1] / "korean_report_hwpx" / "rules_official" / "_공통.json").read_text("utf-8"))
C = int(float(RULES["body"]["pt"]) * 100)
H = 2 * C
STEP = int(RULES["body"].get("indent_per_level", 2) / 2 * C)
MARK = r"(?:\d+\.|[가-힣]\.|\d+\)|[가-힣]\)|\(\d+\)|\([가-힣]\)|[①-⑳]|[㉮-㉻])"


def _build(doc, tmp):
    import importlib
    import korean_report_hwpx.server as srv
    srv = importlib.reload(srv)
    r = srv.build_document(doc, doc_type="official", out_path=str(tmp / "기안문.hwpx"))
    z = zipfile.ZipFile(r["hwpx"])
    return z.read("Contents/section0.xml").decode(), z.read("Contents/header.xml").decode()


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    return _build(S, tmp_path_factory.mktemp("tab"))


def _paras(sec):
    return re.findall(r"<hp:p\b[^>]*>.*?</hp:p>", sec, re.S)


def _first_t(p):
    m = re.search(r"<hp:t>(.*?)</hp:t>", p, re.S)
    return m.group(1) if m else ""


def _pr(head, p):
    pid = re.search(r'paraPrIDRef="(\d+)"', p).group(1)
    return re.search(r'<hh:paraPr\b[^>]*id="%s"[^>]*>.*?</hh:paraPr>' % pid, head, re.S).group(0)


def _margin(pr, name):
    blk = re.search(r"<hp:case\b.*?</hp:case>", pr, re.S)
    src = blk.group(0) if blk else pr
    m = re.search(r'<hc:%s\s+value="(-?\d+)"' % name, src)
    return int(m.group(1)) if m else 0


def _tabs(head, pr):
    tid = re.search(r'tabPrIDRef="(\d+)"', pr).group(1)
    t = re.search(r'<hh:tabPr\b[^>]*id="%s"[^>]*?(?:/>|>.*?</hh:tabPr>)' % tid, head, re.S).group(0)
    case = re.search(r"<hp:case\b.*?</hp:case>", t, re.S)
    dflt = re.search(r"<hp:default>.*?</hp:default>", t, re.S)
    pos = lambda blk: [int(x) for x in re.findall(r'<hh:tabItem\b[^>]*pos="(\d+)"', blk.group(0))] if blk else []
    return t, pos(case), pos(dflt)


def _items(sec):
    return [p for p in _paras(sec) if re.match(MARK + r"<hp:tab\b", _first_t(p))]


def test_mark_then_tab_no_space(built):
    sec, head = built
    items = _items(sec)
    assert len(items) >= 6                                   # 1. 가. 나. 1) 2) 2. 가. …
    for p in items:
        assert re.match(MARK + r'<hp:tab width="\d+" leader="0" type="1"/>\S', _first_t(p)), _first_t(p)[:40]
    body = re.sub(r"<hp:tbl\b.*?</hp:tbl>", "", sec, flags=re.S)        # 표 칸(날짜 "2026. 10. 31." 등)은 항목이 아님
    plain = [p for p in _paras(body) if re.match(MARK + r" ", Hwpx.text(p))]
    assert not [p for p in plain if re.match(MARK + " ", _first_t(p))]   # 번호 뒤 공백으로 띄운 항목이 남지 않음


def test_hang_equals_tab_stop_and_levels(built):
    sec, head = built
    lefts = set()
    for p in _items(sec):
        pr = _pr(head, p)
        assert _margin(pr, "intent") == -H, Hwpx.text(p)[:20]
        left = _margin(pr, "left"); lefts.add(left)
        assert left % STEP == 0
        t, case, dflt = _tabs(head, pr)
        assert 'autoTabLeft="1"' in t
        assert case == [H] and dflt == [2 * H]                 # 탭 위치 = 내어쓰기 거리(한글 원본처럼 default는 2배)
        assert 'type="LEFT"' in t and 'unit="HWPUNIT"' in t
    assert {0, STEP, 2 * STEP} <= lefts                       # 1. → 가. → 1) 한 글자(2타)씩


def test_tab_properties_count(built):
    sec, head = built
    m = re.search(r'<hh:tabProperties itemCnt="(\d+)">(.*?)</hh:tabProperties>', head, re.S)
    assert int(m.group(1)) == len(re.findall(r"<hh:tabPr\b", m.group(2)))


def test_attachments_tabs(built):
    sec, head = built
    ps = _paras(sec)
    label = RULES["attachments"]["label"] + RULES["attachments"]["label_gap"]
    i = next(k for k, p in enumerate(ps) if _first_t(p).startswith(label))
    assert re.match(re.escape(label) + r'1\.<hp:tab\b[^>]*/>\S', _first_t(ps[i]))
    assert re.match(r'<hp:tab\b[^>]*/>2\.<hp:tab\b[^>]*/>\S', _first_t(ps[i + 1]))
    for p in (ps[i], ps[i + 1]):
        pr = _pr(head, p)
        assert _margin(pr, "intent") == -5 * C and _margin(pr, "left") == 0
        t, case, dflt = _tabs(head, pr)
        assert case == [3 * C, 5 * C] and dflt == [6 * C, 10 * C]


def test_single_item_no_tab(tmp_path):
    doc = copy.deepcopy(S)
    doc["body"] = [{"type": "l1", "text": "다음과 같이 알려 드립니다."}, {"type": "l2", "text": "기간: 2026. 11. 2."}]
    sec, head = _build(doc, tmp_path)
    p = next(p for p in _paras(sec) if "다음과 같이" in Hwpx.text(p))
    assert "<hp:tab" not in p and _margin(_pr(head, p), "intent") == 0


def test_text_reads_tab_as_space(built):
    sec, head = built
    txt = Hwpx.text(sec, True)
    assert "1. 국산 AI 모델" in txt and "가. 실증 기간" in txt and "1.국산" not in txt
