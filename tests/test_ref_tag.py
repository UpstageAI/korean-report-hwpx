"""문장 끝 '붙임 N'·'참고 N' 표시는 앞 글자와 상관없이 상자로 그린다(명사형 종결이 '~가동', '~확대'여도). 작성 Mia(윤승미)"""
import re, sys, zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "korean_report_hwpx" / "engine")]
import report as R  # noqa: E402


def _sec(doc, tmp_path):
    R.compose("", doc, tmp_path / "r.hwpx")
    return zipfile.ZipFile(tmp_path / "r.hwpx").read("Contents/section0.xml").decode()


def _doc(lines):
    return {"title": "가나다 보고", "date": "2026. 11. 7.", "dept": "",
            "body": [{"type": "h", "text": "Ⅰ. 주요 내용"}] + [{"type": "l1", "text": t} for t in lines],
            "appendix": [{"title": f"붙임 {k}", "heading": "세부", "body": [{"type": "l1", "text": "가나다 정리"}]} for k in range(1, 6)]}


ENDINGS = ["11월 말부터 가동 붙임 1", "복합데이터셋으로 활용 확대 붙임 2", "실행 중심 운영 강조 붙임 3",
           "관계부처 협의로 추진 붙임 4", "범정부 입법 원칙 확정 붙임 5"]


def _segment(sec, phrase):
    """phrase가 들어 있는 본문 문단: phrase 위치부터 그 문단이 끝날 때까지(상자 안 subList의 </hp:p>는 건너뜀)."""
    i = sec.index(phrase)
    j = sec.find("</hp:rect>", i)
    nxt = sec.find("<hp:p id=", i)
    if j != -1 and (nxt == -1 or j < sec.find("</hp:p>", i) or "<hp:rect" in sec[i:sec.find("</hp:p>", i)]):
        return sec[i:j + len("</hp:rect>")]
    return sec[i:sec.find("</hp:p>", i)]


def test_every_trailing_tag_is_boxed(tmp_path):
    sec = _sec(_doc(ENDINGS), tmp_path)
    for k, e in enumerate(ENDINGS, 1):
        phrase = e.split(" 붙임")[0]
        seg = _segment(sec, phrase)
        assert "<hp:rect" in seg, (e, seg[:300])
        box = re.search(r"<hp:rect\b.*?</hp:rect>", seg, re.S).group(0)
        assert f"<hp:t>붙임 {k}</hp:t>" in box, box[-400:]               # 상자 안에 '붙임 N' 글자
        outside = re.sub(r"<hp:rect\b.*?</hp:rect>", "", seg, flags=re.S)
        texts = re.sub(r"<[^>]+>", "", "".join(re.findall(r"<hp:t>(.*?)</hp:t>", outside, re.S)))
        assert f"붙임 {k}" not in texts, texts                           # 상자 밖에는 글자로 남지 않음


def test_tag_word_in_middle_not_boxed(tmp_path):
    sec = _sec(_doc(["붙임 1과 같이 세부 일정을 정리함", "관련 자료는 참고자료 붙임으로 제출"]), tmp_path)
    for phrase in ("세부 일정을 정리함", "참고자료 붙임으로 제출"):
        i = sec.index(phrase)
        para = sec[sec.rfind("<hp:p id=", 0, i):sec.find("</hp:p>", i)]
        assert "<hp:rect" not in para, para[:300]
