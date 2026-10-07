"""공개판 검증: 전 기관 더미 생성 → 개인정보·원본 내용·그림이 0건인지, 서식 수치가 규칙값과 같은지.

(a) 전화번호: 더미 번호(044-000-0000)만 허용
(b) 직위가 붙은 실명: 가명(김○○·이○○ 형식)만 허용
(c) 더미 원고에 없는 문장: 서식 이름표(보도시점·배포·담당 부서 등) 외 0건
(d) 그림: 0건(로고·슬로건은 사용자가 logo_path로 넣을 때만)
(e) 서식 수치: 계층별 글꼴·크기·내어쓰기·줄 간격, 계층 사이 빈 줄 = rules 값
"""
import json, re, zipfile
from pathlib import Path

import pytest

import compose as C
from hwpx_doc import Hwpx, balanced
from dummy import DUMMY

ORGS = C.ministries()
PHONE = re.compile(r"\(?0\d{1,2}\)?[-.\s)]\s*\d{3,4}[-.\s]\d{4}")
ALLOWED_PHONES = {"044-000-0000"}
TITLE_WORDS = r"(과\s*장|사무관|주무관|서기관|연구관|연구사|장관|차관|청장|차장|처장|위원장|부위원장|국장|실장|팀장|본부장|총리|원장|대변인)"
NAME_TITLE = re.compile(r"([가-힣○]{2,4})\s*" + TITLE_WORDS)
LABELS = {"기관 로고", "보도자료", "보도참고자료", "보도설명자료", "보도해명자료", "보도시점", "보도일시", "배포", "온라인‧방송", "조간",
          "담당 부서", "책임자", "담당자", "참고 1", "□", "ㅇ", "○", "◦", "❍", "-", "*", "※", "　"}


def _allowed_texts(doc):
    out = [doc["release"], doc["distribute"], doc["title"], *doc["subtitles"], *[f"- {s} -" for s in doc["subtitles"]]]
    def blocks(bs):
        for b in bs:
            if "text" in b: out.append(re.sub(r"\*\*(.+?)\*\*", r"\1", b["text"])); out.append(f"< {b['text']} >")
            for r in b.get("rows", []): out.extend(r)
            out.extend(b.get("lines", []))
    blocks(doc["body"])
    for a in doc.get("appendix", []): out += [a["title"], a["heading"]]; blocks(a["body"])
    out.append(doc["contact"]["dept"]); out += [x for p in doc["contact"]["people"] for x in p]
    return out


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    d = tmp_path_factory.mktemp("out"); res = {}
    for org in ORGS:
        dst = d / f"{org}.hwpx"; c = C.compose(org, DUMMY, dst)
        z = zipfile.ZipFile(dst)
        res[org] = (c, z, z.read("Contents/section0.xml").decode(), z.read("Contents/header.xml").decode(), z.read("Preview/PrvText.txt").decode())
    return res


def test_all_orgs_build(built):
    assert len(ORGS) == 52 and set(built) == set(ORGS)


@pytest.mark.parametrize("org", ORGS)
def test_no_phone(built, org):
    _, _, sec, _, prv = built[org]
    for src in (Hwpx.text(sec, True), prv):
        bad = [m.group(0) for m in PHONE.finditer(src) if re.sub(r"[()\s]", "", m.group(0)) not in ALLOWED_PHONES]
        assert not bad, bad


@pytest.mark.parametrize("org", ORGS)
def test_no_real_name(built, org):
    _, _, sec, _, prv = built[org]
    texts = [Hwpx.text(m.group(0)) for m in re.finditer(r"<hp:t>.*?</hp:t>", sec, re.S)] + prv.splitlines()
    for t in texts:
        for m in NAME_TITLE.finditer(t):
            assert "○" in m.group(1), (org, t)


@pytest.mark.parametrize("org", ORGS)
def test_no_foreign_text(built, org):
    _, _, sec, _, prv = built[org]
    allowed = _allowed_texts(DUMMY)
    for raw in re.findall(r"<hp:t>(.*?)</hp:t>", sec, re.S) + prv.splitlines():
        t = Hwpx.text(f"<hp:t>{raw}</hp:t>").strip()
        if not t or t in LABELS or t.replace(" ", "") in LABELS: continue
        if any(t in a for a in allowed): continue
        if t == org or t.startswith("보도시점 :"): continue
        raise AssertionError(f"{org}: 더미에 없는 글 '{t}'")


@pytest.mark.parametrize("org", ORGS)
def test_no_images(built, org):
    _, z, sec, head, _ = built[org]
    assert not [n for n in z.namelist() if n.startswith("BinData/")]
    assert "binaryItemIDRef" not in sec and "binaryItemIDRef" not in head


def test_logo_only_when_given(tmp_path):
    png = tmp_path / "logo.png"
    import struct, zlib
    raw = b"\x00\xff\xff\xff"
    png.write_bytes(b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0) + struct.pack(">I", zlib.crc32(b"IHDR" + struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)))
                    + struct.pack(">I", len(zlib.compress(raw))) + b"IDAT" + zlib.compress(raw) + struct.pack(">I", zlib.crc32(b"IDAT" + zlib.compress(raw))) + b"\x00\x00\x00\x00IEND\xaeB`\x82")
    C.compose(ORGS[0], DUMMY, tmp_path / "a.hwpx", logo_path=png)
    z = zipfile.ZipFile(tmp_path / "a.hwpx")
    assert [n for n in z.namelist() if n.startswith("BinData/")] == ["BinData/image1.png"]
    assert "기관 로고" not in z.read("Contents/section0.xml").decode()


