"""보도자료 본문 문단 간격(빈 줄·문단 위 간격)이 기관 실측값대로 나오는지 (SPEC_press_spacing.md). 작성 Mia(윤승미)"""
import copy, json, re, sys, zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from korean_report_hwpx import server as SV  # noqa: E402
from sample_report import SAMPLE_REPORT  # noqa: E402

PKG = Path(SV.__file__).parent
SP = json.loads((PKG / "rules" / "_문단위간격.json").read_text("utf-8"))
DOC = {"release": "2026. 11. 2.(월) 조간", "title": "○○ 서비스 시범 운영",
       "body": [{"type": "p", "text": "가나다부(장관 ○○○)는 11월 2일(월)부터 ○○ 서비스를 시범 운영한다고 이날 알렸다."},
                {"type": "p", "text": "둘째 문단은 서비스 대상과 범위를 설명하는 문장으로 한 줄을 넘지 않게 쓴다."},
                {"type": "p", "text": "셋째 문단은 앞으로의 계획을 설명하는 문장으로 한 줄을 넘지 않게 쓴다."}],
       "contact": {"dept": "○○과", "people": []}}


def top_paras(xml):
    out, depth, start = [], 0, None
    for m in re.finditer(r"<hp:p\b[^>]*?(/?)>|</hp:p>", xml):
        t = m.group(0)
        if t.startswith("</"):
            depth -= 1
            if depth == 0: out.append(xml[start:m.end()])
        elif m.group(1) == "/":
            if depth == 0: out.append(t)
        else:
            if depth == 0: start = m.start()
            depth += 1
    return out


def text(p):
    return "".join(re.findall(r"<hp:t>([^<]*)</hp:t>", re.sub(r"<hp:tbl\b.*?</hp:tbl>", "", p, flags=re.S)))


def build(org, doc, tmp_path, t="press_release"):
    r = SV.build_document(copy.deepcopy(doc), t, org, str(tmp_path / "s.hwpx"))
    z = zipfile.ZipFile(r["hwpx"])
    return z.read("Contents/section0.xml").decode("utf-8"), z.read("Contents/header.xml").decode("utf-8")


def para_prev(header, p):
    pid = re.search(r'paraPrIDRef="(\d+)"', p).group(1)
    blk = re.search(r'<hh:paraPr id="%s".*?</hh:paraPr>' % pid, header, re.S).group(0)
    return int(re.search(r'<hc:prev value="(-?\d+)"', blk).group(1))


def char_pt(header, p):
    cid = re.search(r'charPrIDRef="(\d+)"', p).group(1)
    blk = re.search(r'<hh:charPr id="%s"[^>]*>' % cid, header).group(0)
    return int(re.search(r'height="(\d+)"', blk).group(1)) / 100


def body_slice(paras):
    i = next(k for k, p in enumerate(paras) if "시범 운영한다고" in text(p))
    j = next(k for k, p in enumerate(paras) if text(p).strip().startswith("셋째 문단"))
    return i, j


def test_data_file():
    assert SP["기관"]["행정안전부"]["p"] == 1000 and SP["기관"]["과학기술정보통신부"]["p"] == 0
    assert set(SP["전체"]) >= {"p", "l1", "l2", "l3", "note", "ref"}


def test_mois_paragraph_top_spacing_no_blank_lines(tmp_path):
    sec, hdr = build("행정안전부", DOC, tmp_path)
    ps = top_paras(sec); i, j = body_slice(ps)
    seg = ps[i:j + 1]
    assert len(seg) == 3, [text(p) for p in seg]          # 빈 줄 없음
    assert all(para_prev(hdr, p) == 1000 for p in seg)


def test_msit_blank_line_between_paragraphs(tmp_path):
    sec, hdr = build("과학기술정보통신부", DOC, tmp_path)
    ps = top_paras(sec); i, j = body_slice(ps)
    seg = ps[i:j + 1]
    assert len(seg) == 5, [text(p) for p in seg]          # 문단 사이 빈 줄 1개씩
    blanks = [p for p in seg if not text(p).strip()]
    assert len(blanks) == 2 and all(char_pt(hdr, p) == 10.0 for p in blanks)
    assert all(para_prev(hdr, p) == 0 for p in seg if text(p).strip())


def test_report_unchanged(tmp_path):
    sec, hdr = build("", SAMPLE_REPORT, tmp_path, "report")
    ps = [p for p in top_paras(sec) if "<hp:tbl" not in p]
    l1 = [p for p in ps if text(p).lstrip().startswith("□")]
    assert l1 and all(para_prev(hdr, p) == 1000 for p in l1)


def test_no_blank_line_before_caption_heading_appendix(tmp_path):
    doc = copy.deepcopy(DOC)
    b = doc["body"]
    doc["body"] = [b[0], {"type": "caption", "text": "표 제목"}, {"type": "table", "rows": [["구분", "값"], ["가", "1건"]]},
                   b[1], {"type": "h", "text": "소제목"}, b[2]]   # 캡션·소제목 모두 p 바로 뒤
    doc["appendix"] = [{"title": "참고 1", "heading": "참고 제목", "body": [{"type": "l1", "text": "참고 내용이다."}]}]
    sec, hdr = build("과학기술정보통신부", doc, tmp_path)
    ps = top_paras(sec)
    for key in ("표 제목", "소제목"):
        k = next(i for i, p in enumerate(ps) if key in text(p) and "<hp:tbl" not in p)
        assert text(ps[k - 1]).strip(), (key, "앞에 빈 줄")
    k = next(i for i, p in enumerate(ps) if "참고 제목" in p)
    assert text(ps[k - 1]).strip() or "<hp:tbl" in ps[k - 1], "참고 머리 앞에 빈 줄"


def test_spacing_rules_read_once():
    import compose as C
    src = Path(C.__file__).read_text("utf-8")
    body = src[src.index("    def item(self"):src.index("    RATIOS")]
    assert "_문단위간격.json" not in body   # 문단마다 파일을 읽지 않는다(모듈 또는 인스턴스에서 한 번)
