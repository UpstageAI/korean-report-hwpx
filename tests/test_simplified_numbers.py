"""간소화 모드 번호가 목록 끝을 넘어도 오류 없이 이어진다. 작성 Mia(윤승미)"""
import re, sys, zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from korean_report_hwpx import server as SV  # noqa: E402


def _text(hwpx):
    x = zipfile.ZipFile(hwpx).read("Contents/section0.xml").decode("utf-8")
    return "".join(re.findall(r"<hp:t>([^<]*)</hp:t>", x))


def test_many_headings(tmp_path):
    body = []
    for i in range(14):
        body += [{"type": "h", "text": f"가나다 {i}"}, {"type": "l1", "text": "가나다라 마바사"}]
    r = SV.build_document({"title": "가나다", "date": "2026. 11. 8.", "body": body}, doc_type="report",
                          style="simplified", out_path=str(tmp_path / "h"), export_markdown=True)
    t = _text(r["hwpx"]); md = Path(r["md"]).read_text("utf-8")
    for want in ("Ⅹ. ", "Ⅺ. ", "Ⅻ. ", "XIII. ", "XIV. "):
        assert want in t and want in md, want


def test_many_sub_items(tmp_path):
    body = [{"type": "h", "text": "가나다"}, {"type": "l1", "text": "가나다라"}]
    body += [{"type": "l2", "text": f"마바사 {i}"} for i in range(16)]
    r = SV.build_document({"title": "가나다", "date": "2026. 11. 8.", "body": body}, doc_type="report",
                          style="simplified", out_path=str(tmp_path / "s"))
    t = _text(r["hwpx"])
    assert "하. 마바사 13" in t and "거. 마바사 14" in t and "너. 마바사 15" in t


def test_existing_numbers_stripped():
    assert SV._strip_existing_number("Ⅺ. 가나다") == "가나다"
    assert SV._strip_existing_number("XIII. 가나다") == "가나다"
    assert SV._strip_existing_number("거. 가나다") == "가나다"
