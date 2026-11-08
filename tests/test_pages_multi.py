"""여러 쪽 보고서 분량 예측 — 정답은 한글 실측(fixtures_pages/README.md). 작성 Mia(윤승미)"""
import json, os, sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from korean_report_hwpx import server as SV  # noqa: E402

FX = Path(__file__).parent / "fixtures_pages"
MANIFEST = json.loads((FX / "manifest.json").read_text("utf-8"))


def est(e):
    d = json.loads((FX / e["file"]).read_text("utf-8"))
    r = SV.check_structure(d, doc_type="report", style=e["style"], report_kind=e["report_kind"])
    assert isinstance(r.get("분량"), dict), r
    return r["분량"]


# ── 1. 쪽수가 한글 실측과 같다 ──
@pytest.mark.parametrize("e", MANIFEST, ids=[e["file"] for e in MANIFEST])
def test_pages_match_hangul(e):
    q = est(e)
    assert q["전체_쪽수"] == e["전체_쪽수"], (e, q)
    if "본문_쪽수" in e:
        assert q["본문_쪽수"] == e["본문_쪽수"], (e, q)


# ── 2. 마지막 쪽 채움이 한글 실측과 ±0.02 안 ──
FILL = [e for e in MANIFEST if "마지막쪽_채움" in e]


@pytest.mark.parametrize("e", FILL, ids=[e["file"] for e in FILL])
def test_fill_matches_hangul(e):
    q = est(e)
    assert abs(q["마지막쪽_채움"] - e["마지막쪽_채움"]) <= 0.02, (e, q)


def test_manifest_size():
    assert len(MANIFEST) == 54 and len(FILL) >= 10


# ── 3. 내부 결재 서식은 내부 결재 기준으로 잰다 ──
def test_report_kind_passed():
    e = next(e for e in MANIFEST if e["report_kind"] == "internal")
    d = json.loads((FX / e["file"]).read_text("utf-8"))
    r = SV.check_structure(d, doc_type="report", report_kind="internal")
    assert r["분량"]["전체_쪽수"] == e["전체_쪽수"]


# ── 4. 예측은 파일을 남기지 않고 입력을 바꾸지 않는다 ──
def test_estimate_leaves_no_files_and_keeps_input(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    e = MANIFEST[0]
    d = json.loads((FX / e["file"]).read_text("utf-8"))
    before = json.dumps(d, ensure_ascii=False, sort_keys=True)
    out_dir = Path(SV.out_dir())
    listing = sorted(os.listdir(out_dir)) if out_dir.exists() else []
    SV.check_structure(d, doc_type="report")
    assert json.dumps(d, ensure_ascii=False, sort_keys=True) == before
    assert list(tmp_path.iterdir()) == []
    assert (sorted(os.listdir(out_dir)) if out_dir.exists() else []) == listing


# ── 5. build_document도 같은 분량을 돌려준다 ──
def test_build_reports_same_estimate(tmp_path):
    e = next(e for e in MANIFEST if e["file"].startswith("big_"))
    d = json.loads((FX / e["file"]).read_text("utf-8"))
    r = SV.build_document(d, doc_type="report", out_path=str(tmp_path / "x"))
    assert r["분량"]["본문_쪽수"] == e["본문_쪽수"] and r["분량"]["전체_쪽수"] == e["전체_쪽수"]
