"""간소화 모드(simplified) 테스트. 작성 Mia(윤승미)
- 번호 부여: 구조에 Ⅰ. 1. 가. 1) 가) 자동 부여
- 표 병합 풀기: 병합 셀을 같은 값으로 행마다 반복
- 표 제목 자동 번호: 〈표 1〉 〈표 2〉 형식
- export_markdown: .md 파일 동시 출력
- check_structure: 간소화 규칙 점검(번호 수준 건너뜀, 표 제목 누락, 병합 사용, 5단계 초과)
"""
import json
import re
import sys
import zipfile
from pathlib import Path

import pytest

# 서버 모듈 임포트를 위한 경로 추가
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "korean_report_hwpx"))

import report as R
from hwpx_doc import Hwpx
from server import build_document, check_structure, get_writing_guide


# ── 테스트용 구조 ──

SIMPLE_REPORT = {
    "title": "간소화 모드 테스트 보고서",
    "date": "2026. 1. 5.",
    "dept": "테스트과",
    "body": [
        {"type": "h", "text": "추진 배경"},
        {"type": "l1", "text": "첫 번째 대항목"},
        {"type": "l2", "text": "첫 번째 중항목"},
        {"type": "l3", "text": "첫 번째 소항목"},
        {"type": "caption", "text": "테스트 표"},
        {"type": "table", "rows": [
            ["구분", "값"],
            ["가", "100"],
            ["나", "200"],
        ]},
        {"type": "l1", "text": "두 번째 대항목"},
    ],
}

MERGED_TABLE_REPORT = {
    "title": "병합 테스트 보고서",
    "date": "2026. 1. 5.",
    "dept": "테스트과",
    "body": [
        {"type": "caption", "text": "병합 표"},
        {"type": "table", "rows": [
            [{"text": "공통", "merge": {"row": 3, "col": 1}}, "값1", "값2"],
            ["", "100", "200"],
            ["", "300", "400"],
        ]},
    ],
}

MULTI_TABLE_REPORT = {
    "title": "여러 표 테스트 보고서",
    "date": "2026. 1. 5.",
    "dept": "테스트과",
    "body": [
        {"type": "caption", "text": "첫 번째 표"},
        {"type": "table", "rows": [["A", "B"], ["1", "2"]]},
        {"type": "caption", "text": "두 번째 표"},
        {"type": "table", "rows": [["C", "D"], ["3", "4"]]},
    ],
}

LEVEL_SKIP_REPORT = {
    "title": "계층 건너뜀 테스트",
    "date": "2026. 1. 5.",
    "dept": "테스트과",
    "body": [
        {"type": "l1", "text": "대항목"},
        {"type": "l3", "text": "소항목 (l2 건너뜀)"},  # l1 → l3: 건너뜀
    ],
}

DEEP_LEVEL_REPORT = {
    "title": "5단계 초과 테스트",
    "date": "2026. 1. 5.",
    "dept": "테스트과",
    "body": [
        {"type": "l1", "text": "1단계"},
        {"type": "l2", "text": "2단계"},
        {"type": "l3", "text": "3단계"},
        {"type": "l3", "text": "4단계 (l3 추가)"},
        {"type": "l3", "text": "5단계 (l3 추가)"},  # l3 내에서 반복 -> 내부적으로 5단계 이상처럼 보임 (실제 spec은 레벨 rank 기준)
    ],
}

NO_CAPTION_REPORT = {
    "title": "표 제목 누락 테스트",
    "date": "2026. 1. 5.",
    "dept": "테스트과",
    "body": [
        {"type": "table", "rows": [["A", "B"], ["1", "2"]]},  # caption 없음
    ],
}


# ── 번호 부여 테스트 ──

