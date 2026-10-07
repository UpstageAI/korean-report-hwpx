"""공개판 전체 점검: 원본 HWPX 유래 파일·그림이 없고, 템플릿 JSON에는 서식 수치만 있는지."""
import json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PKG = ROOT / "korean_gov_docs"
SKIP = {".git", ".venv", "out_check", "out_check_report", "dist", "build", "__pycache__", ".pytest_cache"}
TEMPLATE_KEYS = {"org", "page", "cover", "release", "title", "contact", "heading"}


def files():
    for p in ROOT.rglob("*"):
        if p.is_file() and not (set(p.relative_to(ROOT).parts) & SKIP): yield p


def test_no_hwpx_or_images():
    bad = [p for p in files() if p.suffix.lower() in (".hwpx", ".hwp", ".bmp", ".jpg", ".jpeg", ".png", ".gif", ".pdf") and "docs" not in p.parts]
    assert not bad, bad


def test_no_xml_fragments_in_data():
    for p in list((PKG / "templates").glob("*.json")) + list((PKG / "rules").glob("*.json")) + list((PKG / "rules_report").glob("*.json")):
        s = p.read_text("utf-8")
        assert "<hp:" not in s and "<hh:" not in s, p


def test_template_fields_are_format_only():
    ts = sorted((PKG / "templates").glob("*.json"))
    assert len(ts) == 52
    for p in ts:
        t = json.loads(p.read_text("utf-8"))
        assert set(t) <= TEMPLATE_KEYS, (p.name, set(t) - TEMPLATE_KEYS)
        s = json.dumps(t, ensure_ascii=False)
        assert not re.search(r"\d{9}\.hwpx|borrow|coverage", s), p.name
        assert not re.search(r"0\d{1,2}-\d{3,4}-\d{4}", s), p.name