def test_placeholder_contact(tmp_path):
    doc = dict(DUMMY, contact={})
    C.compose(ORGS[0], doc, tmp_path / "p.hwpx", placeholder_contact=True)
    t = Hwpx.text(zipfile.ZipFile(tmp_path / "p.hwpx").read("Contents/section0.xml").decode(), True)
    assert "○○과" in t and "김○○" in t and "044-000-0000" in t


# ── (e) 서식 수치 = 규칙값 ──
def _header_maps(head):
    fonts = dict(re.findall(r'<hh:font id="(\d+)" face="([^"]+)"', re.search(r'<hh:fontface lang="HANGUL".*?</hh:fontface>', head, re.S).group(0)))
    chars = {m.group(1): m.group(0) for m in re.finditer(r'<hh:charPr id="(\d+)".*?</hh:charPr>', head, re.S)}
    paras = {m.group(1): m.group(0) for m in re.finditer(r'<hh:paraPr id="(\d+)".*?</hh:paraPr>', head, re.S)}
    return fonts, chars, paras


def _char(fonts, chars, cid):
    s = chars[cid]
    return fonts[re.search(r'<hh:fontRef hangul="(\d+)"', s).group(1)], int(re.search(r'height="(\d+)"', s).group(1))


@pytest.mark.parametrize("org", ORGS)
def test_format_matches_rules(built, org):
    c, _, sec, head, _ = built[org]
    fonts, chars, paras = _header_maps(head)
    tops = [p for *_, p in balanced(sec, "p")]
    pos = {re.search(r'<hp:p id="(\d+)"', p).group(1): i for i, p in enumerate(tops)}
    checked = 0
    for pno, it in c.items.items():
        p = tops[pos[pno]]; L_ = c.level(it["lv"])
        body = re.sub(r"<hp:rect\b.*?</hp:rect>", "", p, flags=re.S)
        cid = max(re.findall(r'<hp:run charPrIDRef="(\d+)"><hp:t>(.*?)</hp:t>', body), key=lambda r: len(r[1]))[0]
        face, h = _char(fonts, chars, cid)
        assert face == L_["font"] and h == int(L_["pt"] * 100), (org, it["lv"], face, h, L_)
        pp = paras[re.search(r'paraPrIDRef="(\d+)"', p).group(1)]
        assert f'<hh:lineSpacing type="PERCENT" value="{L_["line"]}"' in pp
        lead = " " * L_["lead"]
        assert it["text"].startswith(lead + (L_["mark"] if it["lv"] != "p" else "")), (org, it)
        if it["lv"] != "p":
            hang = int(round((0.5 * L_["lead"] + C.MARK_W.get(L_["mark"], 1.0) + 0.5 * max(1, L_["gap"])) * L_["pt"] * 100))
            assert f'<hc:intent value="{-hang}"' in pp, (org, it["lv"])
        checked += 1
    assert checked >= 5
    # 규칙값 자체와 대조(문서화된 보정만 예외: 하위 계층 최소 들여쓰기, 주석 13pt 초과 → 12pt, 본문 글꼴 통일)
    R = C.load_rules(org)
    for lv, rv in R["levels"].items():
        if lv not in ("l1", "l2", "l3", "note", "ref", "p"): continue
        L_ = c.level(lv)
        if rv.get("mark") is not None: assert L_["mark"] == rv["mark"]
        if rv.get("line"): assert L_["line"] == rv["line"]
        if rv.get("pt") and not (lv in ("note", "ref") and rv["pt"] > 13) and L_["font"] == rv.get("font"): assert L_["pt"] == rv["pt"]
        if "lead" in rv and lv not in ("l2", "l3"): assert L_["lead"] == rv["lead"]


@pytest.mark.parametrize("org", ORGS)
def test_gaps_match_rules(built, org):
    c, _, sec, head, _ = built[org]
    fonts, chars, _ = _header_maps(head)
    tops = [p for *_, p in balanced(sec, "p")]
    ids = [(re.search(r'<hp:p id="(\d+)"', p).group(1)) for p in tops]
    seq = [k for k, i in enumerate(ids) if i in c.items]
    n = 0
    for a, b in zip(seq, seq[1:]):
        la, lb = c.items[ids[a]]["lv"], c.items[ids[b]]["lv"]
        between = tops[a + 1:b]
        if any("<hp:tbl" in x or "<hp:rect" in x for x in between) or b - a > 2: continue   # 표·상자를 사이에 둔 경우 제외
        g = c.gap_pt(la, lb)
        if g is None: assert b - a == 1, (org, la, lb)
        else:
            assert b - a == 2, (org, la, lb)
            cid = re.search(r'charPrIDRef="(\d+)"', between[0]).group(1)
            assert _char(fonts, chars, cid)[1] == int(g * 100), (org, la, lb, g)
        n += 1
    assert n >= 2
