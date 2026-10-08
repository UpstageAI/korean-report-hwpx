"""줄 나눔·정규화 회귀 확인. 작성 Mia(윤승미)"""
import re, zipfile
import compose as C
import report as RP
from sample_release import SAMPLE


def test_normalize():
    assert C.normalize("– 어르신 대상", "l3") == "어르신 대상"
    assert C.normalize("총 3억 2천만 원, 5천만 원", "l2") == "총 3억 2천만 원, 5천만 원"
    assert C.normalize("하루 400 건", "l2") == "하루 400 건"


def _sec(p): return zipfile.ZipFile(p).read("Contents/section0.xml").decode()


def test_word_break_and_prefix(tmp_path):
    doc = {"title": "가나다시 AI 민원 안내", "body": [{"type": "l1", "text": "총 5천만 원 규모"}, {"type": "l2", "text": "가"},
           {"type": "l3", "text": "—어르신 대상 큰 글씨 및 음성 안내, 현장 도우미 지원 기능을 포함함."}, {"type": "l3", "text": "개인정보는 저장하지 않음."}]}
    c = RP.compose("", doc, tmp_path / "r.hwpx")
    sec = _sec(tmp_path / "r.hwpx")
    used = set(re.findall(r'paraPrIDRef="(\d+)"', sec))
    for pid in used - {"0"}:
        el = re.search(r'<hh:paraPr id="%s".*?</hh:paraPr>' % pid, c.header, re.S).group(0)
        assert 'breakNonLatinWord="BREAK_WORD"' in el
    assert "5천만<hp:nbSpace/>원" in sec
    pre = re.findall(r'<hp:run charPrIDRef="(\d+)"><hp:t>(\s+-\s+)</hp:t>', sec)
    assert len(pre) == 2 and pre[0] == pre[1]   # 같은 계층 접두는 같은 글자 모양(자간 0)
    C.compose("행정안전부", SAMPLE, tmp_path / "b.hwpx")
