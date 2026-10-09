"""규칙 기반 개조식 보고서 생성기. 작성 Mia(윤승미)
보도자료 엔진(compose.Composer)의 공통부(빈 HWPX·글자/문단 모양·계층 문단·자간·표·상자·참고 표시)를 그대로 쓰고,
머리(표지·보도시점·담당 표) 대신 보고서 머리(제목 상자·작성일/작성부서 줄)와 붙임 쪽 머리만 바꾼다.
- 본문 규칙값: rules_report/<기관>.json — 보도자료 참고·붙임 구간 1,326건 실측(refs/보고서_서식_규칙.md)
- 기관 미지정·규칙 없음: rules_report/_공통.json(기관 간 최빈값). 기관 미지정이면 기관명 칸은 비운다.
- 본문은 항상 개조식(□ → ㅇ → - → *, ※), 소제목(Ⅰ. 추진 배경 등)은 "h".
- 간소화 모드(style="simplified"): 제목 상자 없음(일반 제목 문단), 표 머리 음영 없음, 번호 자동 부여, 표 병합 금지."""
import json
import re
import sys
from pathlib import Path

import blank as B
import compose as C

ROOT = C.ROOT
COMMON = "공통"
STYLES = ("standard", "simplified")
REPORT_KINDS = ("standard", "internal")


def ministries():
    """보고서 규칙이 있는 기관(공통 제외)."""
    return sorted(p.stem for p in (ROOT / "rules_report").glob("*.json") if not p.stem.startswith("_"))


def _common():
    d = json.loads((ROOT / "rules_report/_공통.json").read_text("utf-8"))
    r = d["pooled"]; it = d.get("items", {})
    v = lambda k, dft: (it.get(k) or {}).get("value", dft)
    # 제목 상자·표 머리는 기관별 최빈값의 기관 간 최빈값(일치율 표: refs/보고서_서식_규칙.md 2절)
    r["title_box"] = dict(r.get("title_box", {}), font=v("상자.font", "HY헤드라인M"), pt=v("상자.pt", 16.0), fill=v("상자.fill", "#000080"),
                          bold=v("상자.bold", False), bracket=v("상자.bracket", "plain"))
    r["table_head"] = dict(r.get("table_head", {}), font=v("표머리.font", "맑은 고딕"), pt=v("표머리.pt", 12.0), fill=v("표머리.fill", "#DFE6F7"),
                           bold=v("표머리.bold", True))
    return r


def resolve(org):
    """기관 이름 → (규칙 파일 이름, 표시할 기관명). 미지정·'공통' → 공통 규칙·기관명 없음, 규칙 없는 기관 → 공통 규칙·기관명 표시."""
    org = (org or "").strip()
    if not org or org in (COMMON, "_공통"): return COMMON, ""
    return (org if org in ministries() else COMMON), org


def load_rules(org):
    key, _ = resolve(org)
    base = _common()
    r = json.loads((ROOT / f"rules_report/{key}.json").read_text("utf-8")) if key != COMMON else json.loads(json.dumps(base))
    r["_base"] = base
    r["style"] = "box"   # 보고서는 개조식(기관 보고서 구간이 문단식이어도 □ㅇ- 로)
    for k in ("title_box", "table_head"):
        r[k] = dict(base[k], **{a: b for a, b in (r.get(k) or {}).items() if b not in (None, "", "없음")})
    return r


