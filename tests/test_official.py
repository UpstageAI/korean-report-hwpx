"""기안문(별지 제1호서식) 생성 검증 (Claude 작성 2026-10-14) — 수정 금지.
생성 파일의 XML을 직접 읽어 확인한다(내부 값이 아니라 결과물 기준). 근거: 규정 제7조④⑤, 시행규칙 제2조·제4조·제6조.
실행: .venv/bin/python -m pytest tests/test_official.py -q
"""
import json, re, zipfile
from pathlib import Path

import pytest

from hwpx_doc import Hwpx
from sample_official import SAMPLE_OFFICIAL as S, SAMPLE_INTERNAL as SI

RULES = json.loads((Path(__file__).resolve().parents[1] / "korean_report_hwpx" / "rules_official" / "_공통.json").read_text("utf-8"))


def _server():
    import importlib
    import korean_report_hwpx.server as srv
    return importlib.reload(srv)


def _build(doc, tmp, name, **kw):
    srv = _server()
    r = srv.build_document(doc, doc_type="official", out_path=str(tmp / name), **kw)
    z = zipfile.ZipFile(r["hwpx"])
    sec = z.read("Contents/section0.xml").decode()
    head = z.read("Contents/header.xml").decode()
    return r, z, sec, head, Hwpx.text(sec, True)


def _lines(sec):
    out = []
    for raw in re.findall(r"<hp:p\b.*?</hp:p>", sec, re.S):
        t = Hwpx.text(raw, True).strip()
        if t:
            out.append(t)
    return out


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    return _build(S, tmp_path_factory.mktemp("off"), "기안문.hwpx")


@pytest.fixture(scope="module")
def built_internal(tmp_path_factory):
    return _build(SI, tmp_path_factory.mktemp("off_i"), "내부결재.hwpx")


# ── 두문 ────────────────────────────────────────────────────────────────────
def test_header_block(built):
    r, z, sec, head, text = built
    lines = _lines(sec)
    assert lines[0] == S["org"]                                        # 행정기관명이 맨 위(제4조②1호)
    assert f"수신{RULES['head_line']['label_gap']}수신자 참조" in lines    # 수신자 여럿 → "수신자 참조"(제4조②2호나목)
    assert not any(l.startswith("(경유)") for l in lines)             # 경유 없음
    assert f"제목{RULES['head_line']['label_gap']}{S['title']}" in lines
    assert f'height="{int(RULES["org"]["pt"] * 100)}"' in head          # 기관명 글자 크기는 규칙값
    assert RULES["org"]["font"] in head


def test_internal_header(built_internal):
    r, z, sec, head, text = built_internal
    lines = _lines(sec)
    assert f"수신{RULES['head_line']['label_gap']}내부결재" in lines       # 제4조②2호가목
    assert not any(l.startswith("수신자") for l in lines)             # 수신자란 없음


# ── 본문: 항목 번호·들여쓰기·금액 경고 ───────────────────────────────────────
def test_item_numbering(built):
    r, z, sec, head, text = built
    lines = _lines(sec)
    assert any(l.startswith("1. 국산 AI 모델") for l in lines)
    assert any(l.startswith("가. 실증 기간") for l in lines)
    assert any(l.startswith("나. 실증 범위") for l in lines)
    assert any(l.startswith("1) 문서 기반") for l in lines)
    assert any(l.startswith("2) 민원 분류") for l in lines)
    assert any(l.startswith("2. 참여를 희망") for l in lines)
    assert any(l.startswith("가. 실증 지원 예산") for l in lines)         # 상위 항목이 바뀌면 하위 번호 초기화
    assert "1. 1." not in text and "가. 가." not in text


