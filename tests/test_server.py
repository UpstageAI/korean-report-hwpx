"""MCP 서버: 외부 API 없음, 작성 가이드·구조 점검·생성(고칠 점) 흐름. 작성 Mia(윤승미)"""
import json, sys, zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from korean_gov_docs import server as SV  # noqa: E402
from sample_release import SAMPLE  # noqa: E402
from sample_report import SAMPLE_REPORT  # noqa: E402

PKG = Path(SV.__file__).parent


def test_no_external_api():
    assert not (PKG / "solar.py").exists()
    src = "".join(p.read_text("utf-8") for p in PKG.rglob("*.py"))
    for bad in ("solar", "upstage", "UPSTAGE", "urllib.request", "requests", "httpx", "SOLAR_"):
        assert bad not in src, bad
    for name in ("write_document", "make_press_release"): assert not hasattr(SV, name)


def test_tools_and_prompt_registered():
    import asyncio
    names = {t.name for t in asyncio.run(SV.mcp.list_tools())}
    assert {"get_writing_guide", "check_structure", "build_document", "build_from_structure", "list_ministries", "get_rules"} <= names
    assert not names & {"write_document", "make_press_release"}
    assert "writing_guide" in {p.name for p in asyncio.run(SV.mcp.list_prompts())}


@pytest.mark.parametrize("t", ["report", "press_release", "auto"])
def test_writing_guide(t):
    g = SV.get_writing_guide(t, "행정안전부")
    txt = g["guide"]
    for k in ("보도자료", "보고서", "지어내지", "기호", "참고 1" if t != "report" else "붙임 1"): assert k in txt
    if t != "press_release": assert "명사형" in txt and "두괄식" in txt
    ex = g.get("example_report") or g.get("example_press_release")
    assert SV.check_structure(ex, "press_release" if t == "press_release" else "report")["ok"]
    assert "공문서" in SV.writing_guide_prompt(t) or "보고서" in SV.writing_guide_prompt(t)


def test_check_structure_warnings():
    bad = {"title": "", "body": [{"type": "l1", "text": "□ 첫 문장이다. 둘째 문장이다."}, {"type": "l3", "text": "— 소항목"},
                                 {"type": "zz", "text": "x"}, {"type": "table", "rows": "x"}]}
    w = " ".join(SV.check_structure(bad)["warnings"])
    for k in ("title", "기호", "알 수 없는 type", "두괄식", "명사형", "건너뜀", "2차원"): assert k in w, k
    assert SV.check_structure(SAMPLE_REPORT)["ok"]


def test_build_document_report(tmp_path):
    s = json.loads(json.dumps(SAMPLE_REPORT)); s["body"][1]["text"] = "ㅇ " + s["body"][1]["text"]
    r = SV.build_document(s, "report", "", str(tmp_path / "a.hwpx"))
    assert Path(r["hwpx"]).exists() and r["기관"] == "공통(미지정)" and r["warnings"]
    assert not r["structure"]["body"][1]["text"].startswith("ㅇ")
    assert (tmp_path / "a.json").exists()
    zipfile.ZipFile(r["hwpx"]).testzip()


def test_build_press_and_alias(tmp_path):
    r = SV.build_from_structure(SAMPLE, "press_release", "행정안전부", str(tmp_path / "b.hwpx"))
    assert r["doc_type"] == "press_release" and Path(r["hwpx"]).exists()
    with pytest.raises(ValueError): SV.build_document(SAMPLE, "press_release", "", str(tmp_path / "c.hwpx"))
