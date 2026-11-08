"""짧은 표는 쪽을 나누지 않음 (0.5.2, Claude 2026-11-08).

배경: 표가 모두 '줄 단위로 나눔(TABLE)·떠 있는 개체'라, 쪽 끝에 머리 줄만 남고 본문이 다음 쪽으로 넘어가는 일이 있었다(검토서 데모).
본문 높이 1/3 이하 표는 글자처럼 취급(treatAsChar=1)·나누지 않음(NONE) — 표 제목(keepWithNext)과 함께 통째로 넘어간다.
떠 있는 표에 NONE만 주면 표만 다음 쪽으로 가고 뒤 본문이 앞으로 올라와 순서가 바뀌므로(한글 실측) 둘을 같이 바꾼다.
"""
import re, zipfile, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from korean_report_hwpx import server as SV  # noqa: E402


def _tables(doc, tmp_path):
    r = SV.build_document(doc, doc_type="report", out_path=str(tmp_path / "t"))
    x = zipfile.ZipFile(r["hwpx"]).read("Contents/section0.xml").decode("utf-8")
    return [(m.group(1), int(m.group(2)), re.search(r'treatAsChar="(\d)"', m.group(0)).group(1))
            for m in re.finditer(r'<hp:tbl [^>]*?pageBreak="(\w+)"[^>]*?rowCnt="(\d+)".*?</hp:tbl>', x, re.S)]


def _doc(rows):
    return {"title": "표 쪽 나눔 확인", "date": "2026. 11. 8.", "dept": "", "body": [
        {"type": "h", "text": "Ⅰ. 현황"}, {"type": "l1", "text": "구조를 바꾸는 대안을 비교함"},
        {"type": "table", "rows": [["대안", "내용", "세무 효과"]] + rows}]}


def test_short_table_is_inline_and_unsplit(tmp_path):
    rows = [["대표 개인 임차로 전환", "대표가 직접 계약·부담, 회사는 출장 여비만 지급", "가장 명확"],
            ["시가 사용료 수취", "회사 임차 유지, 대표에게 사용료를 받음", "부당행위 해소"],
            ["사택 규정 제정", "규정만 마련하고 현 구조 유지", "출자임원 예외가 아니므로 해결 안 됨"]]
    data = [t for t in _tables(_doc(rows), tmp_path) if t[1] == 4]
    assert data and data[0][0] == "NONE" and data[0][2] == "1"


def test_long_table_still_splits_by_row(tmp_path):
    rows = [[f"항목{i}", "내용 " * 12, f"{i * 1000:,}"] for i in range(40)]
    data = [t for t in _tables(_doc(rows), tmp_path) if t[1] == 41]
    assert data and data[0][0] == "TABLE" and data[0][2] == "0"
