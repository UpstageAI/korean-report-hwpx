"""규칙 기반 개조식 보고서 생성기. 작성 Mia(윤승미)
보도자료 엔진(compose.Composer)의 공통부(빈 HWPX·글자/문단 모양·계층 문단·자간·표·상자·참고 표시)를 그대로 쓰고,
머리(표지·보도시점·담당 표) 대신 보고서 머리(제목 상자·작성일/작성부서 줄)와 붙임 쪽 머리만 바꾼다.
- 본문 규칙값: rules_report/<기관>.json — 보도자료 참고·붙임 구간 1,326건 실측(refs/보고서_서식_규칙.md)
- 기관 미지정·규칙 없음: rules_report/_공통.json(기관 간 최빈값). 기관 미지정이면 기관명 칸은 비운다.
- 본문은 항상 개조식(□ → ㅇ → - → *, ※), 소제목(Ⅰ. 추진 배경 등)은 "h"."""
import json
import re
from pathlib import Path

import blank as B
import compose as C

ROOT = C.ROOT
COMMON = "공통"


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
    def __init__(self, org, logo_path=None, **kw):
        self.rule_key, self.org_name = resolve(org)
        super().__init__(org, logo_path=logo_path)
        th = self.R["table_head"]
        self.TH = {"fill": th.get("fill"), "font": th.get("font") or "맑은 고딕", "pt": float(th.get("pt") or 12.0), "bold": bool(th.get("bold", True))}

    def load(self, org):
        tpl = ROOT / "templates" / f"{org}.json"
        page = json.loads(tpl.read_text("utf-8")).get("page", {}) if org and tpl.exists() else {}
        return load_rules(org), {"page": page}

    def level(self, lv):
        out = super().level(lv)
        src = self.R["levels"].get(lv) or {}
        if lv == "l1" and src.get("font") == "HY헤드라인M":   # 보고서 □는 제목 서체를 쓰는 기관이 많음(9/31) — 그대로 둠
            out["font"], out["pt"] = "HY헤드라인M", src.get("pt") or out["pt"]
        return out

    # ── 보고서 머리 ──
    def box_char(self, **kw):
        tb = self.R["title_box"]
        return self.ch({"font": tb.get("font") or "HY헤드라인M", "pt": float(tb.get("pt") or 16.0), "bold": bool(tb.get("bold")), **kw})

    def border_sides(self, sides, width="0.4 mm", color="#000000", fill=None):
        """지정한 변에만 선이 있는 테두리(sides: 'top','bottom','left','right' 중)."""
        key = ("bs", tuple(sides), width, color, fill)
        if key in self.cache: return self.cache[key]
        f = f'<hc:fillBrush><hc:winBrush faceColor="{fill}" hatchColor="#999999" alpha="0"/></hc:fillBrush>' if fill else ""
        side = lambda s: (f'<hh:{s}Border type="SOLID" width="{width}" color="{color}"/>' if s in sides
                          else f'<hh:{s}Border type="NONE" width="0.1 mm" color="#000000"/>')
        el = ('<hh:borderFill id="0" threeD="0" shadow="0" centerLine="NONE" breakCellSeparateLine="0"><hh:slash type="NONE" Crooked="0" isCounter="0"/>'
              '<hh:backSlash type="NONE" Crooked="0" isCounter="0"/>' + "".join(side(s) for s in ("left", "right", "top", "bottom")) +
              '<hh:diagonal type="NONE" width="0.1 mm" color="#000000"/>' + f + "</hh:borderFill>")
        self.cache[key] = self._add("borderFills", "borderFill", el); return self.cache[key]

    def title_box(self, doc):
        """제목 상자: 1행 1칸 표, 위·아래 굵은 선(기관 상자 색), 제목 서체(상자 라벨 서체) +4pt 가운데."""
        tb = self.R["title_box"]; width = self.text_w - 200
        spec, lines = self.fit_title(doc.get("title") or "", {"font": tb.get("font") or "HY헤드라인M", "pt": float(tb.get("pt") or 16.0) + 4,
                                                             "bold": False, "spacing": -3}, width - 1700)
        cp = self.ch(spec)
        paras = "".join(self.p(self.para_pr("CENTER", 130), [(cp, ln)]) for ln in lines)
        h = int(len(lines) * spec["pt"] * 130 + 1700)
        bf = self.border_sides(("top", "bottom"), "0.5 mm", tb.get("fill") or "#000080")
        cell = self.cell(0, 0, width, h, paras, bf, margin=(850, 850, 700, 700))
        return self.tbl_para([cell], 1, 1, width, h, self.border(None, "NONE"))

    def byline(self, doc):
        """작성일·작성부서 줄(오른쪽 정렬). 기관 미지정이면 기관명 칸은 비움."""
        parts = [doc.get("date") or "", self.org_name, doc.get("dept") or ""]
        if not any(p.strip() for p in parts): return None
        L_ = self.level("l2")
        txt = "  ".join(p.strip() for p in parts if p.strip())
        return self.p(self.para_pr("RIGHT", 130), [(self.char(L_["font"], 12.0, -2), txt)])

    def appx_head(self, label, heading=""):
        """붙임·참고 쪽 머리: 1행 3칸 표(라벨 칸 기관 색 바탕·흰 글자 | 간격 칸 | 제목 칸 아래 선), 서체는 상자 규칙값."""
        tb = self.R["title_box"]; fill = tb.get("fill") or "#000080"
        br = tb.get("bracket") or "plain"
        lab = {"꺾쇠": f"< {label} >", "대괄호": f"[{label}]"}.get(br, label)
        tw = self.text_w - 200; w2 = 400; h = 2000
        pt = float(tb.get("pt") or 16.0); wd = C.WIDTHS.get(tb.get("font")) or C.WIDTHS["바탕"]
        w1 = max(5400, int(C.F.width(lab, pt, 0, 100, wd) * 1.25 + 1400))   # 라벨이 한 줄에 들어가게
        rgb = [int(fill.lstrip("#")[k:k + 2], 16) for k in (0, 2, 4)]
        light = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2] > 150   # 연한 바탕이면 검은 글자
        lab_cp = self.box_char(color="#000000" if light else "#FFFFFF")
        head_spec, _ = self.fit_title(heading, {"font": tb.get("font") or "HY헤드라인M", "pt": float(tb.get("pt") or 16.0), "bold": bool(tb.get("bold"))}, tw - w1 - w2 - 700)
        head_cp = self.ch(head_spec)
        c1 = self.cell(0, 0, w1, h, self.p(self.para_pr("CENTER", 100), [(lab_cp, lab)]), self.border(fill, "SOLID", "0.12 mm", fill))
        c2 = self.cell(1, 0, w2, h, self.p(self.para_pr("CENTER", 100), [(self.char("바탕", 10.0), "")]), self.border(None, "NONE"))
        c3 = self.cell(2, 0, tw - w1 - w2, h, self.p(self.para_pr("LEFT", 100), [(head_cp, heading)]),
                       self.border_sides(("bottom",), "0.4 mm", fill), margin=(400, 141, 141, 141))
        tbl = self.tbl_para([c1 + c2 + c3], 1, 3, tw, h, self.border(None, "NONE"), align="LEFT")
        tbl = re.sub(r'(<hp:p\b[^>]*?)pageBreak="0"', r'\1pageBreak="1"', tbl, count=1)   # 새 쪽에서 시작
        return tbl + self.spacer(10.0)

    def heading(self, text):
        """소제목(Ⅰ. 추진 배경 등): 상자 서체, □ 크기 +1pt, 다음 문단과 같은 쪽."""
        L_ = self.level("l1"); tb = self.R["title_box"]
        hc = self.char(tb.get("font") or "HY헤드라인M", L_["pt"] + 1, -2, bool(tb.get("bold")))
        return self.p(self.para_pr("JUSTIFY", L_["line"], keep=True), [(hc, text.strip("* "))])

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


def compose(org, doc, dst, override=None, logo_path=None, **kw):
    c = ReportComposer(org, logo_path=logo_path); c.override = override or {}
    c.build(doc, dst); return c
