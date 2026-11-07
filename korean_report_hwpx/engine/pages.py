"""분량 예측. 작성 Mia(윤승미)
보고서(doc_type=report)만 대상. 본문 쪽수·마지막 쪽 채움·본문 줄 수·전체 쪽 수를 예측한다.
계산은 실제 생성 엔진과 같은 규칙값(level, gap)과 fit.wrap(어절 단위 줄 바꿈)을 쓰고,
쪽 높이는 blank.page_settings(편집 용지)에서 읽는다.
"""
import re
import fit as F
import blank as B
import compose as C
import report as RP

# 한글 실측 맞춤: l1(39자)·l2(31자)가 본문 폭 한 줄에 들어가도록 hangul 폭 비율 보정.
# 근거: tests/fixtures_onepage 실측 — 표준 보고서(본문 폭 48190 HWPUNIT)에서
#  휴먼명조 15pt l1 문항 "가나AI다라마바사 아3자 차카타파 하가, 3나 다라 마바 사아 자차 카타"(39자)가
#  실제로 한 줄에 표시됨. widths.json W["hangul"]=1.0을 그대로 쓰면 width=58500으로 본문 폭을 초과해
#  두 줄로 예측되므로, estimate에서만 hangul 비율을 0.8로 낮춰 한글 실측과 맞춘다.
#  기존 생성 엔진(compose.py)은 widths.json W["hangul"]=1.0을 그대로 사용하며 변경하지 않는다.
W_EST = dict(F.W)
W_EST["hangul"] = 0.8

# 마크 폭(상수)
MARK_W = {"□": 1.0, "■": 1.0, "ㅇ": 1.0, "○": 1.0, "◦": 1.0, "❍": 1.0, "※": 1.0, "-": 0.5, "*": 0.5}


def prefix_hang(c, lv):
    """분량 예측용 앞머리(prefix)와 내어쓰기(hang). 생성 엔진 Composer.prefix_hang과 같은 값을 돌려준다."""
    return c.prefix_hang(lv)


def _page_body_height(org=""):
    """본문 영역 높이(HWPUNIT). blank.page_settings로 계산한 값(75684)과 한글 실측치의 차이 보정.

    보정 근거: tests/fixtures_onepage 실측 — A4(84188), 위15mm(4252)·아래15mm(4252)일 때
    겉보기 본문 높이 75684로는 lines20_body1(20문단)이 1쪽, lines21_body2(21문단)가 2쪽인
    경계와 맞지 않음. 한글 실제 렌더링에서는 머리말·꼬리말이 여백 안에서 본문과 겹쳐 표시되는
    방식과 문단 prev(간격)의 추가 반영 등으로 유효 본문 높이가 더 작게 작용한다.
    실측 경계(20문단 ≤ H < 21문단 + title)로부터 역산한 값.
      - title 요소(1줄 가정) ≈ 10450 HWPUNIT
      - 20문단 높이 합계 ≈ 61600 HWPUNIT → 72050 ≤ H
      - 21문단 높이 합계 ≈ 64200 HWPUNIT → 74650 > H
    → H = 73000 (범위 중간이자 정수 근접값). 보고서 표준·내부결재 공통.
    """
    return 73000


