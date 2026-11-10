"""통합 시나리오(2026-11-10)에서 나온 고칠 점: □ 날짜 오탐, 날짜 빈칸 규칙, 기안문 입력 형태 오류 문구, 도구 설명, list_ministries 한 덩어리, 1쪽 보고서 안내.
생성 문서 XML은 바뀌지 않는다(검증·경고·설명만). 보완 Claude(뼈대 Solar Pro 4)"""
import asyncio, json, zipfile
from pathlib import Path

import pytest

from korean_report_hwpx import server as SV
from korean_report_hwpx.engine.hwpx_doc import Hwpx

DENSE = Path.home() / "work/mcp/통합테스트/시나리오_1110/공문서/dense_calls.json"


def _l1(text, **kw):
    return SV.check_structure({"title": "제목", "body": [{"type": "l1", "text": text}]}, "report", **kw)["warnings"]


# ── 1. □(l1) 두괄식 점검이 공문서 날짜 온점을 문장 끝으로 세지 않음 ──
@pytest.mark.parametrize("text", [
    "과학기술정보통신부는 2026. 11. 3.(화) ○○ 설명회 개최 예정",
    "11. 2. 김세웅 단장 취임, 민간 개발자와 함께 서비스 개발",
    "접수 11. 3.(화)~11. 12.(목), 기획·개발 등 7개 분야 민간 전문가 채용 붙임 1",
    "자체 파악(2026.11.) 기준 외주 비율 3.5%p 증가, 10p. 참조",
    "'26. 10. 8.(목) 회의 결과 No. 3 안건 보류… 재검토 필요",
])
def test_l1_date_decimal_abbrev_not_sentences(text):
    assert not [w for w in _l1(text) if "두괄식" in w], _l1(text)


@pytest.mark.parametrize("text", ["첫 조치를 완료했다. 그리고 다음 단계를 추진함", "A안을 검토함. B안도 검토함.", "□ 첫 문장이다. 둘째 문장이다."])
def test_l1_two_real_sentences_still_warn(text):
    assert [w for w in _l1(text) if "두괄식" in w and "문장이 2개" in w]


def test_count_sentences_ref_tag_not_a_sentence():
    assert SV._count_sentences("세부 일정은 붙임으로 정리함 붙임 1") == 0
    assert SV._count_sentences("2026. 11. 3.(화) 개최 예정임. 참고 2") == 1


@pytest.mark.skipif(not DENSE.exists(), reason="시나리오 입력 파일 없음")
def test_dense_doc1_structure_ok():
    a = json.loads(DENSE.read_text("utf-8"))[0]["args"]
    r = SV.check_structure(a["structure"], a["doc_type"], target_pages=a["target_pages"])
    assert r["ok"], r["warnings"]


# ── 2. 날짜 빈칸: 본문은 묶음 빈칸(<hp:nbSpace/>)으로 저장, 표 칸은 보통 빈칸 — 압축이 아니며 규칙을 가이드에 적음 ──
def test_body_date_space_is_nbspace_and_table_keeps_plain_space(tmp_path):
    s = {"title": "날짜 표기", "body": [
        {"type": "l1", "text": "추진단은 11. 3.(화) 2차 공개 모집을 발표함"},
        {"type": "caption", "text": "일정"}, {"type": "table", "rows": [["구분", "일시"], ["접수", "2026. 11. 3.(화) ~ 11. 12.(목)"]]}]}
    r = SV.build_document(s, "report", out_path=str(tmp_path / "d.hwpx"))
    sec = zipfile.ZipFile(r["hwpx"]).read("Contents/section0.xml").decode()
    assert "11.<hp:nbSpace/>3.(화)" in sec and "11.3.(화)" not in sec          # 본문: 묶음 빈칸(줄 끝에서 안 갈라짐), 붙여 쓰지 않음
    assert "<hp:t>2026. 11. 3.(화) ~ 11. 12.(목)</hp:t>" in sec                 # 표 칸: 보통 빈칸 그대로
    assert "11. 3.(화)" in Hwpx.text(sec, True)                                 # 읽으면 '11. 3.(화)'
    g = SV.get_writing_guide("report")["guide"]
    assert "묶음 빈칸" in g and "'11.3.'처럼 붙여 쓰지 않는다" in g


