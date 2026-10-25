"""out_path에 폴더·확장자 없는 이름을 줘도 저장 경로가 올바른지."""
from pathlib import Path

from korean_report_hwpx import server as SV


def test_empty_uses_default_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("KOREAN_REPORT_HWPX_OUT_DIR", str(tmp_path))
    p = SV._dst("", "가람정밀 세무 검토", "", "report")
    assert p.parent == tmp_path
    assert p.suffix == ".hwpx"
    assert p.name.startswith("공통_")


def test_existing_dir_puts_file_inside(tmp_path):
    p = SV._dst("", "가람정밀 세무 검토", str(tmp_path), "report")
    assert p.parent == tmp_path
    assert p.suffix == ".hwpx"
    assert "가람정밀" in p.name


def test_dot_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    p = SV._dst("", "보고", ".", "report")
    assert p.resolve().parent == tmp_path.resolve()
    assert p.suffix == ".hwpx"


def test_trailing_slash_new_dir_created(tmp_path):
    d = tmp_path / "새폴더"
    p = SV._dst("", "보고", str(d) + "/", "report")
    assert p.parent == d
    assert d.is_dir()
    assert p.suffix == ".hwpx"


def test_no_suffix_gets_hwpx(tmp_path):
    p = SV._dst("", "보고", str(tmp_path / "결과"), "report")
    assert p == tmp_path / "결과.hwpx"


def test_full_file_path_kept_and_parent_made(tmp_path):
    f = tmp_path / "a" / "b" / "문서.hwpx"
    p = SV._dst("", "보고", str(f), "report")
    assert p == f
    assert f.parent.is_dir()


def test_default_name_same_rule_for_dir_and_empty(tmp_path, monkeypatch):
    monkeypatch.setenv("KOREAN_REPORT_HWPX_OUT_DIR", str(tmp_path / "기본"))
    a = SV._dst("행정안전부", "제목 하나", "", "press_release")
    b = SV._dst("행정안전부", "제목 하나", str(tmp_path) + "/", "press_release")
    assert a.name == b.name


def test_build_document_with_dir(tmp_path):
    s = {"title": "폴더 저장 확인", "date": "2026. 10. 25.", "dept": "",
         "body": [{"type": "h", "text": "Ⅰ. 확인 항목"},
                  {"type": "l1", "text": "폴더를 주면 그 안에 기본 이름으로 저장함"}]}
    r = SV.build_document(s, "report", "", str(tmp_path))
    out = Path(r["hwpx"])
    assert out.parent == tmp_path and out.exists()