def test_indent_follows_level(built):
    r, z, sec, head, text = built
    # 2계층 문단의 왼쪽 여백이 1계층보다 크다(둘째 계층부터 2타 오른쪽, 규칙 indent_per_level)
    def left_of(startswith):   # 번호 뒤 탭(<hp:tab/>) — 문단 글은 Hwpx.text로 읽어 찾는다(2026-10-28 탭 맞춤 반영)
        p = next((p for p in re.findall(r"<hp:p\b[^>]*>.*?</hp:p>", sec, re.S) if Hwpx.text(p).startswith(startswith)), None)
        assert p, startswith
        pid = re.search(r'paraPrIDRef="(\d+)"', p).group(1)
        pr = re.search(r'<hh:paraPr\b[^>]*id="%s"[^>]*>.*?</hh:paraPr>' % pid, head, re.S).group(0)
        mg = re.search(r'<hc:left\s+value="(\d+)"', pr)
        return int(mg.group(1)) if mg else 0
    assert left_of("가. 실증 기간") > left_of("1. 국산 AI 모델")
    assert left_of("1) 문서 기반") > left_of("가. 실증 기간")


def test_amount_warning_only_when_korean_missing(tmp_path):
    srv = _server()
    doc = json.loads(json.dumps(S, ensure_ascii=False))
    doc["body"] = [{"type": "l1", "text": "지원 한도는 5,000,000원입니다."}]
    r = srv.build_document(doc, doc_type="official", out_path=str(tmp_path / "금액.hwpx"))
    assert any("한글 병기" in w for w in r["warnings"])                 # 시행규칙 제2조②
    doc["body"] = [{"type": "l1", "text": "지원 한도는 금5,000,000원(금오백만원)입니다."}]
    r = srv.build_document(doc, doc_type="official", out_path=str(tmp_path / "금액2.hwpx"))
    assert not any("한글 병기" in w for w in r["warnings"])


def test_date_normalized(built):
    r, z, sec, head, text = built
    assert "2026. 11. 2. ~ 2026. 12. 19." in text or "2026. 11. 02. ~ 2026. 12. 19." in text   # 영 제7조⑤: YYYY-MM-DD → 온점 표기
    assert "2026-11-02" not in text


# ── 붙임·끝 표시 ────────────────────────────────────────────────────────────
def test_attachments_and_end_mark(built):
    r, z, sec, head, text = built
    lines = _lines(sec)
    i = next(k for k, l in enumerate(lines) if l.startswith(RULES["attachments"]["label"]))
    assert lines[i].startswith(f"{RULES['attachments']['label']}{RULES['attachments']['label_gap']}1. 실증 참여 신청서 1부.")
    assert lines[i + 1].lstrip().startswith("2. 실증 참여 안내문 1부.")
    assert lines[i + 1].endswith(f"{RULES['end_mark']['gap']}{RULES['end_mark']['text']}")   # 붙임 마지막 글자에서 한 글자 띄우고 "끝."
    assert text.count(RULES["end_mark"]["text"]) == 1


def test_end_mark_after_table_without_attachments(tmp_path):
    srv = _server()
    doc = json.loads(json.dumps(S, ensure_ascii=False)); doc.pop("attachments")
    r = srv.build_document(doc, doc_type="official", out_path=str(tmp_path / "표끝.hwpx"))
    sec = zipfile.ZipFile(r["hwpx"]).read("Contents/section0.xml").decode()
    lines = _lines(sec)
    end = [l for l in lines if l.strip() == RULES["end_mark"]["text"] or l == f"{RULES['end_mark']['gap']}{RULES['end_mark']['text']}"]
    assert len(end) == 1 and Hwpx.text(sec, True).count(RULES["end_mark"]["text"]) == 1   # 표 아래 왼쪽에서 한 글자 띄운 "끝."(제4조⑤2호)
    assert lines.index(end[0]) > lines.index(next(l for l in lines if l.startswith("선정")))


def test_end_mark_on_last_text_line(built_internal):
    r, z, sec, head, text = built_internal
    lines = _lines(sec)
    last_body = next(l for l in lines if l.startswith("가. 2026. 11. 2.") or l.startswith("가. 2026. 11. 02."))   # 두 번째 1. 아래 첫 항목이라 '가.'(상위 바뀌면 초기화)
    assert last_body.endswith(f"{RULES['end_mark']['gap']}{RULES['end_mark']['text']}")