class ReportComposer(C.Composer):
    def __init__(self, org, logo_path=None, style="standard", report_kind="standard",
                 line_spacing=None, para_space_before=None, **kw):
        if style not in STYLES:
            raise ValueError(f"style은 'standard' 또는 'simplified': {style}")
        if report_kind not in REPORT_KINDS:
            raise ValueError(f"report_kind은 'standard' 또는 'internal': {report_kind}")
        self.rule_key, self.org_name = resolve(org)
        self.style = style
        self.report_kind = report_kind
        # 내부 결재 보고서: 본문 줄 간격 150%, 항목 문단 위 5pt (지시 2,3)
        # None일 때만 덮어써서 caller 명시값이 우선
        if report_kind == "internal":
            if line_spacing is None:
                line_spacing = 150
            if para_space_before is None:
                para_space_before = 5.0
        # 간격 옵션: line_spacing(%), para_space_before(pt) — None이면 규칙값/기본값 사용
        super().__init__(org, logo_path=logo_path, style=style,
                         line_spacing=line_spacing, para_space_before=para_space_before)
        th = self.R["table_head"]
        # 간소화 모드: 표 머리 음영 없음
        # 내부 결재 보고서: 표 머리 음영 없음 또는 회색
        if style == "simplified":
            fill = None
        elif report_kind == "internal":
            fill = "#E8E8E8"  # 회색 음영
        else:
            fill = th.get("fill")
        self.TH = {"fill": fill, "font": th.get("font") or "맑은 고딕", "pt": float(th.get("pt") or 12.0), "bold": bool(th.get("bold", True))}
        # 내부 결재 보고서: 쪽 번호 "- n -" footer 추가 (버그7)
        if report_kind == "internal":
            self._add_internal_footer()


    def _add_outline_numbering(self):
        """간소화 모드: header.xml에 개요 번호(outline numbering) 정의 추가 (항목 3).
        기본 paraPr(id=0)는 heading type="NONE" 유지 — OUTLINE은 번호 항목(l1~l4) paraPr에만 지정.
        본문 텍스트에 이미 글자 번호("1. ", "가. " 등)가 있으므로 HWPX 개요 번호가 중복되지 않도록
        para_pr()에서 heading_level이 지정된 paraPr만 OUTLINE으로 설정."""
        outline_xml = (
            '<hh:outlineNumber id="0">'
            '<hh:numberingLevel level="0"><hh:startNumber value="1"/><hh:format format="1"/><hh:jumpStyle value="1"/></hh:numberingLevel>'
            '<hh:numberingLevel level="1"><hh:startNumber value="1"/><hh:format format="가"/><hh:jumpStyle value="1"/></hh:numberingLevel>'
            '<hh:numberingLevel level="2"><hh:startNumber value="1"/><hh:format format="1"/><hh:jumpStyle value="1"/></hh:numberingLevel>'
            '<hh:numberingLevel level="3"><hh:startNumber value="1"/><hh:format format="가"/><hh:jumpStyle value="1"/></hh:numberingLevel>'
            '</hh:outlineNumber>'
        )
        self.header = re.sub(r'(</hh:refList>)', outline_xml + r'\1', self.header)

    def _add_internal_footer(self):
        """내부 결재 보고서용 footer 추가: 페이지 하단 가운데 '- N -' 형식."""
        footer_xml = (
            '<hh:footers itemCnt="1">'
            '<hp:footer id="0" applyPageType="BOTH">'
            '<hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" vertAlign="CENTER" '
            'linkListIDRef="0" linkListNextIDRef="0" textWidth="0" textHeight="0" hasTextRef="0" hasNumRef="0">'
            '<hp:p id="0" paraPrIDRef="0" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">'
            '<hp:run charPrIDRef="0"><hp:t>- </hp:t></hp:run>'
            '<hp:run charPrIDRef="0"><hp:ctrl><hp:pageNum pageNum="CURRENT" format="DIGIT"/></hp:ctrl></hp:run>'
            '<hp:run charPrIDRef="0"><hp:t> -</hp:t></hp:run>'
            '</hp:p></hp:subList></hp:footer></hh:footers>'
        )
        self.header = re.sub(r'(</hh:refList>)', footer_xml + r'\1', self.header)

    def load(self, org):
        tpl = ROOT / "templates" / f"{org}.json"
        page = json.loads(tpl.read_text("utf-8")).get("page", {}) if org and tpl.exists() else {}
        return load_rules(org), {"page": page}

    def level(self, lv):
        out = super().level(lv)
        src = self.R["levels"].get(lv) or {}
        if lv == "l1" and src.get("font") == "HY헤드라인M":   # 보고서 □는 제목 서체를 쓰는 기관이 많음(9/31) — 그대로 둠
            out["font"], out["pt"] = "HY헤드라인M", src.get("pt") or out["pt"]
        # 간소화 모드 / 내부 결재 보고서: 본문 줄 간격 (line_spacing 옵션 우선, 없으면 150%)
        if (self.style == "simplified" or self.report_kind == "internal") and lv in ("l1", "l2", "l3", "p"):
            out["line"] = self.line_spacing if self.line_spacing is not None else 150
        return out

    def gap(self, a, b):
        """문단 간격. 간소화 모드일 때는 기본 간격 대신 지정된 간격 사용.
        - caption 앞: 10pt (표 제목 위, 고정)
        - l1/l2/l3/note/ref/p 앞: para_space_before 옵션 (기본 5pt)
        - h 앞: 10pt (소제목 위, 고정)
        - 그 외: 기본 gap_pt 사용
        pt 값은 paraPr의 prev(앞 간격) 값으로 반영되어 옵션 변경 시 다른 paraPr 생성.
        """
        if self.style == "simplified":
            if b == "caption":
                pt = 10.0  # 표 제목 위 10pt (고정)
            elif b in ("l1", "l2", "l3", "note", "ref", "p"):
                pt = self.para_space_before if self.para_space_before is not None else 5.0
            elif b == "h":
                pt = 10.0  # 소제목 위 10pt (고정)
            else:
                pt = self.gap_pt(a, b)  # 기본 간격
        else:
            pt = self.gap_pt(a, b)
        if pt is None:
            return None
        L_ = self.level("p" if self.R.get("style") == "para" else "l1")
        # pt를 prev 값으로 반영한 paraPr 사용 (간격 옵션이 paraPr의 prev로 반영됨)
        pid = self.para_pr("JUSTIFY", L_["line"], prev=int(pt * 100))
        return self.p(pid, [(self.char(L_["font"], pt), "")])

    # ── 보고서 머리 ──
    def box_char(self, **kw):
        tb = self.R["title_box"]
        return self.ch({"font": tb.get("font") or "HY헤드라인M", "pt": float(tb.get("pt") or 16.0), "bold": bool(tb.get("bold")), **kw})

    def title_box(self, doc):
        """제목 상자: 1행 1칸 표, 위·아래 굵은 선(기관 상자 색), 제목 서체(상자 라벨 서체) +4pt 가운데.
        간소화 모드(style="simplified"): 제목 상자 없이 일반 제목 문단으로 표시.
        내부 결재 보고서(report_kind="internal"): 1×3 라벨 칸 없이 제목만 있는 단순 상자."""
        if self.style == "simplified":
            return self._simplified_title(doc)
        if self.report_kind == "internal":
            return self._internal_title_box(doc)
        tb = self.R["title_box"]; width = self.text_w - 200
        spec, lines = self.fit_title(doc.get("title") or "", {"font": tb.get("font") or "HY헤드라인M", "pt": float(tb.get("pt") or 16.0) + 4,
                                                             "bold": False, "spacing": -3}, width - 1700)
        cp = self.ch(spec)
        paras = "".join(self.p(self.para_pr("CENTER", 130), [(cp, ln)]) for ln in lines)
        h = int(len(lines) * spec["pt"] * 130 + 1700)
        bf = self.border_sides(("top", "bottom"), "0.5 mm", tb.get("fill") or "#000080")
        cell = self.cell(0, 0, width, h, paras, bf, margin=(850, 850, 700, 700))
        return self.tbl_para([cell], 1, 1, width, h, self.border(None, "NONE"))

    def _internal_title_box(self, doc):
        """내부 결재 보고서 제목 상자: 라벨 칸 없이 제목만, HY헤드라인M, 위·아래 선."""
        tb = self.R["title_box"]; width = self.text_w - 200
        spec, lines = self.fit_title(doc.get("title") or "", {"font": tb.get("font") or "HY헤드라인M", "pt": float(tb.get("pt") or 16.0) + 4,
                                                             "bold": False, "spacing": -3}, width - 1700)
        cp = self.ch(spec)
        paras = "".join(self.p(self.para_pr("CENTER", 130), [(cp, ln)]) for ln in lines)
        h = int(len(lines) * spec["pt"] * 130 + 1700)
        bf = self.border_sides(("top", "bottom"), "0.5 mm", tb.get("fill") or "#000080")
        cell = self.cell(0, 0, width, h, paras, bf, margin=(850, 850, 700, 700))
        return self.tbl_para([cell], 1, 1, width, h, self.border(None, "NONE"))

    def _simplified_title(self, doc):
        """간소화 모드: 제목 상자 없이 일반 제목 문단(중앙 정렬, HY헤드라인M, +4pt)."""
        tb = self.R["title_box"]
        width = self.text_w
        spec, lines = self.fit_title(doc.get("title") or "", {"font": tb.get("font") or "HY헤드라인M", "pt": float(tb.get("pt") or 16.0) + 4,
                                                             "bold": False, "spacing": -3}, width)
        cp = self.ch(spec)
        return "".join(self.p(self.para_pr("CENTER", 130), [(cp, ln)]) for ln in lines)

    def byline(self, doc):
        """작성일·작성부서 줄(오른쪽 정렬).
        내부 결재 보고서(report_kind="internal"): "'26. 10. 8.(목) / 과·팀명" 형식(기관명 없음).
        표준 보고서: "2026. 10. 8.  부서명" 형식."""
        date = doc.get("date") or ""
        dept = doc.get("dept") or ""
        if not date.strip() and not dept.strip(): return None

        if self.report_kind == "internal":
            # 내부 결재: "'26. 10. 8.(목) / 과·팀명" 형식
            # 날짜 형식 변환: "2026. 10. 8." → "'26. 10. 8.(목)"
            date_str = self._format_internal_date(date)
            parts = [date_str, dept.strip()]
            txt = "  /  ".join(p for p in parts if p.strip())
        else:
            # 표준: "2026. 10. 8.  부서명  기관명" 형식
            parts = [date, self.org_name, dept]
            txt = "  ".join(p.strip() for p in parts if p.strip())

        if not txt.strip(): return None
        L_ = self.level("l2")
        return self.p(self.para_pr("RIGHT", 130), [(self.char(L_["font"], 12.0, -2), txt)])

    def _format_internal_date(self, date_str):
        """내부 결재용 날짜 형식 변환: '2026. 10. 8.' -> "'26. 10. 8.(목)'"."""
        import datetime, re
        m = re.match(r"(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})\.?", date_str)
        if not m: return date_str
        year, month, day = m.group(1), m.group(2), m.group(3)
        short_year = year[2:]
        # 요일: datetime.date.weekday() 사용 (월=0 → "월화수목금토일")
        wd = datetime.date(int(year), int(month), int(day)).weekday()
        weekday = ["월", "화", "수", "목", "금", "토", "일"][wd]
        return f"'{short_year}. {month}. {day}.({weekday})"

    def heading(self, text):
        """소제목(Ⅰ. 추진 배경 등): 상자 서체, □ 크기 +1pt, 다음 문단과 같은 쪽."""
        L_ = self.level("l1"); tb = self.R["title_box"]
        hc = self.char(tb.get("font") or "HY헤드라인M", L_["pt"] + 1, -2, bool(tb.get("bold")))
        # 간소화 모드: 개요 수준 지정 안 함 (6차 수정)
        return self.p(self.para_pr("JUSTIFY", L_["line"], keep=True, heading_level=None),
                      [(hc, text.strip("* "))], outline_level=None)

    # ── 조립 ──
    def build(self, doc, dst):
        out = []
        if self.logo_path:   # 사용자가 준 로고(선택): 제목 상자 위 가운데, 높이 12mm 안
            bid, pw, ph = self.add_image(self.logo_path)
            out.append(self.p_raw(self.para_pr("CENTER", 100), self.char("바탕", 10.0), self.picture(bid, pw, ph, 40 * C.HU_MM, 12 * C.HU_MM)))
        out.append(self.title_box(doc))
        bl = self.byline(doc)
        out += [self.spacer(4.0), bl] if bl else []
        out.append(self.title_gap())
        sec = B.sec_pr(self.L.get("page", {}))
        # 내부 결재 보고서: footerRef 추가 (버그7)
        if self.report_kind == "internal":
            sec = re.sub(r'</hp:secPr>', '<hp:footerRef idRef="0"/></hp:secPr>', sec)
        out[0] = re.sub(r"(<hp:p\b[^>]*>)", lambda m: m.group(1) + f'<hp:run charPrIDRef="0">{sec}</hp:run>', out[0], count=1)
        self.blocks(doc.get("body", []), out)
        for k, a in enumerate(doc.get("appendix", []), 1):   # 붙임·참고: 새 쪽
            self.blocks([{"type": "appx_h", "text": a.get("title") or f"붙임 {k}", "heading": a.get("heading", "")}] + a.get("body", []), out)
        out = [o for o in out if o]
        section = B.section_xml(out)
        prv = "\n".join(t for t in (re.sub(r"<[^>]+>", "", x.replace("<hp:nbSpace/>", " ")) for x in re.findall(r"<hp:t>(.*?)</hp:t>", section)) if t.strip())
        import html
        B.save(dst, self.header, section, self.images, html.unescape(prv)[:1000], "보고서")
        return dst

    def _unroll_table_merges(self, rows):
        """간소화 모드: 표 셀 병합이 있으면 같은 값을 행마다 반복하도록 풀어 쓴다.
        병합 셀은 {'text': '값', 'merge': {'row': N, 'col': M}} 형식.
        row=N은 세로 병합 행 수, col=M은 가로 병합 열 수."""
        if not rows: return rows
        nrows = len(rows)
        ncol = max(len(r) for r in rows)
        # 병합 정보: (ri, ci) -> (rowspan, colspan, text)
        merges = {}

        for ri, row in enumerate(rows):
            for ci, cell in enumerate(row):
                if isinstance(cell, dict) and cell.get("merge"):
                    merge = cell["merge"]
                    rowspan = merge.get("row", 1)
                    colspan = merge.get("col", 1)
                    text = cell.get("text", "")
                    merges[(ri, ci)] = (rowspan, colspan, text)

        # 병합을 풀어서 각 행에 값 채우기
        result = []
        for ri in range(nrows):
            row_data = rows[ri]
            new_row = []
            for ci in range(ncol):
                cell = row_data[ci] if ci < len(row_data) else ""
                if isinstance(cell, dict) and cell.get("merge"):
                    # 병합 시작 위치: 해당 텍스트 사용
                    new_row.append(cell.get("text", ""))
                elif isinstance(cell, dict):
                    new_row.append(cell.get("text", ""))
                else:
                    # 일반 셀 또는 병합 대상 위치
                    val = str(cell) if cell else ""
                    if not val:
                        # 위쪽 병합 확인
                        for look_ri in range(ri - 1, -1, -1):
                            if (look_ri, ci) in merges:
                                rowspan, colspan, text = merges[(look_ri, ci)]
                                if ri < look_ri + rowspan:
                                    val = text
                                    break
                            # 중간에 일반 값이 있으면 중단
                            if look_ri < len(rows) and ci < len(rows[look_ri]):
                                c = rows[look_ri][ci]
                                if not (isinstance(c, dict) and c.get("merge")):
                                    if isinstance(c, dict):
                                        if c.get("text"): break
                                    elif str(c) if c else "": break
                    if not val:
                        # 왼쪽 병합 확인
                        for look_ci in range(ci - 1, -1, -1):
                            if (ri, look_ci) in merges:
                                rowspan, colspan, text = merges[(ri, look_ci)]
                                if ci < look_ci + colspan:
                                    val = text
                                    break
                            if look_ci < len(row_data):
                                c = row_data[look_ci]
                                if not (isinstance(c, dict) and c.get("merge")):
                                    if isinstance(c, dict):
                                        if c.get("text"): break
                                    elif str(c) if c else "": break
                    new_row.append(val)
            result.append(new_row)
        return result


