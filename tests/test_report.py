"""보고서 모드: 가상 원고(sample_report)로 보고서 규칙 기관 42곳 + 공통 생성 → 열림·정화(실명·전화·원본 문장·그림 0건)·서식 수치=규칙값."""
import re, zipfile

import pytest

import compose as C
import report as R
from hwpx_doc import Hwpx, balanced
from sample_report import SAMPLE_REPORT as S
from test_sanitize import PHONE, ALLOWED_PHONES, NAME_TITLE

ORGS = R.ministries() + [""]   # "" = 기관 미지정(공통 규칙)
LABELS = {"붙임 1", "[붙임 1]", "< 붙임 1 >", "□", "ㅇ", "○", "◦", "❍", "-", "*", "※", "　"}


def _allowed(doc):
    out = [doc["title"], doc["date"], doc["dept"]]
    def blocks(bs):
        for b in bs:
            if "text" in b:
                t = re.sub(r"\*\*(.+?)\*\*", r"\1", b["text"]); out.append(t); out.append(f"< {t} >")
            for r in b.get("rows", []): out.extend(r)
            out.extend(b.get("lines", []))
    blocks(doc["body"])
    for a in doc["appendix"]: out += [a["title"], a["heading"]]; blocks(a["body"])
    return out


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    d = tmp_path_factory.mktemp("rep"); res = {}
    for org in ORGS:
        dst = d / f"{org or '공통'}.hwpx"; c = R.compose(org, S, dst)
        z = zipfile.ZipFile(dst)
        res[org] = (c, z, z.read("Contents/section0.xml").decode(), z.read("Contents/header.xml").decode(), z.read("Preview/PrvText.txt").decode())
    return res


def test_counts(built):
    assert len(R.ministries()) == 42 and len(built) == 43


@pytest.mark.parametrize("org", ORGS)
def test_clean(built, org):
    c, z, sec, head, prv = built[org]
    assert not [n for n in z.namelist() if n.startswith("BinData/")] and "binaryItemIDRef" not in sec
    text = Hwpx.text(sec, True)
    bad = [m.group(0) for src in (text, prv) for m in PHONE.finditer(src) if re.sub(r"[()\s]", "", m.group(0)) not in ALLOWED_PHONES]
    assert not bad, bad
    for raw in re.findall(r"<hp:t>(.*?)</hp:t>", sec, re.S) + prv.splitlines():
        t = Hwpx.text(f"<hp:t>{raw}</hp:t>").strip()
        for m in NAME_TITLE.finditer(t): assert "○" in m.group(1), (org, t)
        if not t or t in LABELS: continue
        if any(t in a for a in _allowed(S)): continue
        if org and t == "  ".join(x for x in (S["date"], org, S["dept"]) if x): continue
        if not org and t == "  ".join((S["date"], S["dept"])): continue
        raise AssertionError(f"{org}: 원고에 없는 글 '{t}'")
    # 보고서에는 보도자료 머리·담당 표가 없음, 붙임 쪽은 새 쪽
    assert "보도자료" not in text and "책임자" not in text and "보도시점" not in text
    assert "붙임 1" in text and 'pageBreak="1"' in sec


@pytest.mark.parametrize("org", ORGS)
def test_format_matches_report_rules(built, org):
    c, _, sec, head, _ = built[org]
    fonts = dict(re.findall(r'<hh:font id="(\d+)" face="([^"]+)"', re.search(r'<hh:fontface lang="HANGUL".*?</hh:fontface>', head, re.S).group(0)))
    chars = {m.group(1): m.group(0) for m in re.finditer(r'<hh:charPr id="(\d+)".*?</hh:charPr>', head, re.S)}
    tops = [p for *_, p in balanced(sec, "p")]
    pos = {re.search(r'<hp:p id="(\d+)"', p).group(1): i for i, p in enumerate(tops)}
    rules = R.load_rules(org); n = 0
    for pno, it in c.items.items():
        p = re.sub(r"<hp:rect\b.*?</hp:rect>", "", tops[pos[pno]], flags=re.S); L_ = c.level(it["lv"])
        cid = max(re.findall(r'<hp:run charPrIDRef="(\d+)"><hp:t>(.*?)</hp:t>', p), key=lambda r: len(r[1]))[0]
        s = chars[cid]
        assert fonts[re.search(r'<hh:fontRef hangul="(\d+)"', s).group(1)] == L_["font"]
        assert int(re.search(r'height="(\d+)"', s).group(1)) == int(L_["pt"] * 100)
        assert it["text"].startswith(" " * L_["lead"] + L_["mark"]), (org, it)
        rv = rules["levels"].get(it["lv"]) or rules["_base"]["levels"][it["lv"]]
        assert L_["mark"] == rv["mark"]
        n += 1
    assert n >= 20
    # 표 머리 = 규칙 표 머리 배경색, 붙임 라벨 칸 = 규칙 상자 색
    assert rules["table_head"]["fill"] in head and rules["title_box"]["fill"] in head


def test_unlisted_org_uses_common_with_name(tmp_path):
    org = next(o for o in C.ministries() if o not in R.ministries())
    c = R.compose(org, S, tmp_path / "x.hwpx")
    assert c.rule_key == R.COMMON and org in Hwpx.text(zipfile.ZipFile(tmp_path / "x.hwpx").read("Contents/section0.xml").decode(), True)


def test_write_document_auto(monkeypatch, tmp_path):
    """Solar 응답을 흉내 내어 auto 판단 → 보고서 생성 흐름 확인(네트워크 없음)."""
    from korean_gov_docs import server as SV
    calls = []
    def fake(prompt, **kw):
        calls.append(prompt)
        return {"doc_type": "report", "reason": "내부 추진계획 메모"} if len(calls) == 1 else dict(S)
    monkeypatch.setattr(SV.solar, "chat_json", fake)
    r = SV.write_document(text="메모", out_path=str(tmp_path / "a.hwpx"))
    assert r["doc_type"] == "report" and r["판단근거"] and (tmp_path / "a.hwpx").exists() and r["기관"] == "공통(미지정)"
    assert "명사형" in calls[1] and "지어내지" in calls[1]
    # 보도자료로 판단됐는데 기관이 없으면 보고서로
    calls.clear()
    monkeypatch.setattr(SV.solar, "chat_json", lambda p, **k: {"doc_type": "press_release", "reason": "대외 발표"} if "판단" in p[:80] else dict(S))
    assert SV.write_document(text="발표문", out_path=str(tmp_path / "b.hwpx"))["doc_type"] == "report"
