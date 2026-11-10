"""표 본문 칸 정렬은 열 단위로 맞춘다: 열의 모든 칸이 한 줄이면 가운데, 한 칸이라도 줄이 바뀌면 그 열 본문 전체 양쪽 정렬. 작성 Mia(윤승미)"""
import re, zipfile
from korean_report_hwpx.engine import report as R


def _cells(rows, tmp_path):
    doc = {"title": "가나다 보고", "date": "2026. 11. 7.", "dept": "",
           "body": [{"type": "h", "text": "Ⅰ. 현황"}, {"type": "caption", "text": "가나다 현황"}, {"type": "table", "rows": rows}], "appendix": []}
    R.compose("", doc, tmp_path / "t.hwpx")
    z = zipfile.ZipFile(tmp_path / "t.hwpx")
    sec, head = z.read("Contents/section0.xml").decode(), z.read("Contents/header.xml").decode()
    align = {m.group(1): m.group(2) for m in re.finditer(r'<hh:paraPr id="(\d+)".*?<hh:align horizontal="(\w+)"', head, re.S)}
    out = {}
    for tc in re.findall(r"<hp:tc\b.*?</hp:tc>", sec, re.S):
        txt = "".join(re.findall(r"<hp:t>([^<]*)</hp:t>", tc)).strip()
        pid = re.search(r'<hp:p [^>]*paraPrIDRef="(\d+)"', tc).group(1)
        if txt: out[txt] = align[pid]
    return out


def test_one_line_column_all_center(tmp_path):
    rows = [["구분", "내용", "일정"],
            ["가나다", "라마바사 아자차카 타파하", "11월"],
            ["라마바", "사아자차 카타파하 가나다라 마바사", "12월"],
            ["사아자", "차카타파", "1월"]]
    a = _cells(rows, tmp_path)
    for v in ("라마바사 아자차카 타파하", "사아자차 카타파하 가나다라 마바사", "차카타파", "11월", "12월"):
        assert a[v] == "CENTER", (v, a[v])        # 짧은 숫자·날짜 칸도 가운데


def test_wrapping_column_all_justify(tmp_path):
    long = "가나다라 마바사아 자차카타 파하가나 다라마바 사아자차 카타파하 가나다라 마바사아 자차카타 파하가나 다라마바"
    rows = [["구분", "내용"], ["가나다", long], ["라마바", "차카타파"]]
    a = _cells(rows, tmp_path)
    assert a[long] in ("JUSTIFY", "LEFT")
    assert a["차카타파"] == a[long]          # 같은 열 짧은 칸도 같은 정렬
    assert a["가나다"] == "CENTER" and a["구분"] == "CENTER"   # 첫 열·머리는 가운데 그대로