# ── 3. 기안문 입력 형태: 문자열 body·납작한 approval → 스택 추적 대신 기대 형태를 적은 한국어 오류 ──
def _official(**over):
    s = json.loads(json.dumps(SV.OFFICIAL_EXAMPLE, ensure_ascii=False)); s.update(over); return s


def test_official_body_as_strings_is_clear_error(tmp_path):
    bad = _official(body=["첫 항목 문장입니다.", "둘째 항목: 2026. 7. 1. ~ 11. 30."])
    with pytest.raises(ValueError, match="body 항목은") as ei:
        SV.check_structure(bad, "official")
    assert '"type"' in str(ei.value) and "l1" in str(ei.value) and "str" in str(ei.value)
    with pytest.raises(ValueError, match="body 항목은"):
        SV.build_document(bad, "official", out_path=str(tmp_path / "x.hwpx"))
    assert not (tmp_path / "x.hwpx").exists()


def test_official_flat_approval_is_clear_error(tmp_path):
    bad = _official(approval={"drafter": "주무관 김철수", "reviewers": ["정보화담당관"], "approver": "시장"})
    with pytest.raises(ValueError, match="approval.drafter") as ei:
        SV.check_structure(bad, "official")
    assert "title" in str(ei.value) and "주무관 김철수" in str(ei.value)
    with pytest.raises(ValueError, match="approval.drafter"):
        SV.build_document(bad, "official", out_path=str(tmp_path / "y.hwpx"))
    bad2 = _official(approval={"drafter": {"title": "주무관", "name": "김철수", "mark": "★"}, "reviewers": ["정보화담당관 이영희"], "approver": {"title": "시장"}})
    with pytest.raises(ValueError, match="approval.reviewers"):
        SV.check_structure(bad2, "official")
    bad3 = _official(doc_no="정보화담당관-1234")
    with pytest.raises(ValueError, match="doc_no"):
        SV.check_structure(bad3, "official")
    assert SV.check_structure(_official(), "official")["ok"]


def test_official_errors_reach_mcp_client_as_text():
    """MCP 경로: 'Error executing tool check_structure'만 오지 않고 한국어 안내가 간다."""
    bad = _official(body=["문장 하나"])
    with pytest.raises(Exception) as ei:
        asyncio.run(SV.mcp.call_tool("check_structure", {"structure": bad, "doc_type": "official"}))
    assert "body 항목은" in str(ei.value)


# ── 4. 도구 설명 ──
def test_tool_descriptions_name_official_and_subfields():
    tools = {t.name: t for t in asyncio.run(SV.mcp.list_tools())}
    assert "'official'" in tools["get_writing_guide"].description
    bd = tools["build_document"].description
    for k in ("drafter", "reviewers", "approver", "coordinators", "issue_date", "disclosure", "문자열 목록 아님"):
        assert k in bd, k
    dp = tools["draft_press_structure"]
    assert "facts_template" in dp.description and '"headline"' in dp.description
    facts_schema = dp.input_schema["properties"]["facts"]
    assert "anyOf" in facts_schema and {"type": "object", "additionalProperties": True} in facts_schema["anyOf"] or facts_schema.get("type") == "object"


def test_draft_press_structure_prose_error_names_template():
    with pytest.raises(ValueError) as ei:
        SV.draft_press_structure("과기정통부가 11월 3일 전문임기제공무원 19명을 모집한다고 밝혔다.", ministry="과학기술정보통신부")
    msg = str(ei.value)
    assert "facts_template" in msg and "press_release" in msg and "Expecting value" not in msg


# ── 5. list_ministries: TextContent 하나(JSON 배열) ──
def test_list_ministries_single_json_array():
    r = asyncio.run(SV.mcp.call_tool("list_ministries", {}))
    assert len(r.content) == 1
    arr = json.loads(r.content[0].text)
    assert isinstance(arr, list) and len(arr) == 53 and arr[-1]["기관"] == "공통(미지정)"
    assert json.loads(SV.list_ministries()) == arr


# ── 6. 1쪽 보고서 안내 ──
def test_onepage_guide_fill_not_cut_and_agency_bold_note():
    g = SV.get_writing_guide("report")["guide"]
    for k in ("꽉 채우는 문서", "단순 삭제하지", "핵심 수치·표로 압축", "주요 내용마다 붙임", "HY헤드라인M", "공통 서식으로 만든다"):
        assert k in g, k
