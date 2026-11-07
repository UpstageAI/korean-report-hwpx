"""분량 예측과 1쪽 보고서 점검 — 정답은 한글 실측(fixtures_onepage/README.md). 작성 Mia(윤승미)"""
import json, sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from korean_report_hwpx import server as SV  # noqa: E402

FX = Path(__file__).parent / "fixtures_onepage"


def load(name):
    return json.loads((FX / f"{name}.json").read_text("utf-8"))


def est(name, **kw):
    r = SV.check_structure(load(name), doc_type="report", **kw)
    assert isinstance(r.get("분량"), dict), r
    return r


# ── 1. 쪽수 예측이 한글 실측과 같다 ──
@pytest.mark.parametrize("name,body,total", [
    ("lines20_body1", 1, 1),
    ("lines21_body2", 2, 2), ("lines22_body2", 2, 2), ("lines23_body2", 2, 2), ("lines24_body2", 2, 2),
    ("lines26_body2", 2, 2), ("lines28_body2", 2, 2), ("lines30_body2", 2, 2), ("lines32_body2", 2, 2),
    ("run4_body1", 1, 3),
    ("run5_body2", 2, 7),
])
def test_pages_match_hangul(name, body, total):
    q = est(name)["분량"]
    assert q["본문_쪽수"] == body, (name, q)
    assert q["전체_쪽수"] == total, (name, q)


def test_fill_values():
    assert est("lines20_body1")["분량"]["마지막쪽_채움"] >= 0.85      # 20줄은 1쪽을 거의 채움
    assert est("lines21_body2")["분량"]["마지막쪽_채움"] <= 0.25      # 21줄은 2쪽에 한 줄만
    f = [est(n)["분량"]["마지막쪽_채움"] for n in ("lines24_body2", "lines28_body2", "lines32_body2")]
    assert f[0] < f[1] < f[2], f
    for n in ("lines20_body1", "run5_body2"):
        q = est(n)["분량"]
        assert 0 < q["마지막쪽_채움"] <= 1 and q["본문_줄수"] > 0


# ── 2. target_pages 경고 ──
def _w(r):
    return " / ".join(r["warnings"])


def test_over_target_warns():
    r = est("run5_body2", target_pages=1)
    assert "쪽을 넘음" in _w(r)
    assert not r["ok"]


def test_full_one_page_no_size_warning():
    r = est("lines20_body1", target_pages=1)
    assert "쪽을 넘음" not in _w(r) and "덜 참" not in _w(r)


def test_one_page_without_appendix_warns():
    r = est("lines20_body1", target_pages=1)        # 주요 내용 □가 여럿인데 붙임이 없음
    assert "붙임이 없음" in _w(r)
    r4 = est("run4_body1", target_pages=1)          # 붙임 2개 있음
    assert "붙임이 없음" not in _w(r4) and "쪽을 넘음" not in _w(r4)


def test_underfilled_one_page_warns():
    d = {"title": "가나다 결과 보고", "date": "2026. 11. 7.", "dept": "",
         "body": [{"type": "h", "text": "Ⅰ. 개요"},
                  {"type": "l1", "text": "가나다라 마바사 아자차 개최"},
                  {"type": "l2", "text": "가나다 라마바 참석"}],
         "appendix": [{"title": "붙임 1", "heading": "출처", "body": [{"type": "l1", "text": "가나다 라마바"}]}]}
    r = SV.check_structure(d, doc_type="report", target_pages=1)
    assert "덜 참" in _w(r), r["warnings"]


def test_no_target_no_size_warnings():
    r = est("run5_body2")                            # target_pages 없음 → 기존 동작(분량 경고 없음)
    for k in ("쪽을 넘음", "덜 참", "붙임이 없음"):
        assert k not in _w(r)


# ── 3. build_document도 분량을 돌려준다 ──
def test_build_returns_size(tmp_path):
    r = SV.build_document(load("run5_body2"), doc_type="report", out_path=str(tmp_path / "x.hwpx"), target_pages=1)
    assert r["분량"]["본문_쪽수"] == 2 and r["분량"]["전체_쪽수"] == 7
    assert "쪽을 넘음" in " / ".join(r["warnings"])
    assert Path(r["hwpx"]).exists()
    r2 = SV.build_document(load("lines20_body1"), doc_type="report", out_path=str(tmp_path / "y.hwpx"))
    assert r2["분량"]["본문_쪽수"] == 1


# ── 4. 다른 문서 종류는 영향 없음 ──
def test_other_doc_types_unaffected():
    from sample_release import SAMPLE
    r = SV.check_structure(SAMPLE, doc_type="press_release", target_pages=1)
    assert "쪽을 넘음" not in _w(r) and "붙임이 없음" not in _w(r) and "덜 참" not in _w(r)


# ── 5. 작성 가이드에 1쪽 보고서 규칙 ──
def test_guide_has_one_page_rules():
    g = SV.get_writing_guide("report")["guide"]
    assert "[1쪽 보고서]" in g
    for k in ("되묻지 않", "꽉 채운다", "붙임", "target_pages", "질문 3개"):
        assert k in g, k
    p = SV.get_writing_guide("press_release", ministry="행정안전부")["guide"]
    assert "[1쪽 보고서]" not in p


def test_server_instructions_mention_target_pages():
    assert "target_pages" in (SV.mcp.instructions or "")
