"""분량 예측. 작성 Mia(윤승미)

보고서(doc_type=report)만 대상. 본문 쪽수·마지막 쪽 채움·본문 줄 수·전체 쪽 수를 예측한다.

이제는 근사 보정 상수(W_EST, 쪽 높이 73000 등) 대신 실제 생성 HWPX를 임시 파일로 만든 뒤
header.xml(charPr·paraPr·글꼴)과 section0.xml(문단·표)을 읽어 한글 배치 규칙대로 쌓아 예측한다.
"""
import json
import re
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from . import fit as F
from . import compose as C
from . import report as RP
from . import xml as X

WIDTHS = C.WIDTHS

NS = {'hp': 'http://www.hancom.co.kr/hwpml/2011/paragraph',
      'hh': 'http://www.hancom.co.kr/hwpml/2011/head',
      'hc': 'http://www.hancom.co.kr/hwpml/2011/core'}

HP_P = '{%s}p' % NS['hp']
HP_RUN = '{%s}run' % NS['hp']
HP_T = '{%s}t' % NS['hp']
HP_TBL = '{%s}tbl' % NS['hp']
HP_TC = '{%s}tc' % NS['hp']
HP_CELLADDR = '{%s}cellAddr' % NS['hp']
HP_CELLSPAN = '{%s}cellSpan' % NS['hp']
HP_CELLSZ = '{%s}cellSz' % NS['hp']
HP_CELLMARGIN = '{%s}cellMargin' % NS['hp']
HP_TR = '{%s}tr' % NS['hp']

# 기존 테스트 호환용: 생성 엔진 Composer.prefix_hang과 같은 값을 돌려준다.
def prefix_hang(c, lv):
    """분량 예측용 앞머리(prefix)와 내어쓰기(hang). 생성 엔진 Composer.prefix_hang과 같은 값을 돌려준다."""
    return c.prefix_hang(lv)


# ── HWPX 파싱 ──────────────────────────────────────────────────────────────────

def _font_id_to_face(header_xml, fid):
    """글꼴 id → 글꼴 얼굴 이름 (HANGUL lang 기준). header_xml은 문자열."""
    m = re.search(r'(<hh:fontface lang="HANGUL"[^>]*>)(.*?)(</hh:fontface>)', header_xml, re.S)
    if not m:
        return "바탕"
    block = m.group(2)
    fm = re.search(r'<hh:font id="%s" face="([^"]+)"' % re.escape(str(fid)), block)
    return fm.group(1) if fm else "바탕"


def _parse_charPr(header_xml):
    """header.xml 문자열에서 charPr 목록을 파싱. 반환: {id: {height, font_face, spacing, ratio, bold}}."""
    out = {}
    for m in re.finditer(r'<hh:charPr id="(\d+)"[^>]*height="(\d+)"[^>]*>.*?</hh:charPr>', header_xml, re.S):
        cid = int(m.group(1))
        height = int(m.group(2))
        fm = re.search(r'<hh:fontRef hangul="(\d+)"', m.group(0))
        font_id = int(fm.group(1)) if fm else 0
        sm = re.search(r'<hh:spacing hangul="(-?\d+)"', m.group(0))
        spacing = int(sm.group(1)) if sm else 0
        rm = re.search(r'<hh:ratio hangul="(\d+)"', m.group(0))
        ratio = int(rm.group(1)) if rm else 100
        bold = '<hh:bold/>' in m.group(0)
        out[cid] = {
            "height": height,
            "font_face": _font_id_to_face(header_xml, font_id),
            "spacing": spacing,
            "ratio": ratio,
            "bold": bold,
        }
    return out


