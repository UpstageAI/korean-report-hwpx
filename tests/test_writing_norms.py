"""작성 가이드: 공무원 문서 문장 규범(한 문장 압축·굵게·각주·개요 표·첫 장). 작성 Mia(윤승미)"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from korean_report_hwpx import server as SV  # noqa: E402


def test_report_guide_norms():
    g = SV.get_writing_guide("report")["guide"]
    assert "꼭 필요할 때만" not in g                     # 굵게를 막던 문구 제거
    for k in ("핵심 문구", "굵게", "**", "한 문장에", "개요", "표로", "첫 장", "붙임"):
        assert k in g, k


def test_press_guide_bold_and_footnote():
    g = SV.get_writing_guide("press_release", ministry="행정안전부")["guide"]
    assert "꼭 필요할 때만" not in g
    assert "굵게" in g and "**" in g