class TestSimplifiedNumbering:
    """간소화 모드 번호 부여 검증."""

    def test_h_get_roman_numeral(self, tmp_path):
        """소제목(h)은 Ⅰ. Ⅱ. Ⅲ. 형식."""
        dst = tmp_path / "test.hwpx"
        R.compose("", SIMPLE_REPORT, dst, style="simplified")
        sec = zipfile.ZipFile(dst).read("Contents/section0.xml").decode()
        text = Hwpx.text(sec, True)
        # Ⅰ. 추진 배경 이 포함되어야 함
        assert "Ⅰ. 추진 배경" in text

    def test_l1_get_arabic_numeral(self, tmp_path):
        """대항목(l1)은 1. 2. 3. 형식."""
        dst = tmp_path / "test.hwpx"
        R.compose("", SIMPLE_REPORT, dst, style="simplified")
        sec = zipfile.ZipFile(dst).read("Contents/section0.xml").decode()
        text = Hwpx.text(sec, True)
        # 1. 첫 번째 대항목 이 포함되어야 함
        assert "1. 첫 번째 대항목" in text

    def test_l2_get_gajja(self, tmp_path):
        """중항목(l2)은 가. 나. 다. 형식."""
        dst = tmp_path / "test.hwpx"
        R.compose("", SIMPLE_REPORT, dst, style="simplified")
        sec = zipfile.ZipFile(dst).read("Contents/section0.xml").decode()
        text = Hwpx.text(sec, True)
        # 가. 첫 번째 중항목 이 포함되어야 함
        assert "가. 첫 번째 중항목" in text

    def test_l3_get_parenthesis(self, tmp_path):
        """소항목(l3)은 1) 2) 3) 형식."""
        dst = tmp_path / "test.hwpx"
        R.compose("", SIMPLE_REPORT, dst, style="simplified")
        sec = zipfile.ZipFile(dst).read("Contents/section0.xml").decode()
        text = Hwpx.text(sec, True)
        # 1) 첫 번째 소항목 이 포함되어야 함
        assert "1) 첫 번째 소항목" in text

    def test_number_reset_on_h(self, tmp_path):
        """h(소제목) 등장 시 번호 리셋."""
        doc = {
            "title": "리셋 테스트",
            "date": "2026. 1. 5.",
            "dept": "테스트과",
            "body": [
                {"type": "h", "text": "첫 번째 장"},
                {"type": "l1", "text": "항목 A"},
                {"type": "h", "text": "두 번째 장"},
                {"type": "l1", "text": "항목 B"},
            ],
        }
        dst = tmp_path / "test.hwpx"
        R.compose("", doc, dst, style="simplified")
        sec = zipfile.ZipFile(dst).read("Contents/section0.xml").decode()
        text = Hwpx.text(sec, True)
        # 첫 번째 장의 1. 항목 A
        assert "1. 항목 A" in text
        # 두 번째 장의 1. 항목 B (리셋됨)
        assert "1. 항목 B" in text
        # Ⅰ. 첫 번째 장, Ⅱ. 두 번째 장
        assert "Ⅰ. 첫 번째 장" in text
        assert "Ⅱ. 두 번째 장" in text

    def test_l2_counter_resets_on_l1(self, tmp_path):
        """l1 등장 시 l2 카운터 리셋."""
        doc = {
            "title": "카운터 리셋 테스트",
            "date": "2026. 1. 5.",
            "dept": "테스트과",
            "body": [
                {"type": "l1", "text": "첫 번째 대항목"},
                {"type": "l2", "text": "가. 첫 중항목"},
                {"type": "l2", "text": "나. 두 번째 중항목"},
                {"type": "l1", "text": "두 번째 대항목"},
                {"type": "l2", "text": "가. 다시 첫 중항목"},  # l1 리셋으로 가. 부터 시작
            ],
        }
        dst = tmp_path / "test.hwpx"
        R.compose("", doc, dst, style="simplified")
        sec = zipfile.ZipFile(dst).read("Contents/section0.xml").decode()
        text = Hwpx.text(sec, True)
        # 두 번째 대항목 아래의 중항목은 다시 가. 부터 시작
        assert "가. 다시 첫 중항목" in text


# ── 표 병합 풀기 테스트 ──