def _parse_paraPr(header_xml):
    """header.xml 문자열에서 paraPr 목록을 파싱. 반환: {id: {line, prev, next, intent, left, widowOrphan, keepWithNext}}."""
    out = {}
    for m in re.finditer(r'<hh:paraPr id="(\d+)"[^>]*>.*?</hh:paraPr>', header_xml, re.S):
        pid = int(m.group(1))
        lm = re.search(r'<hh:lineSpacing type="PERCENT" value="(\d+)"', m.group(0))
        line = int(lm.group(1)) if lm else 160
        pm = re.search(r'<hc:prev value="(-?\d+)"', m.group(0))
        prev = int(pm.group(1)) if pm else 0
        nm = re.search(r'<hc:next value="(-?\d+)"', m.group(0))
        nxt = int(nm.group(1)) if nm else 0
        im = re.search(r'<hc:intent value="(-?\d+)"', m.group(0))
        intent = int(im.group(1)) if im else 0
        lm2 = re.search(r'<hc:left value="(-?\d+)"', m.group(0))
        left = int(lm2.group(1)) if lm2 else 0
        wm = re.search(r'widowOrphan="(\d+)"', m.group(0))
        widow = int(wm.group(1)) if wm else 0
        km = re.search(r'keepWithNext="(\d+)"', m.group(0))
        keep = int(km.group(1)) if km else 0
        out[pid] = {
            "line": line,
            "prev": prev,
            "next": nxt,
            "intent": intent,
            "left": left,
            "widowOrphan": widow,
            "keepWithNext": keep,
        }
    return out


def _parse_page_pr(section_xml):
    """section0.xml 문자열에서 hp:pagePr / hp:margin을 뽑아 쪽 크기·여백 dict로 반환."""
    pm = re.search(r'<hp:pagePr[^>]*width="(\d+)" height="(\d+)"[^>]*>', section_xml)
    if not pm:
        return {}
    width = int(pm.group(1))
    height = int(pm.group(2))
    mm = re.search(r'<hp:margin[^>]*header="(\d+)" footer="(\d+)"[^>]*left="(\d+)" right="(\d+)" top="(\d+)" bottom="(\d+)"', section_xml)
    if not mm:
        return {}
    return {
        "width": width,
        "height": height,
        "header": int(mm.group(1)),
        "footer": int(mm.group(2)),
        "left": int(mm.group(3)),
        "right": int(mm.group(4)),
        "top": int(mm.group(5)),
        "bottom": int(mm.group(6)),
    }