# ── 결문 ────────────────────────────────────────────────────────────────────
def test_closing_block(built):
    r, z, sec, head, text = built
    lines = _lines(sec)
    s = lines.index(S["sender"])
    assert f'height="{int(RULES["sender"]["pt"] * 100)}"' in head
    assert lines[s + 1] == f"{RULES['recipients']['label']}{RULES['recipients']['label_gap']}" + RULES["recipients"]["sep"].join(S["recipients"])
    assert "★주무관" in text and "디지털정부과장" in text and f"디지털정부국장{RULES['approval_table']['opinion_text']}" in text and "차관" in text
    assert f"{RULES['approval_table']['coordinator_label']}{RULES['approval_table']['label_gap']}정보공개정책과장" in text
    assert f"{RULES['footer_lines']['issue']}  디지털정부과-1234 (2026. 10. 14.)" in text
    assert RULES["footer_lines"]["receive"] + "  " not in text           # 접수 값이 없으면 접수란 생략
    assert f"{RULES['footer_lines']['zip']} 30112  세종특별자치시 한누리대로 411" in text and "www.mois.go.kr" in text
    assert f"{RULES['footer_lines']['phone']} 044-000-0000" in text and f"{RULES['footer_lines']['fax']} 044-000-0001" in text
    assert "○○○@korea.kr" in text and text.rstrip().endswith("공개")
    assert "○○○" not in re.sub(r"○○○@korea.kr", "", text)             # 서명 칸은 비움(자리표시 성명 없음)


def test_internal_closing_and_date(built_internal):
    r, z, sec, head, text = built_internal
    assert "디지털정부과-1235 (2026. 10. 14.)" in text                      # YYYY-MM-DD → YYYY. MM. DD.
    assert text.rstrip().endswith("비공개")


# ── 검증·안내·마크다운 ───────────────────────────────────────────────────────
def test_check_structure_rejects_bad_values():
    srv = _server()
    bad = json.loads(json.dumps(S, ensure_ascii=False)); bad["contact"]["disclosure"] = "공개함"
    with pytest.raises(Exception):
        srv.check_structure(bad, doc_type="official")
    bad = json.loads(json.dumps(S, ensure_ascii=False)); bad["approval"].pop("approver")
    with pytest.raises(Exception):
        srv.check_structure(bad, doc_type="official")
    bad = json.loads(json.dumps(S, ensure_ascii=False)); bad.pop("to")
    with pytest.raises(Exception):
        srv.check_structure(bad, doc_type="official")


def test_guide_and_listing():
    srv = _server()
    g = srv.get_writing_guide(doc_type="official")
    txt = json.dumps(g, ensure_ascii=False)
    for k in ("1., 가., 1), 가), (1), (가)", "끝", "붙임", "2026. 10. 14.", "금"):
        assert k in txt, k
    assert "official" in json.dumps(srv.list_ministries(), ensure_ascii=False) or "기안문" in json.dumps(srv.list_ministries(), ensure_ascii=False)
    rules = srv.get_rules(doc_type="official")
    assert rules["org"]["pt"] == RULES["org"]["pt"]


def test_markdown_export(tmp_path):
    srv = _server()
    r = srv.build_document(json.loads(json.dumps(S, ensure_ascii=False)), doc_type="official", out_path=str(tmp_path / "md.hwpx"), export_markdown=True)
    md = Path(r["md"]).read_text("utf-8")
    assert md.lstrip().startswith("# ") and "1. 국산 AI 모델" in md and "가. 실증 기간" in md and "붙임" in md and "끝." in md
    assert "행정안전부장관" in md and "디지털정부과-1234" in md


def test_no_press_release_or_report_artifacts(built):
    r, z, sec, head, text = built
    assert not [n for n in z.namelist() if n.startswith("BinData/")]
    for bad in ("보도자료", "보도시점", "책임자", "담당자", "붙임 1"):
        assert bad not in text, bad
    assert r["doc_type"] == "official" and "기안" in r["문서종류"]