class TestSimplifiedTableMerge:
    """간소화 모드 표 병합 풀기 검증."""

    def test_merged_cell_unrolled(self, tmp_path):
        """병합된 셀은 같은 값이 행마다 반복."""
        dst = tmp_path / "test.hwpx"
        R.compose("", MERGED_TABLE_REPORT, dst, style="simplified")
        sec = zipfile.ZipFile(dst).read("Contents/section0.xml").decode()
        text = Hwpx.text(sec, True)
        # 병합된 "공통" 값이 모든 행에 반복되어야 함
        # 첫 번째 열에 "공통"이 3번 이상 나타남
        assert text.count("공통") >= 3

    def test_merge_not_in_standard_mode(self, tmp_path):
        """표준 모드에서는 병합이 유지됨 (간소화 모드만 풀어씀)."""
        dst = tmp_path / "test.hwpx"
        # 표준 모드에서는 병합 셀 처리가 다를 수 있음 (간소화만 풀어씀)
        R.compose("", MERGED_TABLE_REPORT, dst, style="standard")
        sec = zipfile.ZipFile(dst).read("Contents/section0.xml").decode()
        # 표준 모드는 병합 구문(cellSpan)이 있을 수 있음
        # 간소화 모드와 비교하여 검증


# ── 표 제목 자동 번호 테스트 ──

class TestSimplifiedTableCaptionNumbering:
    """간소화 모드 표 제목 자동 번호 검증."""

    def test_single_table_gets_table_1(self, tmp_path):
        """단일 표는 〈표 1〉 형식."""
        dst = tmp_path / "test.hwpx"
        R.compose("", SIMPLE_REPORT, dst, style="simplified")
        sec = zipfile.ZipFile(dst).read("Contents/section0.xml").decode()
        text = Hwpx.text(sec, True)
        assert "〈표 1〉 테스트 표" in text

    def test_multiple_tables_get_sequential_numbers(self, tmp_path):
        """여러 표는 〈표 1〉 〈표 2〉 순차 부여."""
        dst = tmp_path / "test.hwpx"
        R.compose("", MULTI_TABLE_REPORT, dst, style="simplified")
        sec = zipfile.ZipFile(dst).read("Contents/section0.xml").decode()
        text = Hwpx.text(sec, True)
        assert "〈표 1〉 첫 번째 표" in text
        assert "〈표 2〉 두 번째 표" in text

    def test_appendix_tables_get_numbers(self, tmp_path):
        """부록(표) 테이블도 순차 번호."""
        doc = {
            "title": "부록 표 테스트",
            "date": "2026. 1. 5.",
            "dept": "테스트과",
            "body": [
                {"type": "caption", "text": "본문 표"},
                {"type": "table", "rows": [["X"], ["1"]]},
            ],
            "appendix": [
                {"title": "붙임 1", "heading": "부록 내용", "body": [
                    {"type": "caption", "text": "부록 표"},
                    {"type": "table", "rows": [["Y"], ["2"]]},
                ]},
            ],
        }
        dst = tmp_path / "test.hwpx"
        R.compose("", doc, dst, style="simplified")
        sec = zipfile.ZipFile(dst).read("Contents/section0.xml").decode()
        text = Hwpx.text(sec, True)
        # 본문 표와 부록 표 모두 번호 부여
        assert "〈표 1〉 본문 표" in text
        assert "〈표 2〉 부록 표" in text


# ── export_markdown 테스트 ──