def _parse_section(section_xml):
    """section0.xml 문자열을 ElementTree로 파싱하여 문단 목록 반환.

    반환: [dict]
      - paraPrIDRef, pageBreak
      - runs: [(charPrIDRef, text), ...]  (표 문단이면 빈 목록)
      - is_table_para: 표 문단이면 True
      - tbl_info: 표 문단이면 {pageBreak, repeatHeader, rows: [{cells: [{text, width, height, rowSpan, colSpan, cellMargin, row, col}]}]}
    """
    root = ET.fromstring(section_xml)
    out = []
    for p in root.findall('hp:p', NS):
        paraPrIDRef = int(p.get('paraPrIDRef', 0))
        pageBreak = int(p.get('pageBreak', 0))

        # Run 목록
        runs = []
        tbl_info = None
        for run in p.findall('hp:run', NS):
            charPrIDRef = int(run.get('charPrIDRef', 0))
            # 표가 있으면 표 정보 추출
            for tbl in run.findall('hp:tbl', NS):
                if tbl_info is None:
                    # 표 outMargin bottom 추출
                    out_marg = tbl.find('hp:outMargin', NS)
                    out_margin_bottom = int(out_marg.get('bottom', 0)) if out_marg is not None else 0
                    tbl_info = {
                        "pageBreak": tbl.get('pageBreak', 'NONE'),
                        "repeatHeader": int(tbl.get('repeatHeader', 0)),
                        "rows": [],
                        "outMargin_bottom": out_margin_bottom,
                    }
                rowCnt = int(tbl.get('rowCnt', 0))
                colCnt = int(tbl.get('colCnt', 0))
                # 셀 추출
                cells = []
                for tc in tbl.findall('hp:tr/hp:tc', NS):
                    addr = tc.find(HP_CELLADDR)
                    row = int(addr.get('rowAddr', 0)) if addr is not None else 0
                    col = int(addr.get('colAddr', 0)) if addr is not None else 0
                    sz = tc.find(HP_CELLSZ)
                    cell_w = int(sz.get('width', 0)) if sz is not None else 0
                    cell_h = int(sz.get('height', 0)) if sz is not None else 0
                    span = tc.find(HP_CELLSPAN)
                    colSpan = int(span.get('colSpan', 1)) if span is not None else 1
                    rowSpan = int(span.get('rowSpan', 1)) if span is not None else 1
                    marg = tc.find(HP_CELLMARGIN)
                    cellMargin = {
                        "left": int(marg.get('left', 0)) if marg is not None else 0,
                        "right": int(marg.get('right', 0)) if marg is not None else 0,
                        "top": int(marg.get('top', 0)) if marg is not None else 0,
                        "bottom": int(marg.get('bottom', 0)) if marg is not None else 0,
                    }
                    # 셀 안 문단(subList) 파싱: 문단별 paraPrIDRef + 런별 charPrIDRef + 텍스트
                    cell_paras = []
                    sublist = tc.find('hp:subList', NS)
                    if sublist is not None:
                        for cp in sublist.findall('hp:p', NS):
                            pp_ref = int(cp.get('paraPrIDRef', 0))
                            cell_runs = []
                            for cr in cp.findall('hp:run', NS):
                                cr_ref = int(cr.get('charPrIDRef', 0))
                                txt = "".join((t.text or "") for t in cr.findall('hp:t', NS))
                                cell_runs.append((cr_ref, txt))
                            cell_paras.append({"paraPrIDRef": pp_ref, "runs": cell_runs})
                    if not cell_paras:
                        # subList 없음(본문 외 표 등): 텍스트를 한 문단으로
                        cell_text = "".join((t.text or "") for t in tc.iter(HP_T))
                        cell_paras = [{"paraPrIDRef": 0, "runs": [(0, cell_text)]}]
                    cells.append({
                        "paras": cell_paras,
                        "width": cell_w,
                        "height": cell_h,
                        "rowSpan": rowSpan,
                        "colSpan": colSpan,
                        "cellMargin": cellMargin,
                        "row": row,
                        "col": col,
                    })
                # 행별로 그룹화
                rows = {}
                for cell in cells:
                    rows.setdefault(cell["row"], []).append(cell)
                max_row = max(rows.keys()) if rows else -1
                tbl_info["rows"] = [rows.get(r, []) for r in range(max_row + 1)] if max_row >= 0 else []
                tbl_info["rowCnt"] = rowCnt
                tbl_info["colCnt"] = colCnt
            # 텍스트 런
            texts = []
            for t in run.findall('hp:t', NS):
                if t.text:
                    texts.append(t.text)
            if texts or not tbl_info:
                runs.append((charPrIDRef, "".join(texts)))

        if tbl_info is not None:
            out.append({
                "paraPrIDRef": paraPrIDRef,
                "pageBreak": pageBreak,
                "runs": [],
                "is_table_para": True,
                "tbl_info": tbl_info,
            })
        else:
            out.append({
                "paraPrIDRef": paraPrIDRef,
                "pageBreak": pageBreak,
                "runs": runs,
                "is_table_para": False,
            })
    return out


def _build_temp_hwpx(structure, style, report_kind, ministry):
    """실제 생성과 같은 구조로 임시 HWPX를 만들어 경로 반환. 입력 structure는 바꾸지 않는다."""
    s = json.loads(json.dumps(structure or {}))
    s.setdefault("body", [])
    if not s.get("date", "").strip():
        from datetime import date
        s["date"] = date.today().strftime("%Y. %m. %d.")
    s = RP._convert_table_titles(s)   # build_document와 같게 표 제목 키 → caption 블록
    with tempfile.NamedTemporaryFile(suffix=".hwpx", delete=False) as tf:
        tmp_path = tf.name
    try:
        org = ministry or ""
        RP.compose(org, s, tmp_path, style=style, report_kind=report_kind)
        return tmp_path
    except Exception:
        Path(tmp_path).unlink(missing_ok=True)
        raise


def _read_hwpx(tmp_path):
    """임시 HWPX를 읽어 (header_xml_str, section_xml_str) 반환."""
    with zipfile.ZipFile(tmp_path) as z:
        header = z.read("Contents/header.xml").decode("utf-8")
        section = z.read("Contents/section0.xml").decode("utf-8")
    return header, section


# ── 줄 나눔 / 폭 계산 helpers ──────────────────────────────────────────────────

def _run_width(run_text, charPr, w=WIDTHS):
    """한 런의 텍스트 폭(HWPUNIT)."""
    if not run_text:
        return 0
    pt = charPr["height"] / 100.0
    return F.width(run_text, pt, charPr["spacing"], charPr["ratio"], w.get(charPr["font_face"]) or w.get("바탕"))