def _simplify_numbers(s):
    """구조 JSON의 body와 appendix에 간소화 모드 번호(Ⅰ. 1. 가. 1) 가))를 자동 부여.
    level은 h=0, l1=1, l2=2, l3=3, 그 아래는 4(가)로 처리. 사용자가 번호를 직접 쓰지 않음."""
    counters = [0, 0, 0, 0, 0]  # Ⅰ., 1., 가., 1), 가) 카운터

    def _number_for_level(level):
        """수준에 따른 번호 문자열 반환. 리셋은 _process_body에서 처리."""
        if level == 0:  # h (소제목)
            counters[0] += 1
            roman = ["Ⅰ", "Ⅱ", "Ⅲ", "Ⅳ", "Ⅴ", "Ⅵ", "Ⅶ", "Ⅷ", "Ⅸ", "Ⅹ"]
            return f"{roman[counters[0] - 1]}. "
        elif level == 1:  # l1
            counters[1] += 1
            return f"{counters[1]}. "
        elif level == 2:  # l2
            counters[2] += 1
            gajja = ["가", "나", "다", "라", "마", "바", "사", "아", "자", "차", "카", "타", "파", "하"]
            return f"{gajja[counters[2] - 1]}. "
        elif level == 3:  # l3
            counters[3] += 1
            return f"{counters[3]}) "
        else:  # level >= 4: 가)
            counters[4] += 1
            gajja = ["가", "나", "다", "라", "마", "바", "사", "아", "자", "차", "카", "타", "파", "하"]
            return f"{gajja[counters[4] - 1]}) "
        return ""

    def _process_body(body):
        result = []
        for b in body:
            typ = b.get("type")
            new_b = dict(b)
            if typ in ("h", "l1", "l2", "l3"):
                level = {"h": 0, "l1": 1, "l2": 2, "l3": 3}[typ]
                # 번호 수준 리셋: 상위 수준 등장 시 하위 카운터만 리셋 (자기 카운터는 증가만)
                if typ == "h":
                    counters[1] = 0; counters[2] = 0; counters[3] = 0; counters[4] = 0
                elif typ == "l1":
                    counters[2] = 0; counters[3] = 0; counters[4] = 0  # l2, l3, l4 리셋
                elif typ == "l2":
                    counters[3] = 0; counters[4] = 0  # l3, l4 리셋
                elif typ == "l3":
                    counters[4] = 0  # l4 리셋
                new_b["text"] = _number_for_level(level) + b.get("text", "")
            elif typ in ("note", "ref"):
                # note/ref는 현재 l1 수준 유지
                pass
            if "body" in b:
                new_b["body"] = _process_body(b["body"])
            result.append(new_b)
        return result

    s = dict(s)
    s["body"] = _process_body(s.get("body") or [])
    s["appendix"] = [dict(a, body=_process_body(a.get("body") or [])) for a in s.get("appendix") or []]
    return s


