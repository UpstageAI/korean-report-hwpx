"""structure를 JSON 문자열로 줘도 객체로 준 것과 같은 문서."""
import asyncio
import json
import re
import zipfile
from pathlib import Path

import pytest

from korean_report_hwpx import server as SV
from sample_report import SAMPLE_REPORT


def _section_xml(p):
    """요소 id는 만들 때마다 달라질 수 있으므로 지우고 비교한다."""
    with zipfile.ZipFile(p) as z:
        x = z.read("Contents/section0.xml").decode("utf-8")
    return re.sub(r'\b(id|instid|zOrder)="[^"]*"', "", x)


def test_build_document_json_string_same(tmp_path):
    a = SV.build_document(SAMPLE_REPORT, "report", "", str(tmp_path / "a.hwpx"))
    b = SV.build_document(json.dumps(SAMPLE_REPORT, ensure_ascii=False), "report", "", str(tmp_path / "b.hwpx"))
    assert Path(b["hwpx"]).exists()
    assert a["warnings"] == b["warnings"]
    assert _section_xml(a["hwpx"]) == _section_xml(b["hwpx"])


def test_check_structure_json_string():
    a = SV.check_structure(SAMPLE_REPORT, "report")
    b = SV.check_structure(json.dumps(SAMPLE_REPORT, ensure_ascii=False), "report")
    assert a == b


def test_build_from_structure_json_string(tmp_path):
    r = SV.build_from_structure(json.dumps(SAMPLE_REPORT, ensure_ascii=False), "report", "", str(tmp_path / "c.hwpx"))
    assert Path(r["hwpx"]).exists()


def test_bad_json_string_raises_valueerror(tmp_path):
    with pytest.raises(ValueError, match="structure"):
        SV.build_document("{title: 깨짐", "report", "", str(tmp_path / "d.hwpx"))


def test_json_string_not_object_raises(tmp_path):
    with pytest.raises(ValueError, match="structure"):
        SV.check_structure('["a", "b"]', "report")


def test_schema_accepts_string():
    tools = asyncio.run(SV.mcp.list_tools())
    for name in ("build_document", "check_structure", "build_from_structure"):
        t = next(t for t in tools if t.name == name)
        sch = json.dumps(t.input_schema["properties"]["structure"], ensure_ascii=False)
        assert '"string"' in sch and '"object"' in sch, name