def _para_first_rest_width(W, paraPr):
    """문단의 첫 줄 폭 / 나머지 줄 폭(HWPUNIT)."""
    left = paraPr.get("left", 0) or 0
    intent = paraPr.get("intent", 0) or 0
    first = W - left - (intent if intent > 0 else 0)
    rest = W - left - (-intent if intent < 0 else 0)
    return first, rest


def _wrap_paragraph(runs, charPrs, paraPr, W, line, w=WIDTHS):
    """문단 런 목록 → [(줄텍스트, 줄maxPt, 줄lineH), ...]."""
    if not runs:
        return []

    # prefix 런 찾기: spacing=0, ratio=100, 텍스트가 기호·공백만
    prefix_runs = []
    body_runs = []
    for cpr_id, txt in runs:
        cp = charPrs.get(cpr_id)
        if cp is None:
            body_runs.append((cpr_id, txt))
            continue
        if cp["spacing"] == 0 and cp["ratio"] == 100 and txt and all(c in "□■ㅇ○◦❍※- *" or c == " " for c in txt):
            prefix_runs.append((cpr_id, txt))
        else:
            body_runs.append((cpr_id, txt))

    # prefix 폭
    prefix_w = sum(_run_width(txt, charPrs.get(cpr_id) or {}, w) for cpr_id, txt in prefix_runs)

    first_w, rest_w = _para_first_rest_width(W, paraPr)
    first_text_w = max(0, first_w - prefix_w)

    # 본문 텍스트 결합
    body_text = "".join(txt for _, txt in body_runs).replace("\u00a0", " ")

    if not body_text.strip():
        # 빈 문단(공백만): 한 줄로 처리, 높이는 첫 런의 pt 사용
        pt = 15.0
        for cpr_id, txt in runs:
            cp = charPrs.get(cpr_id)
            if cp:
                pt = cp["height"] / 100.0
                break
        line_h = int(pt * line)
        return [("", pt, line_h)]

    # 본문 대표 charPr (첫 body 런)
    if body_runs:
        rep_cpr_id, _ = body_runs[0]
        rep_cp = charPrs.get(rep_cpr_id) or {}
        pt = rep_cp.get("height", 1500) / 100.0
        spacing = rep_cp.get("spacing", 0)
        ratio = rep_cp.get("ratio", 100)
        font = rep_cp.get("font_face", "바탕")
        wcfg = w.get(font) or w.get("바탕")
    else:
        pt = 15.0
        spacing = 0
        ratio = 100
        wcfg = w.get("바탕")

    lines = F.wrap(body_text, pt, spacing, first_text_w, rest_w, ratio, wcfg)

    result = []
    for li, line_text in enumerate(lines):
        max_pt = pt
        if li == 0 and prefix_runs:
            for cpr_id, _ in prefix_runs:
                cp = charPrs.get(cpr_id)
                if cp:
                    max_pt = max(max_pt, cp["height"] / 100.0)
        line_h = int(max_pt * line)
        result.append((line_text, max_pt, line_h))
    return result


def _count_lines(runs, charPrs, paraPr, W, line, w=WIDTHS):
    """문단 줄 수."""
    return len(_wrap_paragraph(runs, charPrs, paraPr, W, line, w))


def _para_height(runs, charPrs, paraPr, W, line, w=WIDTHS):
    """문단 전체 높이(HWPUNIT). = 줄높이 합 + prev + next."""
    wrapped = _wrap_paragraph(runs, charPrs, paraPr, W, line, w)
    if not wrapped:
        return paraPr.get("prev", 0) + paraPr.get("next", 0)
    line_h_sum = sum(lh for _, _, lh in wrapped)
    return line_h_sum + paraPr.get("prev", 0) + paraPr.get("next", 0)


# ── 표 높이 계산 ───────────────────────────────────────────────────────────────

