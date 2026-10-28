"""기안문(별지 제1호서식) 생성기. 작성 Mia(윤승미)·Claude 2026-10-14.
근거: 행정업무의 운영 및 혁신에 관한 규정 제7조④⑤⑥, 시행규칙 제2조·제4조·제6조(법제처 2026-01-01 시행본).
서식 값: rules_official/_공통.json에서만 읽는다(코드 상수 금지)."""
import html, json, re
from pathlib import Path

import blank as B
import compose as C
from compose import Composer

ROOT = C.ROOT


def _common():
    return json.loads((ROOT / "rules_official" / "_공통.json").read_text("utf-8"))


# 본문용 항목 번호 접두사 제거 정규식 — report.py/_strip_existing_number와 동일
_EXISTING_NUMBER_RE = re.compile(
    r"^\s*"
    r"(?:"
    r"[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]\."
    r"|[1-9][0-9]?\."
    r"|[가-힣]\."
    r"|[1-9][0-9]?\)"
    r"|[가-힣]\)"
    r")"
    r"\s*"
)


def _strip_existing_number(text):
    """텍스트 앞에 이미 붙은 번호 접두사(Ⅰ. 1. 가. 1) 가) 등)를 제거."""
    if not text:
        return text
    return _EXISTING_NUMBER_RE.sub("", text, count=1)


# 간소화 모드 표 병합 풀어쓰기 — report.py의 ReportComposer._unroll_table_merges 재사용
def _unroll_table_rows(rows):
    """표 행의 병합 셀 풀어쓰기. 병합 dicts를 일반 문자열로 변환."""
    if not rows:
        return rows
    from report import ReportComposer
    rc = ReportComposer("")
    rc.R, rc.L = rc.load("")
    rc.header = C.B.header_xml()
    rc.cache = {}
    rc.text_w = rc.L.get("page", {}).get("width", 59528) - rc.L.get("page", {}).get("left", 5669) - rc.L.get("page", {}).get("right", 5669)
    rc._seq = 7000000
    return rc._unroll_table_merges(rows)


_HANGUL_ORDER = "가나다라마바사아자차카타파하"


def item_label(pat, c):
    """항목 번호 패턴(규칙 body.numbering의 "1." "가." "1)" "가)" "(1)" "(가)" "①" "㉮")과 순번 c(1부터)로 라벨 문자열(뒤 공백 포함). HWPX·마크다운 공통 (Claude 10-14)"""
    h = _HANGUL_ORDER[(c - 1) % len(_HANGUL_ORDER)]
    return {"1.": f"{c}. ", "가.": f"{h}. ", "1)": f"{c}) ", "가)": f"{h}) ", "(1)": f"({c}) ", "(가)": f"({h}) ",
            "①": f"{chr(0x2460 + c - 1)} ", "㉮": f"{chr(0x326E + c - 1)} "}.get(pat, f"{c}. ")


