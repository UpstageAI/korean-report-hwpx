"""내어쓰기: 둘째 줄은 항상 기호 뒤 첫 글자(괄호면 괄호)에 맞춤. 앞머리 라벨 문단도 라벨 없는 같은 계층 문단과 같음."""
import json, re

import pytest

import compose as C
import fit as F
import report as R


def intent(c, xml):
    pid = re.search(r'paraPrIDRef="(\d+)"', xml).group(1)
    el = re.search(r'<hh:paraPr id="%s".*?</hh:paraPr>' % pid, c.header, re.S).group(0)
    return -int(re.search(r'<hc:intent value="(-?\d+)"', el).group(1))


def base_hang(L_):
    return int(round((0.5 * L_["lead"] + C.MARK_W.get(L_["mark"], 1.0) + 0.5 * max(1, L_["gap"])) * L_["pt"] * 100))


@pytest.mark.parametrize("mk", [lambda: C.Composer("행정안전부"), lambda: R.ReportComposer("")])
@pytest.mark.parametrize("lv", ["l1", "l2"])
@pytest.mark.parametrize("label", ["(방식) ", "〔일정〕 ", "[대상자] "])
def test_label_hang_equals_plain(mk, lv, label):
    c = mk(); L_ = c.level(lv)
    body = "누리집·모바일 앱·무인민원발급기 등 여러 경로로 신청할 수 있도록 접수 창구를 넓히고 처리 결과를 문자로 알림"
    assert intent(c, c.item(lv, label + body)) == intent(c, c.item(lv, body)) == base_hang(L_)


@pytest.mark.parametrize("mk", [lambda: C.Composer("행정안전부"), lambda: R.ReportComposer("")])
@pytest.mark.parametrize("lv", ["l1", "l2", "l3"])
def test_no_label_unchanged(mk, lv):
    c = mk(); L_ = c.level(lv)
    xml = c.item(lv, "누리집·모바일 앱·무인민원발급기 등 여러 경로로 신청할 수 있도록 접수 창구를 넓히고 처리 결과를 문자로 알림")
    assert intent(c, xml) == base_hang(L_)


def test_release_align_follows_census():
    """보도시점 칸 정렬 = 원본 실측 최빈값(templates release.cells[].align)."""
    m = json.loads((C.ROOT / "rules/_보도시점정렬.json").read_text("utf-8"))
    for org, s in m["orgs"].items():
        t = C.load_layout(org) if org in C.ministries() else None
        if not t or not t.get("release"): continue
        for cell in t["release"]["cells"]:
            k = {"release_label": "보도_label", "release": "보도_value", "distribute_label": "배포_label", "distribute": "배포_value"}.get(cell["role"])
            if k and s.get(k): assert cell["align"] == s[k], (org, cell["role"])