def _cell_content_height(cell, paraPrs, charPrs, W, w=WIDTHS):
    """셀 안 문단을 셀 안쪽 폭 × 1.03(≤ W)으로 줄 나눔해 쌓은 높이
    (마지막 줄의 줄간격 몫 제외) + cellMargin top + bottom.

    SPEC 4) 방식: 셀 안 각 문단의 run별 charPr(글꼴·크기·자간·장평)와
    해당 문단의 paraPr(line·intent·left)를 쓴다.
    """
    raw_w = cell["width"] - cell["cellMargin"]["left"] - cell["cellMargin"]["right"]
    inner_w = min(raw_w * 1.03, W) if raw_w > 0 else 100

    total_line_h = 0
    last_line_h = 0
    last_max_pt = 0.0
    for para in (cell.get("paras") or []) or []:
        pp_ref = para.get("paraPrIDRef", 0)
        pp = paraPrs.get(pp_ref, {}) if paraPrs else {}
        runs = para.get("runs", [])
        # 빈 문단 처리: run의 charPr height로 줄 하나의 높이만 계산
        if not runs or not any(txt.strip() for _, txt in runs):
            pt = 15.0
            for cr_ref, _ in runs:
                cp = charPrs.get(cr_ref)
                if cp:
                    pt = cp["height"] / 100.0
                    break
            line_h = int(pt * pp.get("line", 130))
            total_line_h += line_h
            last_line_h = line_h
            last_max_pt = pt
            continue
        wrapped = _wrap_paragraph(runs, charPrs, pp, inner_w, pp.get("line", 130), w)
        if not wrapped:
            continue
        for _, max_pt, line_h in wrapped:
            total_line_h += line_h
            last_line_h = line_h
            last_max_pt = max_pt

    if total_line_h == 0:
        return cell["cellMargin"]["top"] + cell["cellMargin"]["bottom"]

    last_h_char = int(last_max_pt * X.PT)
    content_h = total_line_h - (last_line_h - last_h_char)
    return content_h + cell["cellMargin"]["top"] + cell["cellMargin"]["bottom"]


def _row_height(row_cells, paraPrs, charPrs, W, w=WIDTHS):
    """한 행 높이 = rowSpan=1인 셀들 중 max(hp:cellSz height, 내용 높이)."""
    max_h = 0
    for cell in row_cells:
        if cell["rowSpan"] != 1:
            continue
        ch = _cell_content_height(cell, paraPrs, charPrs, W, w)
        # hp:cellSz height와 내용 높이 중 큰 값
        cell_declared_h = cell.get("height", 0) or 0
        eff_h = max(cell_declared_h, ch)
        if eff_h > max_h:
            max_h = eff_h
    return max_h


# ── 페이지 시뮬레이션 ──────────────────────────────────────────────────────────

def _page_body_metrics(page_pr):
    """본문 영역 높이 H와 폭 W(HWPUNIT)."""
    H = page_pr["height"] - page_pr["top"] - page_pr["bottom"] - page_pr["header"] - page_pr["footer"]
    W = page_pr["width"] - page_pr["left"] - page_pr["right"]
    return H, W


def estimate(structure, style="standard", report_kind="standard", ministry="", xml=None):
    """보고서(doc_type report) 분량 예측.

    실제 생성 HWPX를 임시 파일로 만든 뒤 header.xml·section0.xml을 읽어 한글 배치 규칙대로
    페이지를 쌓아 예측한다. xml=(header_xml, section_xml): 이미 조립한 보고서 XML(ReportComposer의 header·section)을
    주면 임시 파일을 만들지 않고 그걸로 잰다(build_document가 저장할 문서를 한 번만 조립해 넘김).
    """
    if not structure.get("body"):
        return {"본문_쪽수": 0, "마지막쪽_채움": 0.0, "본문_줄수": 0, "전체_쪽수": 0}

    if xml is None:
        tmp_path = _build_temp_hwpx(structure, style, report_kind, ministry)
        try:
            xml = _read_hwpx(tmp_path)
        finally:
            Path(tmp_path).unlink(missing_ok=True)
    return _estimate_xml(*xml)