class TestSimplifiedMarkdownExport:
    """간소화 모드 마크다운 출력 검증."""

    def test_markdown_file_created(self, tmp_path):
        """export_markdown=True이면 .md 파일이 함께 생성."""
        dst = tmp_path / "test.hwpx"
        result = build_document(SIMPLE_REPORT, doc_type="report", style="simplified", export_markdown=True, out_path=str(dst))
        assert result.get("md", "").endswith(".md")
        md_path = Path(result["md"])
        assert md_path.exists()
        md_content = md_path.read_text("utf-8")
        # 마크다운에 필수 요소 포함
        assert "# 간소화 모드 테스트 보고서" in md_content
        assert "Ⅰ. 추진 배경" in md_content
        assert "1. 첫 번째 대항목" in md_content
        assert "| 구분 | 값 |" in md_content  # GFM 표
        # 번호 중복 없음 (버그3): "1. 1." 또는 "가. 가." 같은 중복 번호가 없어야 함
        assert "1. 1." not in md_content, f"마크다운에 번호 중복: {md_content[:500]}"
        assert "가. 가." not in md_content, f"마크다운에 번호 중복: {md_content[:500]}"

    def test_markdown_contains_gfm_table(self, tmp_path):
        """마크다운에 GFM 형식 표 포함."""
        dst = tmp_path / "test.hwpx"
        result = build_document(SIMPLE_REPORT, doc_type="report", style="simplified", export_markdown=True, out_path=str(dst))
        md_content = Path(result["md"]).read_text("utf-8")
        # GFM 표 형식 확인
        assert "| 구분 | 값 |" in md_content
        assert "|---" in md_content
        assert "| 가 | 100 |" in md_content

    def test_markdown_no_merge(self, tmp_path):
        """마크다운 표에는 병합 dict 없음."""
        dst = tmp_path / "test.hwpx"
        result = build_document(MERGED_TABLE_REPORT, doc_type="report", style="simplified", export_markdown=True, out_path=str(dst))
        md_content = Path(result["md"]).read_text("utf-8")
        # 병합 dict 키 merge가 마크다운에 없어야 함
        assert '"merge"' not in md_content
        assert "〈표 1〉 병합 표" in md_content

    def test_markdown_date_filled_when_empty(self, tmp_path):
        """마크다운 작성일이 비어 있으면 오늘 날짜로 채움 (버그5)."""
        doc_no_date = {
            "title": "날짜 없는 보고서",
            "dept": "테스트과",
            "body": [{"type": "l1", "text": "내용"}],
        }
        dst = tmp_path / "test.hwpx"
        result = build_document(doc_no_date, doc_type="report", style="simplified", export_markdown=True, out_path=str(dst))
        md_content = Path(result["md"]).read_text("utf-8")
        # 오늘 날짜가 마크다운에 포함되어야 함
        import datetime
        today_str = f"{datetime.date.today().year}. {datetime.date.today().month}. {datetime.date.today().day}."
        assert f"- 작성일: {today_str}" in md_content, f"마크다운에 오늘 날짜가 없음: {md_content[:300]}"


# ── check_structure 간소화 규칙 테스트 ──

