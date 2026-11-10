"""보고서 표 선·음영 — 기준: 공무원 보도·보고 문서 실측(과기정통부 2026-10-29 보도자료 표). 작성 Mia(윤승미)
위·아래 바깥선 굵게(0.5mm), 머리 행 아래 이중선, 안쪽 선 얇게(0.12mm), 좌우 바깥선 없음, 머리 행만 옅은 회색(#F2F2F2)."""
import re, zipfile
from korean_report_hwpx.engine import report as R

ROWS = [["구분", "내용", "일정"], ["가나다", "라마바사 아자차카", "11월"], ["라마바", "사아자차 카타파", "12월"], ["사아자", "차카타파", "1월"]]


def _grid(doc, tmp_path, which=0):
    R.compose("", doc, tmp_path / "t.hwpx")
    z = zipfile.ZipFile(tmp_path / "t.hwpx")
    sec, head = z.read("Contents/section0.xml").decode(), z.read("Contents/header.xml").decode()
    bf = {}
    for m in re.finditer(r'<hh:borderFill id="(\d+)".*?</hh:borderFill>', head, re.S):
        b, d = m.group(0), {}
        for side in ("left", "right", "top", "bottom"):
            s = re.search(rf'<hh:{side}Border type="(\w+)" width="([\d.]+) mm"', b)
            d[side] = (s.group(1), float(s.group(2))) if s else ("NONE", 0.0)
        f = re.search(r'faceColor="(#\w+)"', b); d["fill"] = (f.group(1).upper() if f else "")
        bf[m.group(1)] = d
    tbls = [t for t in re.findall(r"<hp:tbl\b.*?</hp:tbl>", sec, re.S) if "구분" in t]
    t = tbls[which]
    grid = []
    for tr in re.findall(r"<hp:tr>.*?</hp:tr>", t, re.S):
        grid.append([bf[b] for b in re.findall(r'<hp:tc\b[^>]*borderFillIDRef="(\d+)"', tr)])
    return grid


def _doc(appendix=False):
    tbl = [{"type": "caption", "text": "가나다 현황"}, {"type": "table", "rows": ROWS}]
    d = {"title": "가나다 보고", "date": "2026. 11. 7.", "dept": "", "body": [{"type": "h", "text": "Ⅰ. 현황"}] + ([] if appendix else tbl),
         "appendix": [{"title": "붙임 1", "heading": "세부", "body": tbl}] if appendix else []}
    return d


def _thick(side): return side[0] == "SOLID" and side[1] >= 0.4
def _thin(side): return side[0] == "SOLID" and side[1] <= 0.15


def _check(g):
    head, body, last = g[0], g[1:], g[-1]
    for c in head:
        assert _thick(c["top"]), c                       # 위 바깥선 굵게
        assert c["bottom"][0] == "DOUBLE_SLIM", c        # 머리 행 아래 이중선(HWPX 선 종류 이름 그대로)
        assert c["fill"] in ("#F2F2F2",), c              # 머리 행 옅은 회색
    for c in last:
        assert _thick(c["bottom"]), c                    # 아래 바깥선 굵게
    for c in g[1]:
        assert c["top"][0] == "DOUBLE_SLIM", c           # 머리 바로 아래 행의 위 선도 이중선
    for r in body:
        assert r[0]["fill"] in ("", "#FFFFFF", "NONE"), r[0]   # 첫 열 본문 칸은 칠하지 않음
    for r in body[:-1]:
        for c in r: assert _thin(c["bottom"]), c         # 안쪽 가로선 얇게
    for r in g:
        assert r[0]["left"][0] == "NONE", r[0]           # 왼쪽 바깥선 없음
        assert r[-1]["right"][0] == "NONE", r[-1]        # 오른쪽 바깥선 없음
        for c in r[:-1]: assert _thin(c["right"]), c     # 안쪽 세로선 얇게


def test_body_table_style(tmp_path):
    _check(_grid(_doc(), tmp_path))


def test_appendix_table_style(tmp_path):
    _check(_grid(_doc(appendix=True), tmp_path))