def _estimate_xml(header_xml, section_xml):
    charPrs = _parse_charPr(header_xml)
    paraPrs = _parse_paraPr(header_xml)
    page_pr = _parse_page_pr(section_xml)
    if not page_pr:
        return {"본문_쪽수": 0, "마지막쪽_채움": 0.0, "본문_줄수": 0, "전체_쪽수": 0}

    H, W = _page_body_metrics(page_pr)
    if H <= 0:
        return {"본문_쪽수": 0, "마지막쪽_채움": 0.0, "본문_줄수": 0, "전체_쪽수": 0}

    paragraphs = _parse_section(section_xml)

    # 본문(첫 pageBreak="1" 문단 앞까지)과 전체 구분
    # 첫 pageBreak="1"인 문단(붙임 머리 표 포함)을 찾으면 그 앞까지가 본문
    first_pb_idx = None
    for i, p in enumerate(paragraphs):
        if p["pageBreak"] == 1:
            first_pb_idx = i
            break
    # 첫 pageBreak가 표 문단의 CELL 등이면 본문 구분은 그대로(전체 문서)
    # 실제 보고서에서는 붙임 머리(appx_head)가 pageBreak="1"인 일반 문단

    def simulate(start_idx, end_idx):
        """문단[start_idx:end_idx]을 시뮬레이션. (최종쪽수, 마지막쪽_y, 총줄수, 마지막쪽번호) 반환."""
        y = 0
        page = 1
        total_lines = 0

        for pi in range(start_idx, end_idx):
            p = paragraphs[pi]
            if p["is_table_para"]:
                # ── 표 문단 ──
                # 문단 pageBreak="1"이면 새 쪽에서 시작
                if p["pageBreak"] == 1:
                    page += 1
                    y = 0

                tbl = p["tbl_info"]
                rows = tbl["rows"]
                pageBreak = tbl["pageBreak"]
                repeat_header = tbl["repeatHeader"]

                # 행 높이 계산 (셀 문단의 paraPr line 사용)
                row_heights = []
                for ri, row_cells in enumerate(rows):
                    rh = _row_height(row_cells, paraPrs, charPrs, W, WIDTHS)
                    row_heights.append(rh)

                # 표 위 prev (표 문단의 paraPr prev)
                prev = paraPrs.get(p["paraPrIDRef"], {}).get("prev", 0) or 0
                # 표 아래 next (표 문단의 paraPr next)
                nxt = paraPrs.get(p["paraPrIDRef"], {}).get("next", 0) or 0

                header_row_h = row_heights[0] if row_heights else 0

                # 표 행 수를 본문_줄수에 추가
                total_lines += len(rows)

                if pageBreak in ("TABLE", "CELL"):
                    # 행 단위 나눔
                    # 표 위 prev 더하기
                    y += prev

                    # 첫 행(머리행) 처리
                    if repeat_header and y == 0 and page > 1:
                        # 새 쪽이고 머리행 반복: 머리행 높이 추가
                        y += header_row_h
                    elif row_heights:
                        # 현재 쪽에 머리행 추가
                        if y + header_row_h > H:
                            page += 1
                            y = 0
                            if repeat_header:
                                y += header_row_h
                        else:
                            y += header_row_h

                    # 나머지 행 처리
                    for ri in range(1, len(row_heights)):
                        rh = row_heights[ri]
                        is_last = (ri == len(row_heights) - 1)
                        # 마지막 행은 outMargin까지 포함해야 그 쪽에 남음
                        needed = rh + (tbl.get("outMargin_bottom", 0) if is_last else 0)
                        if y + needed > H:
                            page += 1
                            y = 0
                            if repeat_header:
                                y += header_row_h
                        y += rh
                    y += tbl.get("outMargin_bottom", 0) + nxt  # 표 아래 outMargin + next
                elif pageBreak == "NONE":
                    # 통째로 다음 쪽으로
                    total_tbl_h = prev + sum(row_heights) + tbl.get("outMargin_bottom", 0) + nxt
                    if y + total_tbl_h > H:
                        page += 1
                        y = 0
                    y += total_tbl_h
                else:
                    # 기본: 표 전체가 현재 쪽에 들어가면 그대로, 안 들어가면 통째로 다음 쪽
                    total_tbl_h = prev + sum(row_heights) + tbl.get("outMargin_bottom", 0) + nxt
                    if y + total_tbl_h > H:
                        page += 1
                        y = 0
                    y += total_tbl_h

                continue

            # ── 일반 문단 ──
            paraPr = paraPrs.get(p["paraPrIDRef"], {})
            line = paraPr.get("line", 160)
            prev = paraPr.get("prev", 0)
            nxt = paraPr.get("next", 0)
            widow = paraPr.get("widowOrphan", 0)
            keep_next = paraPr.get("keepWithNext", 0)
            page_break = p["pageBreak"]

            # 줄 나눔
            n_lines = _count_lines(p["runs"], charPrs, paraPr, W, line, WIDTHS)
            total_lines += n_lines
            para_h = _para_height(p["runs"], charPrs, paraPr, W, line, WIDTHS)

            # pageBreak="1"이면 새 쪽
            if page_break == 1:
                page += 1
                y = 0

            # keepWithNext 처리
            if keep_next and pi < end_idx - 1 and not paragraphs[pi + 1]["is_table_para"]:
                next_p = paragraphs[pi + 1]
                next_paraPr = paraPrs.get(next_p["paraPrIDRef"], {})
                next_line = next_paraPr.get("line", 160)
                next_n_lines = _count_lines(next_p["runs"], charPrs, next_paraPr, W, next_line, WIDTHS)
                next_widow = next_paraPr.get("widowOrphan", 0)
                if next_widow == 1 and next_n_lines >= 2:
                    next_first_lines = 2
                else:
                    next_first_lines = 1
                wrapped_next = _wrap_paragraph(next_p["runs"], charPrs, next_paraPr, W, next_line, WIDTHS)
                next_first_h = 0
                if wrapped_next:
                    next_first_h = wrapped_next[0][2]
                    if next_first_lines >= 2 and len(wrapped_next) >= 2:
                        next_first_h += wrapped_next[1][2]
                if y + para_h + next_first_h > H and y > 0:
                    page += 1
                    y = 0

            # 외톨이줄 보호
            if widow == 1 and n_lines >= 2 and y + para_h > H:
                remaining = H - y
                wrapped = _wrap_paragraph(p["runs"], charPrs, paraPr, W, line, WIDTHS)
                if wrapped:
                    last_line_h = wrapped[-1][2]
                    if remaining < last_line_h + prev:
                        page += 1
                        y = 0

            # 문단 쌓기: 줄 단위로 체크 (줄간격 몫은 넘쳐도 됨)
            wrapped = _wrap_paragraph(p["runs"], charPrs, paraPr, W, line, WIDTHS)
            if not wrapped:
                # 빈 문단: prev + next만 더함
                y += prev + nxt
                continue

            # 첫 줄 체크: y + prev + h <= H?
            # 실제로 체크할 것은 y + prev + h_char <= H (h_char = 첫 줄의 글자 높이)
            # h_char = wrapped[0][1] * 100 (pt -> HWPUNIT)
            h_char = int(wrapped[0][1] * X.PT)

            if y + prev + h_char > H:
                # 새 쪽으로
                page += 1
                y = 0

            y += prev
            for li, (_, _, line_h) in enumerate(wrapped):
                if li > 0 and y + int(wrapped[li][1] * X.PT) > H:
                    page += 1
                    y = 0
                    y += prev  # 새 쪽 맨 위에서도 prev 적용
                y += line_h
            y += nxt

        return page, y, total_lines, page

    # 본문 시뮬레이션
    if first_pb_idx is not None:
        body_paras = paragraphs[:first_pb_idx]
    else:
        body_paras = paragraphs

    if body_paras:
        _, body_last_y, body_lines, body_pages = simulate(0, len(body_paras))
        본문_쪽수 = body_pages
        본문_줄수 = body_lines
        마지막쪽_채움_y = body_last_y
    else:
        본문_쪽수 = 0
        본문_줄수 = 0
        마지막쪽_채움_y = 0

    if 본문_쪽수 == 0:
        return {"본문_쪽수": 0, "마지막쪽_채움": 0.0, "본문_줄수": 0, "전체_쪽수": 0}

    마지막쪽_채움 = round(마지막쪽_채움_y / H, 2)

    # 전체 시뮬레이션
    if first_pb_idx is not None:
        _, _, _, 전체_쪽수 = simulate(0, len(paragraphs))
    else:
        _, _, _, 전체_쪽수 = simulate(0, len(paragraphs))

    return {
        "본문_쪽수": 본문_쪽수,
        "마지막쪽_채움": 마지막쪽_채움,
        "본문_줄수": 본문_줄수,
        "전체_쪽수": 전체_쪽수,
    }