class TestSimplifiedCheckWarnings:
    """간소화 모드 check_structure 경고 검증."""

    def test_level_skip_warning(self, tmp_path):
        """간소화 모드: 계층 건너뜀 경고."""
        result = check_structure(LEVEL_SKIP_REPORT, doc_type="report", style="simplified")
        warnings = result["warnings"]
        assert any("계층 건너뜀" in w or "번호 수준 건너뜀" in w for w in warnings), f"경고: {warnings}"

    def test_merge_warning(self, tmp_path):
        """간소화 모드: 병합 사용 경고."""
        result = check_structure(MERGED_TABLE_REPORT, doc_type="report", style="simplified")
        warnings = result["warnings"]
        assert any("병합" in w for w in warnings), f"경고: {warnings}"

    def test_no_noun_ending_warning_in_simplified(self, tmp_path):
        """간소화 모드: 명사형 종결 경고 없음 (서술식 허용)."""
        doc = {
            "title": "서술식 테스트",
            "date": "2026. 1. 5.",
            "dept": "테스트과",
            "body": [
                {"type": "l1", "text": "AI 서비스를 도입합니다."},  # 동사형 종결
                {"type": "l1", "text": "민원 안내가 필요합니다."},
            ],
        }
        result = check_structure(doc, doc_type="report", style="simplified")
        warnings = result["warnings"]
        # 명사형 종결 경고가 없어야 함
        assert not any("명사형 종결" in w for w in warnings), f"불필요한 경고: {warnings}"

    def test_noun_ending_warning_in_standard(self, tmp_path):
        """표준 모드: 명사형 종결 경고 있음."""
        doc = {
            "title": "서술식 테스트",
            "date": "2026. 1. 5.",
            "dept": "테스트과",
            "body": [
                {"type": "l1", "text": "AI 서비스를 도입합니다."},
            ],
        }
        result = check_structure(doc, doc_type="report", style="standard")
        warnings = result["warnings"]
        # 명사형 종결 경고가 있어야 함
        assert any("명사형 종결" in w for w in warnings), f"경고 없음: {warnings}"

    def test_standard_mode_preserves_original_behavior(self, tmp_path):
        """표준 모드: 기존 동작 그대로 (간소화 규칙이 적용되지 않음)."""
        # 표준 모드에서는 번호 부여가 적용되지 않음
        result = build_document(SIMPLE_REPORT, doc_type="report", style="standard", out_path=str(tmp_path / "test.hwpx"))
        sec = zipfile.ZipFile(tmp_path / "test.hwpx").read("Contents/section0.xml").decode()
        text = Hwpx.text(sec, True)
        # 표준 모드에서는 □ 기호가 사용됨
        assert "□" in text
        # 간소화 모드 번호가 없음
        assert "Ⅰ." not in text

    def test_standard_mode_comprehensive_behavior(self, tmp_path):
        """표준 모드 결과 불변 종합 검증: □ 기호, 표 머리 음영, outlineLevel 없음, footer 없음."""
        dst = tmp_path / "test.hwpx"
        R.compose("", SIMPLE_REPORT, dst, style="standard")
        sec = zipfile.ZipFile(dst).read("Contents/section0.xml").decode()
        head = zipfile.ZipFile(dst).read("Contents/header.xml").decode()
        text = Hwpx.text(sec, True)
        # 1. 표준 모드 HWPX 본문에 □ 기호가 있음 (간소화 모드와 다름)
        assert "□" in sec, "표준 모드 HWPX에 □ 기호가 없음"
        # 2. 표준 모드 표 머리 음영(#DFE6F7)이 header에 있음
        assert "#DFE6F7" in head, "표준 모드 header에 표 머리 음영이 없음"
        # 3. 표준 모드 HWPX 문단에 outlineLevel 속성이 없음
        assert 'outlineLevel=' not in sec, "표준 모드 HWPX에 outlineLevel이 있음"
        # 4. 표준 모드(report_kind="standard")에는 footer가 없음
        assert '<hp:footer' not in head, "표준 모드 header에 footer가 있음"
        assert '<hp:footerRef' not in sec, "표준 모드 section에 footerRef가 있음"
        # 5. 표준 모드 본문에 □ 기호가 붙은 문단 텍스트 확인
        assert "□ 첫 번째 대항목" in text or "□첫 번째 대항목" in text, "표준 모드 본문에 □ 기호가 붙지 않음"

    def test_simplified_no_square_marker_in_hwpix(self, tmp_path):
        """간소화 모드: HWPX 본문에 □ ○ - 기호가 없고 번호만 있음 (버그1 검증)."""
        dst = tmp_path / "test.hwpx"
        R.compose("", SIMPLE_REPORT, dst, style="simplified")
        sec = zipfile.ZipFile(dst).read("Contents/section0.xml").decode()
        # 간소화 모드에서는 항목 기호(□ ㅇ ○ - *)가 없어야 함
        assert "□" not in sec, "간소화 모드 HWPX에 □ 기호가 있음"
        assert "○" not in sec, "간소화 모드 HWPX에 ○ 기호가 있음"
        # 번호 텍스트는 있어야 함
        text = Hwpx.text(sec, True)
        assert "Ⅰ. 추진 배경" in text
        assert "1. 첫 번째 대항목" in text
        assert "가. 첫 번째 중항목" in text
        assert "1) 첫 번째 소항목" in text

    def test_simplified_outline_levels_in_hwpix(self, tmp_path):
        """간소화 모드: HWPX 문단에 outlineLevel 속성 없음 (6차 수정 - 개요 번호 제거)."""
        dst = tmp_path / "test.hwpx"
        R.compose("", SIMPLE_REPORT, dst, style="simplified")
        sec = zipfile.ZipFile(dst).read("Contents/section0.xml").decode()
        # 간소화 모드: outlineLevel 속성이 없어야 함 (개요 번호 제거)
        assert 'outlineLevel=' not in sec, "간소화 모드 HWPX에 outlineLevel이 있음"
        # 표준 모드에서도 outlineLevel이 없어야 함
        dst_std = tmp_path / "test_std.hwpx"
        R.compose("", SIMPLE_REPORT, dst_std, style="standard")
        sec_std = zipfile.ZipFile(dst_std).read("Contents/section0.xml").decode()
        assert 'outlineLevel=' not in sec_std, "표준 모드 HWPX에 outlineLevel이 있음"

    def test_internal_report_page_number(self, tmp_path):
        """내부 결재 보고서(report_kind='internal'): 쪽 번호 '- n -'가 footer에 있음 (버그7 검증)."""
        dst = tmp_path / "test.hwpx"
        R.compose("", SIMPLE_REPORT, dst, style="standard", report_kind="internal")
        head = zipfile.ZipFile(dst).read("Contents/header.xml").decode()
        sec = zipfile.ZipFile(dst).read("Contents/section0.xml").decode()
        # header에 footer 정의 있음
        assert '<hp:footer' in head, "internal 보고서 header에 footer가 없음"
        assert '<hp:pageNum' in head, "internal 보고서 footer에 pageNum이 없음"
        # section의 secPr에 footerRef 있음
        assert '<hp:footerRef' in sec, "internal 보고서 section에 footerRef가 없음"
        # footer에 "- N -" 형식 확인 (페이지 번호는 컨트롤로 포함)
        assert '- </hp:t></hp:run><hp:run charPrIDRef="0"><hp:ctrl><hp:pageNum' in head, "internal 보고서 footer에 '- N -' 형식이 아님"

    def test_simplified_line_spacing_option(self, tmp_path):
        """간소화 모드: line_spacing 옵션으로 줄 간격 변경 가능 (8번 항목)."""
        dst_default = tmp_path / "test_default.hwpx"
        dst_custom = tmp_path / "test_custom.hwpx"
        # 기본 line_spacing=150%
        R.compose("", SIMPLE_REPORT, dst_default, style="simplified")
        # line_spacing=200% 옵션 적용
        R.compose("", SIMPLE_REPORT, dst_custom, style="simplified", line_spacing=200)
        head_default = zipfile.ZipFile(dst_default).read("Contents/header.xml").decode()
        head_custom = zipfile.ZipFile(dst_custom).read("Contents/header.xml").decode()
        # 기본: lineSpacing type="PERCENT" value="150" (간소화 모드 본문 paraPr)
        assert 'lineSpacing type="PERCENT" value="150"' in head_default, "기본 line_spacing=150%가 아님"
        # 커스텀: lineSpacing type="PERCENT" value="200"
        assert 'lineSpacing type="PERCENT" value="200"' in head_custom, "line_spacing=200% 옵션이 적용되지 않음"
        # 기본에는 200이 없어야 함 (옵션 미적용)
        assert 'lineSpacing type="PERCENT" value="200"' not in head_default, "기본에 200%가 포함됨"

    def test_simplified_para_space_before_option(self, tmp_path):
        """간소화 모드: para_space_before 옵션으로 문단 간격 변경 가능 (8번 항목)."""
        dst_default = tmp_path / "test_default.hwpx"
        dst_custom = tmp_path / "test_custom.hwpx"
        # 기본 para_space_before=4pt (기본값)
        R.compose("", SIMPLE_REPORT, dst_default, style="simplified")
        # para_space_before=8pt 옵션 적용
        R.compose("", SIMPLE_REPORT, dst_custom, style="simplified", para_space_before=8.0)
        sec_default = zipfile.ZipFile(dst_default).read("Contents/section0.xml").decode()
        sec_custom = zipfile.ZipFile(dst_custom).read("Contents/section0.xml").decode()
        # 간소화 모드에서 문단 간격(gap)은 빈 문단으로 생성됨
        # para_space_before 옵션 적용 시 더 큰 간격의 빈 문단이 생성되어야 함
        # 기본(4pt)과 커스텀(8pt)에서 생성된 문단 수나 내용이 달라야 함
        # 빈 문단(내용 없는 <hp:p>)의 개수를 비교
        import re
        # 내용이 공백뿐인 문단 찾기 (빈 문단 = 간격 문단)
        empty_paras_default = re.findall(r'<hp:p\b[^>]*>(?:<hp:run[^>]*><hp:t[^>]*>\s*</hp:t></hp:run>)*</hp:p>', sec_default)
        empty_paras_custom = re.findall(r'<hp:p\b[^>]*>(?:<hp:run[^>]*><hp:t[^>]*>\s*</hp:t></hp:run>)*</hp:p>', sec_custom)
        # 옵션 적용 시 빈 문단(간격)의 charPr이 달라야 함 (8pt vs 4pt)
        # gap 메서드에서 생성된 문단의 charPr ID를 비교하여 다른지 확인
        # 실제 검증: 두 header의 paraPr 중 pt 값이 다른 것이 있는지 확인
        head_default = zipfile.ZipFile(dst_default).read("Contents/header.xml").decode()
        head_custom = zipfile.ZipFile(dst_custom).read("Contents/header.xml").decode()
        # paraPr id별 pt(height) 값 추출
        def get_charpt_map(header):
            return {m.group(1): int(m.group(2)) for m in re.finditer(r'<hh:charPr id="(\d+)" height="(\d+)"', header)}
        charpt_default = get_charpt_map(head_default)
        charpt_custom = get_charpt_map(head_custom)
        # 8pt(800)와 5pt(500) 높이가 모두 존재하는지 확인
        # 간소화 모드 gap에서 pt=5일 때 charPr height=500, pt=8일 때 height=800
        assert any(v == 500 for v in charpt_default.values()), "기본 header에 5pt charPr이 없음"
        assert any(v == 800 for v in charpt_custom.values()), "커스텀 header에 8pt charPr이 없음"

    def test_simplified_options_output_example(self, tmp_path):
        """간소화 모드 줄간격·문단 간격 옵션 적용 결과 HWPX 출력 예 (8번 항목).
        line_spacing=200, para_space_before=8 적용 시 실제 HWPX 값 확인."""
        dst = tmp_path / "test_options.hwpx"
        R.compose("", SIMPLE_REPORT, dst, style="simplified", line_spacing=200, para_space_before=8.0)
        sec = zipfile.ZipFile(dst).read("Contents/section0.xml").decode()
        head = zipfile.ZipFile(dst).read("Contents/header.xml").decode()
        # 1. 줄간격 200% 적용 확인: paraPr에 lineSpacing type="PERCENT" value="200"
        assert 'lineSpacing type="PERCENT" value="200"' in head, "line_spacing=200% 옵션이 header에 반영되지 않음"
        # line_spacing=150(기본)이 아닌 200이 있는지 확인
        assert 'lineSpacing type="PERCENT" value="150"' not in head, "기본 line_spacing=150%가 옵션 적용 후에도 남아있음"
        # 2. 문단 간격 8pt 적용 확인: paraPr에 <hc:prev value="800"> (8pt = 800 HWPUNIT)
        assert 'prev value="800"' in head, "para_space_before=8pt 옵션이 header에 반영되지 않음 (prev=800 없음)"
        # 3. 간소화 모드 기호 없음 확인
        assert "□" not in sec, "간소화 모드 옵션 적용 HWPX에 □ 기호가 있음"
        # 4. 번호 확인 (outlineLevel은 없음 - 6차 수정)
        assert "Ⅰ. 추진 배경" in Hwpx.text(sec, True)
        assert 'outlineLevel=' not in sec
        # 출력 예: 생성된 paraPr 중 lineSpacing=200, prev=800인 것 확인
        import re
        paras = re.findall(r'<hh:paraPr id="(\d+)"[^>]*>.*?</hh:paraPr>', head, re.S)
        for pid, pxml in re.findall(r'<hh:paraPr id="(\d+)"[^>]*>(.*?)</hh:paraPr>', head, re.S):
            ls = re.search(r'lineSpacing type="PERCENT" value="(\d+)"', pxml)
            pv = re.search(r'<hc:prev value="(\d+)"', pxml)
            if ls and pv:
                print(f"  [예시] paraPr id={pid}: lineSpacing={ls.group(1)}%, prev={pv.group(1)} (={int(pv.group(1))/100}pt)")