def _add_table_numbers(s):
    """간소화 모드: caption 앞에 〈표 N〉 형식 자동 번호 부여."""
    table_counter = [0]

    def _process_body(body):
        result = []
        for b in body:
            new_b = dict(b)
            if b.get("type") == "caption":
                table_counter[0] += 1
                new_b["text"] = f"〈표 {table_counter[0]}〉 " + b.get("text", "")
            if "body" in b:
                new_b["body"] = _process_body(b["body"])
            result.append(new_b)
        return result

    s = dict(s)
    s["body"] = _process_body(s.get("body") or [])
    s["appendix"] = [dict(a, body=_process_body(a.get("body") or [])) for a in s.get("appendix") or []]
    return s


def compose(org, doc, dst, override=None, logo_path=None, style="standard", report_kind="standard", **kw):
    if style not in STYLES:
        raise ValueError(f"style은 'standard' 또는 'simplified': {style}")
    if report_kind not in REPORT_KINDS:
        raise ValueError(f"report_kind은 'standard' 또는 'internal': {report_kind}")
    c = ReportComposer(org, logo_path=logo_path, style=style, report_kind=report_kind, **kw); c.override = override or {}
    # 간소화 모드: 번호 부여, 표 제목 번호, 표 병합 풀어쓰기
    if style == "simplified":
        doc = _simplify_numbers(doc)
        doc = _add_table_numbers(doc)
        doc = dict(doc)
        doc["body"] = [dict(b) for b in doc.get("body", [])]
        for b in doc["body"]:
            if b.get("type") == "table":
                b["rows"] = c._unroll_table_merges(b.get("rows", []))
        for a in doc.get("appendix", []):
            a = dict(a)
            a["body"] = [dict(b) for b in a.get("body", [])]
            for b in a["body"]:
                if b.get("type") == "table":
                    b["rows"] = c._unroll_table_merges(b.get("rows", []))
    c.build(doc, dst); return c
