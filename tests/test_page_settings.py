"""쪽 설정(편집 용지)이 모든 문서 종류에 들어가고, 표가 본문폭을 넘지 않는지 (SPEC_page_settings.md). 작성 Mia(윤승미)"""
import copy, json, re, sys, zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from korean_report_hwpx import server as SV  # noqa: E402
from sample_release import SAMPLE  # noqa: E402
from sample_report import SAMPLE_REPORT  # noqa: E402
import sample_official as SO  # noqa: E402

PKG = Path(SV.__file__).parent
PAGE = json.loads((PKG / "rules" / "_쪽설정.json").read_text("utf-8"))
D = PAGE["default"]
OFFICIAL = next(v for v in vars(SO).values() if isinstance(v, dict) and "approval" in v)
KEYS = ("width", "height", "left", "right", "top", "bottom", "header", "footer")


def tpl_page(org):
    return json.loads((PKG / "templates" / f"{org}.json").read_text("utf-8"))["page"]


def page_of(xml):
    assert xml.count("<hp:secPr") == 1
    pp = re.search(r'<hp:pagePr[^>]*width="(\d+)" height="(\d+)"', xml)
    mg = re.search(r"<hp:margin ([^>]*)/>", xml)
    assert pp and mg
    d = {k: int(v) for k, v in re.findall(r'(\w+)="(\d+)"', mg.group(1))}
    d.update(width=int(pp.group(1)), height=int(pp.group(2)))
    return d


def tables(xml):
    out = []
    for m in re.finditer(r"<hp:tbl\b", xml):
        sz = re.search(r'<hp:sz width="(\d+)"', xml[m.end():])
        out.append(int(sz.group(1)))
    return out


def test_rule_file():
    assert D == {"width": 59528, "height": 84188, "left": 5669, "right": 5669, "top": 4252, "bottom": 4252, "header": 2835, "footer": 2835, "gutter": 0}
    assert PAGE["text_width"] == 48190
    src = json.dumps(PAGE["출처"], ensure_ascii=False)
    assert "2,667" in src and "2640" in src and "1817" in src


CASES = [
    ("report", "", SAMPLE_REPORT, {}, None),
    ("report", "", SAMPLE_REPORT, {"report_kind": "internal"}, None),
    ("report", "", SAMPLE_REPORT, {"style": "simplified"}, None),
    ("report", "행정안전부", SAMPLE_REPORT, {}, "행정안전부"),
    ("report", "국방부", SAMPLE_REPORT, {}, "국방부"),
    ("press_release", "과학기술정보통신부", SAMPLE, {}, "과학기술정보통신부"),
    ("press_release", "행정안전부", SAMPLE, {}, "행정안전부"),
    ("press_release", "재외동포청", SAMPLE, {}, "재외동포청"),
    ("official", "", OFFICIAL, {}, None),
    ("official", "", OFFICIAL, {"style": "simplified"}, None),
]


@pytest.mark.parametrize("t,org,s,kw,tpl", CASES, ids=[f"{c[0]}-{c[1] or '공통'}-{'-'.join(c[3].values()) or 'std'}" for c in CASES])
def test_every_doc_has_page_settings(t, org, s, kw, tpl, tmp_path):
    r = SV.build_document(copy.deepcopy(s), t, org, str(tmp_path / "p.hwpx"), **kw)
    xml = zipfile.ZipFile(r["hwpx"]).read("Contents/section0.xml").decode("utf-8")
    pg = page_of(xml)
    want = dict(D)
    if tpl: want.update({k: v for k, v in tpl_page(tpl).items() if k in KEYS})
    for k in KEYS:
        assert abs(pg[k] - want[k]) <= 2, (k, pg[k], want[k])
    assert abs(pg["width"] - 59528) <= 2 and abs(pg["height"] - 84188) <= 2
    assert pg["left"] == pg["right"] == 5669
    tw = pg["width"] - pg["left"] - pg["right"]
    ws = tables(xml)
    assert ws, "표가 하나 이상 있어야 함(샘플)"
    assert max(ws) <= tw, (max(ws), tw)


@pytest.mark.parametrize("org", ["과학기술정보통신부", "행정안전부"])
def test_target_ministries_use_most_common_margins(org):
    p = tpl_page(org)
    assert [round(p[k] / 283.465) for k in ("top", "bottom", "header", "footer")] == [15, 15, 10, 10]
    assert PAGE["기관값"][org]["top_bottom_header_footer_mm"] == [15, 15, 10, 10]


def test_common_report_and_official_use_default(tmp_path):
    for t, s in (("report", SAMPLE_REPORT), ("official", OFFICIAL)):
        r = SV.build_document(copy.deepcopy(s), t, "", str(tmp_path / f"{t}.hwpx"))
        pg = page_of(zipfile.ZipFile(r["hwpx"]).read("Contents/section0.xml").decode("utf-8"))
        assert (pg["top"], pg["bottom"], pg["header"], pg["footer"]) == (4252, 4252, 2835, 2835)


def test_wide_official_table_fits(tmp_path):
    s = copy.deepcopy(OFFICIAL)
    s["body"].append({"type": "table", "rows": [[f"열{i}" for i in range(9)], ["가나다라마바사아자차카타파하" * 2] * 9]})
    r = SV.build_document(s, "official", "", str(tmp_path / "w.hwpx"))
    xml = zipfile.ZipFile(r["hwpx"]).read("Contents/section0.xml").decode("utf-8")
    pg = page_of(xml)
    assert max(tables(xml)) <= pg["width"] - pg["left"] - pg["right"]


def test_blank_page_settings_helper():
    import blank as B
    assert B.page_settings("") == D
    p = B.page_settings("과학기술정보통신부")
    for k in KEYS: assert abs(p[k] - tpl_page("과학기술정보통신부")[k]) <= 0
    assert 'top="4252"' in B.sec_pr({}) and 'header="2835"' in B.sec_pr({})