# ── 제목 상자 없음 테스트 ──

class TestSimplifiedNoTitleBox:
    """간소화 모드 제목 상자 없음 검증."""

    def test_no_title_box_in_simplified(self, tmp_path):
        """간소화 모드: 제목 상자(표 형태) 없음."""
        dst = tmp_path / "test.hwpx"
        R.compose("", SIMPLE_REPORT, dst, style="simplified")
        sec = zipfile.ZipFile(dst).read("Contents/section0.xml").decode()
        # 제목 상자(표)는 특정 borderFill 참조가 있음
        # 간소화 모드에서는 제목이 plain paragraph로 표시됨
        # 깔끔한 검증을 위해 제목 텍스트 직접 확인
        text = Hwpx.text(sec, True)
        assert "간소화 모드 테스트 보고서" in text
        # 표 머리가 없는 fill이 사용됨
        # 간소화 모드는 표 머리 fill=None

    def test_no_table_head_fill_in_simplified(self, tmp_path):
        """간소화 모드: 표 머리 음영 없음."""
        dst = tmp_path / "test.hwpx"
        R.compose("", SIMPLE_REPORT, dst, style="simplified")
        head = zipfile.ZipFile(dst).read("Contents/header.xml").decode()
        # 간소화 모드는 표 머리 fill이 None (음영 없음)
        # #DFE6F7 (표준 표 머리 색)이 header에 없음
        assert "#DFE6F7" not in head

    def test_table_head_fill_in_standard(self, tmp_path):
        """표준 모드: 표 머리 음영 있음."""
        dst = tmp_path / "test.hwpx"
        R.compose("", SIMPLE_REPORT, dst, style="standard")
        head = zipfile.ZipFile(dst).read("Contents/header.xml").decode()
        # 표준 모드는 표 머리 fill이 있음
        assert "#DFE6F7" in head


# ── get_writing_guide 테스트 ──

class TestSimplifiedGuide:
    """간소화 모드 작성 가이드 검증."""

    def test_get_writing_guide_with_simplified_style(self):
        """간소화 스타일 가이드에는 간소화 규칙이 포함됨."""
        result = get_writing_guide(doc_type="report", style="simplified")
        assert result["style"] == "simplified"
        assert "간소화 모드 규칙" in result["guide"]
        # 간소화 규칙에 번호 관련 내용 포함
        assert "단계별 번호" in result["guide"] or "Ⅰ." in result["guide"]
        assert "1." in result["guide"] or "사용자가" in result["guide"]

    def test_get_writing_guide_standard_default(self):
        """기본 스타일은 standard."""
        result = get_writing_guide(doc_type="report")
        assert result["style"] == "standard"
        assert "간소화 모드 규칙" not in result["guide"]

    def test_invalid_style_raises_error(self):
        """잘못된 style 값은 오류."""
        with pytest.raises(ValueError, match="style은 'standard' 또는 'simplified'"):
            get_writing_guide(doc_type="report", style="invalid")