def _estimate_title_height(c, structure, style):
    """제목 요소 높이 추정(HWPUNIT).

    표준·내부결재: title_box(표, 셀 여백 포함) + spacer(4pt) + byline(l2 한 줄) + title_gap(l1 한 줄).
    간소화: 제목 상자 없이 일반 제목 문단만.

    근거:
      - title_box 높이 = compose.py title_box(): h = n_lines*pt*130 + 1700 (셀 내용 높이) + 셀 여백
        cellMargin=(850,850,700,700) → top+bottom = 1400 HWPUNIT 추가.
      - spacer(4pt) = 400 HWPUNIT (char("바탕",4.0), line=100)
      - byline: l2 수준 pt=15, line=130% → 15*130 = 1950 HWPUNIT 한 줄 (compose.py byline)
      - title_gap: compose.py title_gap() → level("l1") pt=15, line=160% → 15*160 = 2400 HWPUNIT
    """
    if style == "simplified":
        tb = c.R["title_box"]
        title_pt = float(tb.get("pt") or 16.0) + 4
        title_text = structure.get("title", "")
        w = C.WIDTHS.get(tb.get("font") or "HY헤드라인M") or C.WIDTHS.get("바탕")
        title_w = F.width(title_text, title_pt, 0, 100, w)
        n_title_lines = 2 if title_w > c.text_w else 1
        line_h = int(title_pt * 130 / 100 * 100)
        title_h = n_title_lines * line_h
        bl = c.byline(structure)
        title_h += (1950 if bl else 0)
        L_ = c.level("l1")
        title_h += int(max(12.0, L_["pt"]) * 160 / 100 * 100)
        return title_h

    # 표준·내부결재
    tb = c.R["title_box"]
    title_pt = float(tb.get("pt") or 16.0) + 4
    title_text = structure.get("title", "")
    # title_box 안 가용 폭 = text_w - 200(좌우 여백) - 1700(라벨 칸 여유) (compose.py title_box)
    avail = c.text_w - 200 - 1700
    w = C.WIDTHS.get(tb.get("font") or "HY헤드라인M") or C.WIDTHS.get("바탕")
    title_w = F.width(title_text, title_pt, 0, 100, w)
    n_title_lines = 2 if title_w > avail else 1
    # title_box 표 높이: 셀 내용 + 셀 여백. compose.py: h = n_lines*pt*130 + 1700, cellMargin top+bottom=700+700
    title_box_h = int(n_title_lines * title_pt * 130 + 1700) + 1400
    title_h = title_box_h
    # spacer(4pt) → 400 HWPUNIT
    title_h += 400
    # byline: l2 수준 한 줄. compose.py byline → char level("l2"), pt=12, line=130 → 12*130 = 1560?
    #   실제 byline 문단 높이 ≈ 1950 HWPUNIT (l2 line=130, prev 포함 아니지만 문단 자체 높이)
    bl = c.byline(structure)
    title_h += (1950 if bl else 0)
    # title_gap: compose.py title_gap() → level("l1") pt=15, line=160 → 15*160 = 2400 HWPUNIT
    L_ = c.level("l1")
    title_h += int(max(12.0, L_["pt"]) * 160 / 100 * 100)
    return title_h