class OfficialComposer(Composer):
    """기안문(별지 제1호서식)composer. compose.Composer를 상속하고 규칙·조립을 overrides."""

    def __init__(self, org, doc, logo_path=None):
        self.org = org
        self.doc = doc
        self.logo_path = logo_path
        self.R = _common()          # rules_official/_공통.json
        self.L = {"page": B.page_settings("")}   # A4 페이지 정보 (blank.page_settings default)
        self.cache = {}
        self.images = []
        self.header = B.header_xml()
        self.base_para = "0"
        self.base_char = "0"
        self._seq = 7000000
        pg = self.L["page"]
        self.text_w = pg.get("width", 59528) - pg.get("left", 5669) - pg.get("right", 5669)
        # 규칙 속기
        self._org_r = self.R["org"]
        self._hl = self.R["head_line"]
        self._body = self.R["body"]
        self._att = self.R["attachments"]
        self._end = self.R["end_mark"]
        self._rec = self.R["recipients"]
        self._appr = self.R["approval_table"]
        self._foot = self.R["footer_lines"]

    # ── 규칙값 (공식 문서 전용) ──

    def level(self, lv):
        """항목 level(l1~l6) → 글꼴·크기·들여쓰기. 규칙은 _공통.json body.*."""
        base = self._body
        pt = float(base.get("pt", 15.0))
        font = base.get("font", "휴먼명조")
        line = int(base.get("line", 160))
        return {"mark": "", "lead": 0, "gap": 1, "font": font, "pt": pt, "line": line}

    def gap_pt(self, a, b):
        return 6.0

    # ── 조립 ──

    def build(self, dst):
        out = []

        # 로고(선택): 두문 여백 위 가운데
        if self.logo_path:
            bid, pw, ph = self.add_image(self.logo_path)
            out.append(self.p_raw(self.para_pr("CENTER", 100), self.char("바탕", 10.0),
                                  self.picture(bid, pw, ph, 40 * C.HU_MM, 12 * C.HU_MM)))

        # ── 두문 ──
        out.extend(self._두문())

        # ── 본문 (항목 번호 자동 부여) ──
        body_out, warnings = self._본문()
        out.extend(body_out)

        # ── 붙임 (마지막 줄에 "끝." 포함) ──
        atts = self.doc.get("attachments") or []
        if atts:
            out.append(self._빈줄(5.0))
            att_out, 끝표시_포함 = self._붙임(atts)
            out.extend(att_out)
        else:
            끝표시_포함 = False

        # ── "끝." 표시 ──
        # - 붙임이 있으면: 마지막 붙임 줄에 이미 "끝." 포함 → 별도 줄 없음
        # - 붙임이 없고 본문이 table로 끝나면: 표 아래 왼쪽 기본선에서 한 글자 띄운 "끝." 줄
        # - 붙임이 없고 본문이 text로 끝나면: 별도 "끝." 줄 (또는 마지막 text 줄에 붙일 수도 있으나,
        #   현재 구조상 별도 줄로 처리)
        body_ended_table = self._본문끝사항(body_out) if not atts else False
        if not 끝표시_포함:
            if body_ended_table:
                out.append(self._빈줄(5.0))
                out.extend(self._끝표시(True, False))
            else:
                # 제4조⑤1호: 본문 마지막 글자에서 한 글자 띄우고 "끝." — 마지막 글 문단 끝에 붙인다 (Claude 10-14)
                gap = self._end.get("gap", "  "); txt = self._end.get("text", "끝.")
                for i in range(len(out) - 1, -1, -1):
                    if isinstance(out[i], str) and "</hp:t>" in out[i] and "<hp:tbl" not in out[i]:
                        k = out[i].rfind("</hp:t>")
                        out[i] = out[i][:k] + html.escape(gap + txt) + out[i][k:]
                        break

        # ── 결문 ──
        out.append(self._빈줄(12.0))
        out.extend(self._결문())

        out = [o for o in out if o]
        sec = B.sec_pr(self.L.get("page", {}))
        out[0] = re.sub(r"(<hp:p\b[^>]*>)", lambda m: m.group(1) + f'<hp:run charPrIDRef="0">{sec}</hp:run>', out[0], count=1)
        section = B.section_xml(out)
        prv = "\n".join(t for t in (re.sub(r"<[^>]+>", "", x.replace("<hp:nbSpace/>", " ")) for x in re.findall(r"<hp:t>(.*?)</hp:t>", section)) if t.strip())
        B.save(dst, self.header, section, self.images, html.unescape(prv)[:1000], "기안문")
        return dst

    # ── 두문 ──

    def _두문(self):
        out = []
        org = self.doc.get("org", "")

        # org 가운데 정렬 큰 글씨
        o = self._org_r
        cp = self.ch({"font": o.get("font"), "pt": float(o.get("pt")), "bold": False})
        pp = self.para_pr("CENTER", 100)
        out.append(self.p(pp, [(cp, org)]))
        out.append(self._빈줄(float(o.get("after_pt", 10.0))))

        # 수신  {to}
        to = self.doc.get("to", "")
        lbl = self._hl.get("labels", {}).get("to", "수신")
        gap = self._hl.get("label_gap", "  ")
        L = self._hl
        cp = self.ch({"font": L.get("font"), "pt": float(L.get("pt")), "bold": False})
        pp = self.para_pr("JUSTIFY", int(L.get("line", 160)))
        out.append(self.p(pp, [(cp, f"{lbl}{gap}{to}")]))

        # (경유)  {via}
        via = self.doc.get("via", "")
        if via:
            vlbl = self._hl.get("labels", {}).get("via", "(경유)")
            vgap = self._hl.get("label_gap", "  ")
            pp2 = self.para_pr("JUSTIFY", int(L.get("line", 160)))
            out.append(self.p(pp2, [(cp, f"{vlbl}{vgap}{via}")]))

        # 제목  {title}
        title = self.doc.get("title", "")
        tlbl = self._hl.get("labels", {}).get("title", "제목")
        out.append(self.p(pp, [(cp, f"{tlbl}{gap}{title}")]))
        out.append(self._가로선())     # 별지 제1호서식: 두문 아래 가로선
        out.append(self._빈줄(6.0))   # 두문 → 본문 간격
        return out

    # ── 본문 ──

    def _본문(self):
        """body 블록을 렌더링하고 warnings(경고)를 반환."""
        out = []
        warnings = []
        numbering = self._body.get("numbering", ["1.", "가.", "1)", "가)", "(1)", "(가)", "①", "㉮"])
        counters = [0] * len(numbering)   # 각 번호 수준별 카운터
        indent = int(self._body.get("indent_per_level", 2))
        pt = float(self._body.get("pt", 15.0))
        font = self._body.get("font", "휴먼명조")
        line = int(self._body.get("line", 160))

        def _번호(level):
            """level에 번호 부여 후 문자열 반환. 상위 레벨 등장 시 하위 카운터 리셋.
            numbering 패턴의 형태(숫자/한글/동그라미/괄호)를 읽어 카운터 순차값을 생성.
            한글 음절은 실제 Unicode 값을 사용한다."""
            if level < 0 or level >= len(counters):
                return ""
            for i in range(level + 1, len(counters)):
                counters[i] = 0
            counters[level] += 1
            c = counters[level]
            pat = numbering[level]
            return item_label(pat, c)

        def _왼쪽들여쓰기(level):
            """둘째 계층(level≥1)부터 상위 번호 폭 + indent_per_level 타 오른쪽."""
            if level <= 0:
                return 0
            # 상위 레벨들의 번호 폭(한 글자 ≈ pt 단위) 합 + 각 레벨당 indent
            widths = 0
            for lv in range(level):
                widths += pt * 100   # 한 글자 폭(HWPUNIT 근사)
            widths += indent * pt * 100 * level
            return int(widths)

        def _process(blocks):
            for b in blocks:
                typ = b.get("type")
                if typ in ("l1", "l2", "l3", "l4", "l5", "l6"):
                    lvl_map = {"l1": 0, "l2": 1, "l3": 2, "l4": 3, "l5": 4, "l6": 5}
                    lvl = lvl_map[typ]
                    text = _strip_existing_number(b.get("text", ""))
                    # 금액 한글 병기 점검 (제2조②)
                    text_raw = b.get("text", "")
                    if _check_amount_needed(text_raw):
                        warnings.append(f"금액 한글 병기 필요(시행규칙 제2조②): {text_raw.strip()}")
                    prefix = _번호(lvl)
                    text = prefix + text
                    left = _왼쪽들여쓰기(lvl)
                    hang = int(pt * 100 * (0.55 * sum(1 for ch in prefix if ord(ch) < 0x3000) + 1.0 * sum(1 for ch in prefix if ord(ch) >= 0x3000)))   # 번호 폭(영문·숫자 반각, 한글 전각)
                    pp = self.para_pr("JUSTIFY", line, indent=-hang, left=left + hang, word=False)   # 둘째 줄부터 번호 다음 글자 위치에 맞춤(내어쓰기)
                    cp = self.char(font, pt)
                    out.append(self.p(pp, [(cp, text)]))
                elif typ == "table":
                    out.append(self._표(b))
                elif typ == "lines":
                    out.extend(self._줄们(b.get("lines", [])))
                elif typ == "note":
                    txt = b.get("text", "")
                    pp = self.para_pr("JUSTIFY", line)
                    cp = self.char(font, pt)
                    out.append(self.p(pp, [(cp, f"* {txt}")]))
                elif typ == "ref":
                    txt = b.get("text", "")
                    pp = self.para_pr("JUSTIFY", line)
                    cp = self.char(font, pt)
                    out.append(self.p(pp, [(cp, f"※ {txt}")]))
                elif typ == "caption":
                    cap = b.get("text", "")
                    pp = self.para_pr("CENTER", line)
                    cp = self.char("맑은 고딕", min(13.0, pt), -2, True)
                    out.append(self.p(pp, [(cp, f"< {cap} >")]))
                elif typ == "h":
                    txt = b.get("text", "")
                    pp = self.para_pr("JUSTIFY", line, keep=True, word=False)
                    cp = self.char(font, pt, bold=True)
                    out.append(self.p(pp, [(cp, txt)]))
                elif typ in ("p", "plain"):
                    txt = b.get("text", "")
                    pp = self.para_pr("JUSTIFY", line)
                    cp = self.char(font, pt)
                    out.append(self.p(pp, [(cp, txt)]))
                # 하위 body 재귀
                if "body" in b:
                    _process(b["body"])

        _process(self.doc.get("body", []))
        return out, warnings

    def _표(self, block):
        """table 블록 렌더링 (Composer.table 재사용)."""
        rows = block.get("rows", [])
        if not rows:
            return ""
        return self.table(rows)

    def _줄们(self, lines):
        """lines 블록 렌더링: 각 줄을 별도 문단."""
        out = []
        pt = float(self._body.get("pt", 15.0))
        font = self._body.get("font", "휴먼명조")
        line = int(self._body.get("line", 160))
        pp = self.para_pr("JUSTIFY", line)
        cp = self.char(font, pt)
        for ln in lines:
            out.append(self.p(pp, [(cp, ln)]))
        return out

    def _본문끝사항(self, body_out):
        """본문 마지막 요소가 table인지 확인. body_out이 비어있으면 False."""
        if not body_out:
            return False
        # 마지막 out 요소가 표 문단인지 확인 (간단한 휴리스틱: <hp:tbl 포함)
        last = body_out[-1]
        return "<hp:tbl" in last if isinstance(last, str) else False

    # ── 붙임 ──

    def _붙임(self, atts):
        """붙임 표시. 1개면 "붙임  {명칭}", 2개 이상이면 "붙임  {번호}. {명칭}" / "      {번호}. {명칭}".
        numbered_from: 첫 번째 항목의 번호는 numbered_from-1(≥1), 두 번째부터는 numbered_from부터.
        반환: (문단 목록, 끝표시_포함_여부). 2개 이상일 때 마지막Attachment 줄에 "  끝." 포함."""
        out = []
        label = self._att.get("label", "붙임")
        gap = self._att.get("label_gap", "  ")
        numbered_from = int(self._att.get("numbered_from", 2))
        first_num = max(1, numbered_from - 1)
        pt = float(self._body.get("pt", 15.0))
        font = self._body.get("font", "휴먼명조")
        line = int(self._body.get("line", 160))
        cp = self.char(font, pt)
        end_gap = self._end.get("gap", "  ")
        end_txt = self._end.get("text", "끝.")

        if len(atts) == 1:
            pp = self.para_pr("JUSTIFY", line)
            txt = f"{label}{gap}{atts[0]}{end_gap}{end_txt}"      # 제4조⑤1호: 붙임 마지막 글자에서 한 글자 띄우고 "끝."
            out.append(self.p(pp, [(cp, txt)]))
            끝표시_포함 = True
        else:
            pp = self.para_pr("JUSTIFY", line)
            out.append(self.p(pp, [(cp, f"{label}{gap}{first_num}. {atts[0]}")]))
            remaining = list(atts[1:])
            for idx, a in enumerate(remaining):
                i = numbered_from + idx
                is_last = (idx == len(remaining) - 1)
                if is_last:
                    txt = f"      {i}. {a}{end_gap}{end_txt}"
                else:
                    txt = f"      {i}. {a}"
                pp2 = self.para_pr("JUSTIFY", line, left=0)
                out.append(self.p(pp2, [(cp, txt)]))
            끝표시_포함 = True
        return out, 끝표시_포함

    # ── 끝 표시 ──

    def _끝표시(self, body_ended_table, has_attachments):
        """끝 표시:
        - 본문이 table로 끝나고 붙임이 없으면: 표 아래 왼쪽 기본선에서 한 글자(2타) 띄운 "끝."
        - 그 외: 본문/붙임 마지막 글자에서 한 글자(2타) 띄운 "끝." (별도 문단)
        문서 전체에서 "끝."은 정확히 한 번."""
        gap = self._end.get("gap", "  ")
        txt = self._end.get("text", "끝.")
        pt = float(self._body.get("pt", 15.0))
        font = self._body.get("font", "휴먼명조")
        line = int(self._body.get("line", 160))
        cp = self.char(font, pt)

        if body_ended_table and not has_attachments:
            # 표 아래 왼쪽 기본선(왼쪽=0)에서 2타 띄운 "끝."
            pp = self.para_pr("JUSTIFY", line, left=0)
            return [self.p(pp, [(cp, f"{gap}{txt}")])]
        else:
            pp = self.para_pr("JUSTIFY", line)
            return [self.p(pp, [(cp, f"{gap}{txt}")])]

    # ── 결문 ──

    def _결문(self):
        out = []
        sender = self.doc.get("sender", "")
        to = self.doc.get("to", "")
        recipients = self.doc.get("recipients") or []
        approval = self.doc.get("approval", {})
        doc_no = self.doc.get("doc_no", {})
        contact = self.doc.get("contact", {})

        # 1. sender 가운데 정렬 큰 글씨
        s = self._org_r  # 오타로 self._org_r를 썼지만 sender 규칙이 별도로 없음 —sender는 _org_r와 동일 폰트라 가정
        # 실제 sender 규칙: _공통.json의 sender 키
        snd = self.R.get("sender", self._org_r)
        cp = self.ch({"font": snd.get("font"), "pt": float(snd.get("pt")), "bold": False})
        pp = self.para_pr("CENTER", 100, prev=int(snd.get("before_pt", 20.0) * 100), keep=True)
        out.append(self.p(pp, [(cp, sender)]))

        # 2. to가 "수신자 참조"면 수신자란
        if to == "수신자 참조":
            lbl = self._rec.get("label", "수신자")
            g = self._rec.get("label_gap", "  ")
            sep = self._rec.get("sep", ", ")
            txt = f"{lbl}{g}{sep.join(recipients)}"
            pt = float(self._body.get("pt", 15.0))
            font = self._body.get("font", "휴먼명조")
            pp2 = self.para_pr("JUSTIFY", int(self._body.get("line", 160)))
            out.append(self.p(pp2, [(self.char(font, pt), txt)]))

        # 3~6. 결재란·협조자·시행/접수·주소·연락처를 테두리 있는 표 하나로 (별지 제1호서식 결문 틀, Claude 10-14)
        out.append(self._결문표(approval, doc_no, contact))
        return out

    def _가로선(self, width="0.12 mm", height=80):
        """가로선 한 줄(아래 변만 있는 1칸 표). 별지 제1호서식의 두문 아래·결문 아래 선."""
        bf = self.border_sides(("bottom",), width=width)
        W = int(self.text_w - 200)
        cell = self.cell(0, 0, W, height, self.p(self.para_pr("LEFT", 100), [(self.char("바탕", 2.0), "")]), bf, margin=(0, 0, 0, 0))
        return self._표블록([cell], 1, 1, W, height, bf)

    def _결문표(self, approval, doc_no, contact):
        """별지 제1호서식 결문: 회색 구분선 → 기안자·검토자·결재권자(직위·서명) 한 줄 → 협조자 → 시행 | 접수 → 우 주소 / 홈페이지 →
        전화번호 팩스번호 / 전자우편 / 공개 구분 → 아래 가로선. 격자 없이 줄글(칸 선 없음), 값은 rules_official."""
        fl, ap = self._foot, self._appr
        cp = self.char(fl.get("font", "맑은 고딕"), float(fl.get("pt", 11.0)))
        cpa = self.char(ap.get("font", "맑은 고딕"), float(ap.get("pt", 11.0)))
        none = self.border_sides(())                                   # 선 없음
        bottom = self.border_sides(("bottom",), width="0.12 mm")      # 마지막 줄 아래 가로선
        W = int(self.text_w - 200)
        def para(text, cpx=cp, align="LEFT"):
            return self.p(self.para_pr(align, 130), [(cpx, text)])
        drafter = approval.get("drafter", {}); reviewers = approval.get("reviewers", []); approver = approval.get("approver", {})
        opinion = ap.get("opinion_text", "(의견 있음)")
        titles = [f"{drafter.get('mark', '')}{drafter.get('title', '')}"] + \
                 [f"{r.get('title', '')}{opinion if r.get('opinion') else ''}" for r in reviewers] + [approver.get("title", "")]
        names = [drafter.get("name", "") or ""] + [r.get("name", "") or "" for r in reviewers] + [approver.get("name", "") or ""]
        k = max(1, len(titles)); w = W // k
        h1 = int(float(fl.get("pt", 11.0)) * 100 * 1.5) + 200
        rows, H, r = [], 0, 0
        # 회색 구분선(서식의 굵은 회색 띠)
        bar_h = int(2.2 * C.HU_MM)
        rows.append(self.cell(0, r, W, bar_h, self.p(self.para_pr("LEFT", 100), [(self.char("바탕", 2.0), "")]), self.border_sides((), fill="#BFBFBF"), colspan=k, margin=(0, 0, 0, 0))); H += bar_h; r += 1
        # 기안자·검토자·결재권자: 직위 (서명은 성명이 있으면 뒤에)
        rows.append("".join(self.cell(i, r, w, h1, para(f"{t}  {n}".rstrip(), cpa), none) for i, (t, n) in enumerate(zip(titles, names)))); H += h1; r += 1
        coords = approval.get("coordinators", [])
        txt = f"{ap.get('coordinator_label', '협조자')}{ap.get('label_gap', '  ')}{' / '.join(c.get('title', '') for c in coords)}" if coords else ap.get("coordinator_label", "협조자")
        rows.append(self.cell(0, r, W, h1, para(txt, cpa), none, colspan=k)); H += h1; r += 1
        issue = f"{fl.get('issue', '시행')}  {doc_no.get('issue', '')} ({_정규화날짜(doc_no.get('issue_date', ''))})"
        if doc_no.get("receive"):
            recv = f"{fl.get('receive', '접수')}  {doc_no.get('receive', '')} ({_정규화날짜(doc_no.get('receive_date', ''))})"
            half = max(1, k // 2)
            rows.append(self.cell(0, r, w * half, h1, para(issue), none, colspan=half) + self.cell(half, r, W - w * half, h1, para(recv), none, colspan=k - half))
        else:
            rows.append(self.cell(0, r, W, h1, para(issue), none, colspan=k))
        H += h1; r += 1
        addr = f"{fl.get('zip', '우')} {contact.get('zip', '')}  {contact.get('address', '')}{fl.get('sep', '  /  ')}{contact.get('homepage', '')}"
        rows.append(self.cell(0, r, W, h1, para(addr), none, colspan=k)); H += h1; r += 1
        cnt = (f"{fl.get('phone', '전화번호')} {contact.get('phone', '')}  {fl.get('fax', '팩스번호')} {contact.get('fax', '')}"
               f"{fl.get('sep', '  /  ')}{contact.get('email', '')}{fl.get('sep', '  /  ')}{contact.get('disclosure', '')}")
        rows.append(self.cell(0, r, W, h1, para(cnt), bottom, colspan=k)); H += h1; r += 1
        return self._표블록(rows, r, k, W, H, none, page_break="TABLE")

    def _표블록(self, rows, nrow, ncol, W, H, bf, page_break="CELL"):
        """compose.table과 같은 배치(글자처럼 취급 끔, 쪽 넘김 가능)로 표 문단을 만든다 — 결문 표가 통째로 다음 쪽으로 밀리지 않게 (Claude 10-14)."""
        from compose import _rid
        tbl = (f'<hp:tbl id="{_rid()}" zOrder="1" numberingType="TABLE" textWrap="TOP_AND_BOTTOM" textFlow="BOTH_SIDES" lock="0" dropcapstyle="None" pageBreak="{page_break}" repeatHeader="0" '
               f'rowCnt="{nrow}" colCnt="{ncol}" cellSpacing="0" borderFillIDRef="{bf}" noAdjust="0"><hp:sz width="{int(W)}" widthRelTo="ABSOLUTE" height="{int(H)}" heightRelTo="ABSOLUTE" protect="0"/>'
               '<hp:pos treatAsChar="0" affectLSpacing="0" flowWithText="1" allowOverlap="0" holdAnchorAndSO="0" vertRelTo="PARA" horzRelTo="COLUMN" vertAlign="TOP" horzAlign="CENTER" vertOffset="0" horzOffset="0"/>'
               '<hp:outMargin left="0" right="0" top="0" bottom="0"/><hp:inMargin left="510" right="510" top="141" bottom="141"/>' + "".join(f"<hp:tr>{r}</hp:tr>" for r in rows) + "</hp:tbl>")
        return (f'<hp:p id="0" paraPrIDRef="{self.para_pr("CENTER", 100, nxt=0)}" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">'
                f'<hp:run charPrIDRef="{self.char("맑은 고딕", 11.0)}">{tbl}<hp:t/></hp:run></hp:p>')

    def _결재란(self, approval):
        """결재란: 첫 행에 기안자·검토자·결재권자 직위(마크+의견), 둘째 행에 서명(name 또는 빈 줄)."""
        out = []
        drafter = approval.get("drafter", {})
        reviewers = approval.get("reviewers", [])
        approver = approval.get("approver", {})
        opinion_text = self._appr.get("opinion_text", "(의견 있음)")
        pt = float(self._appr.get("pt", 11.0))
        font = self._appr.get("font", "맑은 고딕")

        # 첫 행: 직위
        titles = []
        titles.append(f"{drafter.get('mark', '')}{drafter.get('title', '')}")
        for rv in reviewers:
            r_title = rv.get("title", "")
            r_opinion = opinion_text if rv.get("opinion") else ""
            titles.append(f"{r_title}{r_opinion}")
        titles.append(approver.get("title", ""))
        title_line = "  ".join(t for t in titles if t)

        # 둘째 행: 서명 (name이 있으면 표시, 없으면 빈 줄)
        names = []
        names.append(drafter.get("name", "") or "")
        for rv in reviewers:
            names.append(rv.get("name", "") or "")
        names.append(approver.get("name", "") or "")
        name_line = "  ".join(n for n in names if n)

        cp = self.char(font, pt)
        line = int(self._foot.get("line", 150))
        pp = self.para_pr("JUSTIFY", line)
        out.append(self.p(pp, [(cp, title_line)]))
        if name_line:
            out.append(self.p(pp, [(cp, name_line)]))
        else:
            # name이 모두 비어 있으면 빈 줄(서명 자리 표시 아님 — 빈 줄)
            out.append(self.p(pp, [(cp, "")]))
        return out

    def _시행접수(self, doc_no):
        """시행 {issue} ({issue_date}) [같은 줄 오른쪽 접수 {receive} ({receive_date})]."""
        out = []
        issue = doc_no.get("issue", "")
        issue_date = _정규화날짜(doc_no.get("issue_date", ""))
        receive = doc_no.get("receive", "")
        receive_date = _정규화날짜(doc_no.get("receive_date", ""))
        fl = self._foot
        txt_issue = f"{fl.get('issue', '시행')}  {issue} ({issue_date})"
        if receive:
            txt_receive = f"{fl.get('receive', '접수')}  {receive} ({receive_date})"
            combined = f"{txt_issue}     {txt_receive}"
        else:
            combined = txt_issue
        cp = self.char(fl.get("font", "맑은 고딕"), float(fl.get("pt", 11.0)))
        line = int(fl.get("line", 150))
        pp = self.para_pr("JUSTIFY", line)
        out.append(self.p(pp, [(cp, combined)]))
        return out

    def _주소연락처(self, contact):
        """우 {zip}  {address}  /  {homepage}  다음 줄 전화번호 {phone}  팩스번호 {fax}  /  {email}  /  {disclosure}."""
        out = []
        fl = self._foot
        cp = self.char(fl.get("font", "맑은 고딕"), float(fl.get("pt", 11.0)))
        line = int(fl.get("line", 150))
        sep = fl.get("sep", "  /  ")

        # 우 {zip}  {address}  /  {homepage}
        addr = f"{fl.get('zip', '우')} {contact.get('zip', '')}  {contact.get('address', '')}  /  {contact.get('homepage', '')}"
        pp1 = self.para_pr("JUSTIFY", line)
        out.append(self.p(pp1, [(cp, addr)]))

        # 전화번호 {phone}  팩스번호 {fax}  /  {email}  /  {disclosure}
        cnt = f"{fl.get('phone', '전화번호')} {contact.get('phone', '')}  {fl.get('fax', '팩스번호')} {contact.get('fax', '')}  /  {contact.get('email', '')}  /  {contact.get('disclosure', '')}"
        pp2 = self.para_pr("JUSTIFY", line)
        out.append(self.p(pp2, [(cp, cnt)]))
        return out

    def _빈줄(self, pt):
        """고정 pt 간격 빈 문단."""
        return self.p(self.para_pr("JUSTIFY", 100), [(self.char("바탕", pt), "")])


def _정규화날짜(s):
    """YYYY-MM-DD / YYYY.MM.DD → YYYY. MM. DD. 이미 온점 형식이면 그대로."""
    if not s:
        return ""
    s = s.strip()
    m = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})$", s)
    if m:
        return f"{m.group(1)}. {int(m.group(2))}. {int(m.group(3))}."
    m = re.match(r"^(\d{4})\.(\d{1,2})\.(\d{1,2})$", s)
    if m:
        return f"{m.group(1)}. {int(m.group(2))}. {int(m.group(3))}."
    return s


def _check_amount_needed(text):
    """금액 표기 점검: 금\\d 또는 \\d{1,3}(,\\d{3})+원 형태 뒤에 (금…원) 한글 병기가 없으면 True.
    제2조②: 금액에는 한글 병기를 붙여야 함."""
    if not text:
        return False
    # 패턴: 금\d 또는 \d{1,3}(,\d{3})+원
    amt_re = re.compile(r"금\d|\d{1,3}(?:,\d{3})+원")
    m = amt_re.search(text)
    if not m:
        return False
    # 이미 (금…원) 형태가 뒤에 있는지 확인
    # 예: "금5,000,000원(금오백만원)" → 병기 있음 → False
    korean_re = re.compile(r"\(금[^\)]+원\)")
    if korean_re.search(text):
        return False
    return True


def compose(org, doc, dst, logo_path=None):
    c = OfficialComposer(org, doc, logo_path=logo_path)
    c.build(dst)
    return c
