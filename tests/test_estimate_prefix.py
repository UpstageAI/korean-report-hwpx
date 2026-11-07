"""분량 예측의 문단 앞머리(기호·내어쓰기) 폭은 생성 엔진과 같은 함수에서 나온다 — 간소화 모드 기호 없음 포함. 작성 Mia(윤승미)"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "korean_report_hwpx" / "engine")]
import report as RP  # noqa: E402
import pages  # noqa: E402


@pytest.mark.parametrize("style", ["standard", "simplified"])
@pytest.mark.parametrize("lv", ["l1", "l2", "l3", "p", "note", "ref"])
def test_prefix_hang_shared(style, lv):
    c = RP.ReportComposer("", style=style)
    prefix, hang = c.prefix_hang(lv)                      # 생성 엔진이 item()에서 쓰는 값
    assert pages.prefix_hang(c, lv) == (prefix, hang)    # 예측도 같은 값
    if style == "simplified" and lv in ("l1", "l2", "l3"):
        assert c.level(lv)["mark"] not in prefix          # 간소화 모드 □ㅇ- 기호 없음
    if lv == "p":
        assert hang == 0


def test_simplified_not_more_lines_than_standard():
    long = "가나다라 마바사아 자차카타 파하가나 다라마바 사아자차 카타파하 가나다라 마바사아 자차카타 파하가나 다라마바"
    d = {"title": "가나다 보고", "date": "2026. 11. 7.", "dept": "",
         "body": [{"type": "h", "text": "Ⅰ. 개요"}] + [{"type": "l1", "text": long} for _ in range(6)], "appendix": []}
    a = pages.estimate(d, style="standard")["본문_줄수"]
    b = pages.estimate(d, style="simplified")["본문_줄수"]
    assert b <= a, (a, b)