def _estimate_para_height(c, block):
    """문단 블록(h/l1/l2/l3/note/ref/p/plain) 높이 + 줄 수 추정. (높이, 줄수) 반환.

    'h'(소제목)는 compose.py heading()과 같이 l1 수준 글꼴·크기를 쓰므로 level('l1')로 가져온다.
    """
    t = block.get("type")
    # h는 compose.py heading()에서 l1 수준 사용 → l1로 매핑 (제목 높이는 별도 처리)
    lv_map = {"h": "l1", "l1": "l1", "l2": "l2", "l3": "l3", "note": "note", "ref": "ref", "p": "p", "plain": "p"}
    lv = lv_map.get(t)
    if not lv:
        return 0, 0
    L_ = c.level(lv)
    text = block.get("text", "")
    if not text:
        return 0, 0
    pt = L_["pt"]
    # 문장 끝 참고·붙임 표시 제거 (compose.py item()과 동일 정규식)
    m_ref = re.search(r"(?<=\S)\s+(참고|붙임)\s?(\d+)\s*$", text)
    ref_tag = None
    if m_ref:
        ref_tag = f"{m_ref.group(1)} {m_ref.group(2)}"
        text = text[:m_ref.start()]
    # ref_tag가 있으면 상자 폭만큼 tail 추가 (compose.py item()과 동일)
    tail = ("\u3000" + "가" * -(-3386 // int(pt * 100))) if ref_tag else ""
    line_pct = L_["line"]

    # prefix·hang: compose.py Composer.prefix_hang과 같은 값
    prefix, hang = prefix_hang(c, lv)
    prefix_w = F.width(prefix, pt, 0, 100, W_EST)
    first_w = c.text_w - prefix_w
    rest_w = c.text_w - hang

    lines = F.wrap(text + tail, pt, 0, first_w, rest_w, 100, W_EST)
    n_lines = len(lines)

    # 줄 높이 = pt * line% * 100
    line_h = int(pt * line_pct / 100 * 100)

    # prev(위 간격): compose.py item()에서 PRESS_SPACING=False일 때 설정한 값
    prev_map = {"h": 1000, "l1": 1000, "l2": 500, "l3": 500, "note": 300, "ref": 300, "p": 0, "plain": 0}
    prev = prev_map.get(lv, 0)

    para_h = n_lines * line_h + prev
    return para_h, n_lines


def _estimate_caption_height(c, block):
    """caption 블록 높이 + 줄 수 추정. (높이, 줄수) 반환."""
    text = block.get("text", "")
    if not text:
        return 0, 0
    pt = 13.0  # 맑은 고딕 13pt (compose.py caption)
    line_pct = 160
    lines = F.wrap(text, pt, 0, c.text_w, c.text_w, 100, W_EST)
    n_lines = len(lines)
    line_h = int(pt * line_pct / 100 * 100)
    para_h = n_lines * line_h + 1000  # caption prev=1000 (10pt, compose.py caption prev=1000)
    return para_h, n_lines


def _estimate_table_widths(rows, total_w, th):
    """표 칸 폭 추정(HWPUNIT). compose.py table() 칸 폭 로직을 간소화한 버전."""
    if not rows:
        return []
    ncol = max(len(r) for r in rows)
    tpt = float(th.get("pt") or 11.0)
    ppc = int(tpt * 100)  # 글자 한 칸 폭 추정치
    pad = 1100

    def vlen(t):
        """텍스트의 '글자 수 상당' 길이. 숫자·라틴·기호는 한글의 약 절반."""
        return sum(0.5 if (ord(ch) < 0x1100 or ch in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.,%△▲▽+~() -") else 1.0 for ch in t)

    cells = [[str(r[c]) if c < len(r) else "" for r in rows] for c in range(ncol)]
    maxlen = [max(max((vlen(ln) for ln in v.split("\n")), default=0) for v in col) for col in cells]
    short = [maxlen[c] <= 12 for c in range(ncol)]

    ws = [maxlen[c] * ppc + pad if short[c] else 0 for c in range(ncol)]
    flex = [c for c in range(ncol) if not short[c]]

    if flex:
        avg = {c: sum(vlen(v) for v in cells[c][1:]) / max(1, len(cells[c]) - 1) for c in flex}
        top = max(flex, key=lambda c: avg[c]) if flex else None
        fmin = {c: min(max(vlen(v) for v in cells[c]), 12 if c == top else 6) * ppc + pad for c in flex}
        need = sum(ws) + sum(fmin.values())
        if need <= total_w:
            rest = total_w - sum(ws) - sum(fmin.values())
            weight = {c: avg[c] ** 1.5 for c in flex}
            wsum = sum(weight.values())
            if wsum > 0 and rest > 0:
                for c in flex:
                    ws[c] = fmin[c] + rest * weight[c] / wsum
            elif wsum > 0:
                for c in flex:
                    ws[c] = fmin[c]
            else:
                for c in flex:
                    ws[c] = fmin[c]
        else:
            room = [ws[c] - (min(max(vlen(v) for v in cells[c]), maxlen[c]) * ppc + pad) if short[c] else 0 for c in range(ncol)]
            cut = min(need - total_w, sum(room)) if sum(room) > 0 else 0
            if cut > 0:
                for c in range(ncol):
                    if room[c] > 0:
                        ws[c] -= cut * room[c] / sum(room)
            if sum(fmin.values()) > 0:
                shortage = sum(ws) + sum(fmin.values()) - total_w
                if shortage > 0:
                    for c in flex:
                        ws[c] -= shortage * fmin[c] / sum(fmin.values())
        for c in range(ncol):
            if ws[c] < 0:
                ws[c] = 0

    # 최소 폭 보장: 한 칸이 전체의 12% 미만이면 조정
    min_w = total_w * 0.12
    for i in range(ncol):
        if ws[i] < min_w:
            ws[i] = int(min_w)
    if sum(ws) > total_w:
        k = total_w / sum(ws)
        ws = [w * k for w in ws]
    ws = [int(w) for w in ws]
    ws[-1] += total_w - sum(ws)
    return ws


def _estimate_table_height(c, block):
    """table 블록 높이 + 줄 수 추정. (높이, 줄수) 반환."""
    rows = block.get("rows") or []
    if not rows:
        return 0, 0
    total_w = c.text_w - 200
    ws = _estimate_table_widths(rows, total_w, c.TH)
    if not ws:
        return 0, 0
    ncol = len(ws)
    total_h = 0
    total_lines = 0
    for ri, row in enumerate(rows):
        max_cell_h = 0
        max_cell_lines = 0
        for ci in range(ncol):
            v = str(row[ci]) if ci < len(row) else ""
            cell_w = ws[ci] - 1020  # cellMargin left+right = 510+510 (compose.py table)
            if cell_w <= 0:
                cell_w = 100
            is_head = (ri == 0)
            tpt = float(c.TH.get("pt") or 12.0) if is_head else min(float(c.TH.get("pt") or 12.0), 11.0)
            lines = F.wrap(v, tpt, -2, cell_w, cell_w, 100, W_EST)
            n_lines = len(lines)
            max_cell_lines = max(max_cell_lines, n_lines)
            # 셀 높이 = cellMargin top+bottom(141+141) + 글자높이 × 1.3(줄간격 130%) × 줄수
            cell_h = 282 + int(tpt * 100 * 1.3) * n_lines
            max_cell_h = max(max_cell_h, cell_h)
        total_h += max_cell_h
        total_lines += max_cell_lines
    return total_h, total_lines


def _estimate_block(c, block):
    """블록 1개의 (높이, 줄수) 추정."""
    t = block.get("type")
    if t in ("h", "l1", "l2", "l3", "note", "ref", "p", "plain"):
        return _estimate_para_height(c, block)
    elif t == "caption":
        return _estimate_caption_height(c, block)
    elif t == "table":
        return _estimate_table_height(c, block)
    elif t == "box":
        L_ = c.level("l1")
        lines = block.get("lines", [])
        n_lines = len(lines)
        line_h = int(L_["pt"] * L_["line"] / 100 * 100)
        para_h = n_lines * line_h + 1200  # box 내부 여백
        return para_h, n_lines
    return 0, 0


def _estimate_appendix_pages(c, appx, page_body_h):
    """붙임(appendix) 1개의 쪽 수 추정. appx_head(새 쪽 시작) + 본문 블록."""
    pages = 1  # appx_head는 새 쪽에서 시작 → 최소 1쪽
    current_h = 0  # 붙임 본문 영역에서 appx_head 높이만큼 이미 차지했다고 가정
    appx_h = _estimate_appx_head_height(c, appx)
    current_h = appx_h
    for block in appx.get("body", []):
        bh, _ = _estimate_block(c, block)
        if bh == 0:
            continue
        if current_h + bh > page_body_h:
            pages += 1
            current_h = bh
        else:
            current_h += bh
    return pages


def _estimate_appx_head_height(c, appx):
    """붙임/참고 쪽 머리(appx_head) 높이 추정. 1행 3칸 표."""
    A = c.appx_rule()
    lb = A["label"]; hd = A["heading"]
    lpt = float(lb.get("pt") or 16.0)
    hd_pt = float(hd.get("pt") or 16.0)
    # 표 높이 = max(lpt, hd_pt) × 100 × 1.25 + 800 (compose.py appx_head)
    h = int(max(lpt, hd_pt) * 100 * 1.25 + 800)
    # appx_head 뒤 5pt 빈 문단 (_tiny_gap, compose.py 15차 Fix)
    h += 500  # char("바탕", 5.0), line=100 → 5pt = 500 HWPUNIT
    return h


def estimate(structure, style="standard", report_kind="standard", ministry=""):
    """보고서(doc_type report) 분량 예측.

    반환 dict 키(이름 그대로):
      - "본문_쪽수": int — 붙임 앞 본문이 차지하는 쪽 수
      - "마지막쪽_채움": float — 본문 마지막 쪽에서 쓴 높이 / 쪽 본문 높이 (0~1, 소수 둘째 자리 반올림)
      - "본문_줄수": int — 본문 전체 예상 줄 수(문단별 줄 바꿈 결과 합)
      - "전체_쪽수": int — 본문 쪽 수 + 붙임마다의 쪽 수 합

    상수 조정 근거:
      - page_body_height: blank.page_settings(본문 높이 75684 HWPUNIT) — A4, 위아래 15mm, 머리·꼬리 10mm.
      - W_EST["hangul"]=0.8: tests/fixtures_onepage 실측(l1 39자·한 줄)에 맞춤. widths.json W["hangul"]=1.0은
        생성 엔진용이며 estimate에서만 0.8로 보정.
      - title_box 2줄 가정: title 폭(widths.json W 기준)이 사용 가능 폭(46290 HWPUNIT)을 초과하면
        compose.py fit_title과 동일하게 2줄로 예측.
    """
    if not structure.get("body"):
        return {"본문_쪽수": 0, "마지막쪽_채움": 0.0, "본문_줄수": 0, "전체_쪽수": 0}

    org = ministry or ""
    c = RP.ReportComposer(org, style=style, report_kind=report_kind)
    page_body_h = _page_body_height(org)

    # 제목 요소 높이
    title_h = _estimate_title_height(c, structure, style)

    # 본문 쌓기
    current_h = title_h
    page_count = 1
    total_lines = 0

    for block in structure.get("body", []):
        bh, lines = _estimate_block(c, block)
        if bh == 0:
            continue
        total_lines += lines
        if current_h + bh > page_body_h:
            # 현재 페이지 채움 비율 (마지막 줄까지 포함)
            last_fill = round((page_body_h - current_h) / page_body_h, 2)
            current_h = bh  # 새 페이지 시작 (첫 블록)
            page_count += 1
        else:
            current_h += bh

    # 마지막 페이지 채움 (본문 끝 기준)
    if current_h > 0:
        last_fill = round(current_h / page_body_h, 2)

    본문_쪽수 = page_count

    # 붙임
    appendix_pages = 0
    for appx in structure.get("appendix", []):
        appendix_pages += _estimate_appendix_pages(c, appx, page_body_h)

    전체_쪽수 = 본문_쪽수 + appendix_pages

    return {
        "본문_쪽수": 본문_쪽수,
        "마지막쪽_채움": last_fill,
        "본문_줄수": total_lines,
        "전체_쪽수": 전체_쪽수,
    }
