"""규칙 기반 보도자료 생성기. 작성 Mia(윤승미)
원본 문서를 틀로 쓰지 않는다. 빈 HWPX(blank.py)에 규칙값만으로 모든 문단·표를 그린다.
- 기관 서식 수치: templates/<기관>.json (쪽 여백, 표지·보도시점·제목·담당 표의 칸 폭·글꼴·크기·색)
- 본문 규칙값: rules/<기관>.json (계층별 기호·기호 앞 공백·글꼴·크기·줄 간격, 계층 사이 빈 줄) — refs/보도자료_서식_규칙.md
- 내어쓰기 = (기호 앞 공백×0.5 + 기호 폭 + 기호 뒤 공백×0.5) × 글자 크기  (항목 둘째 줄을 내용 첫 글자에 맞춤)
  앞머리 라벨 '(방식) ' 문단도 같음: 둘째 줄은 기호 뒤 첫 글자(괄호면 괄호)에 맞춤
- 빈 줄 = 앞뒤 계층 쌍별 실측 크기(기관값→전체값), 붙여 쓰는 쌍은 빈 줄 없음
- 자간 = 문단별로 0~하한 사이에서 짧은 마지막 줄·어절 중간 끊김을 피하도록 선택
- 표 = 머리행 굵게·음영·가운데, 숫자 오른쪽, 짧은 글 가운데, 긴 글 양쪽
- 기관 로고·슬로건 그림은 넣지 않는다(정부상징 사용 규정). 로고 칸은 같은 크기의 '기관 로고' 자리표시로 두고,
  logo_path·slogan_path를 주면 그 자리에 그림을 넣는다."""
import html, json, random, re, struct
from pathlib import Path
import fit as F
import blank as B

PUA = re.compile("[\U000F0000-\U000FFFFD-]")
PUA_MAP = {"\U000f007e": "☞ ", "\U000f02b1": "①", "\U000f02b2": "②", "\U000f02b3": "③"}  # 한컴 전용 문자 → 표준 문자, 나머지는 제거

ROOT = Path(__file__).resolve().parent.parent
WIDTHS = json.loads((Path(__file__).parent / "widths.json").read_text("utf-8"))
MARK_W = {"□": 1.0, "■": 1.0, "ㅇ": 1.0, "○": 1.0, "◦": 1.0, "❍": 1.0, "※": 1.0, "-": 0.5, "*": 0.5, "": 0}
LANGS = ("hangul", "latin", "hanja", "japanese", "other", "symbol", "user")
HU_MM = 283.465
esc = lambda s: html.escape(s, quote=False).replace("\u00a0", "<hp:nbSpace/>")   # 묶음 빈칸
DASHES = re.compile("[\u2010\u2011\u2012\u2013\u2014\u2015\u2212]")
LEAD_MARK = re.compile(r"^[\s\u00a0\u3000\-·•∙ㅇ○◦❍□■▪◇◆]+")
UNIT = r"(?:\d|원|명|건|%|개|억|만|천|곳|대|종|배|년|월|일|시간|회|가구|세대|kg|km|㎡|㎞)"
NUM_UNIT = re.compile(r"(\d[\d,.]*[천만억조]*)[ \t]+(?=" + UNIT + ")")


HEAD_LABEL = re.compile(r"[(\[〔][^()\[\]〔〕\s][^()\[\]〔〕]{1,5}[)\]〕] ?")   # 문단 앞머리 라벨 2~6자: (목적) [대상] 〔일정〕


def normalize(text, lv=None):
    """원고 텍스트 정리: 대시류 → '-', 계층 문단 앞에 붙은 기호·공백 제거, 숫자와 단위 사이 빈칸 → 묶음 빈칸(줄 끝에서 안 떨어짐)."""
    text = DASHES.sub("-", text or "").strip()
    if lv in ("l1", "l2", "l3"): text = LEAD_MARK.sub("", text)
    return NUM_UNIT.sub(lambda m: m.group(1) + "\u00a0", text)
PLACEHOLDER_CONTACT = {"dept": "○○과", "people": [["책임자", "과장", "이○○", "(044-000-0000)"], ["담당자", "사무관", "김○○", "(044-000-0000)"]]}
DEFAULT_CHAR = {"font": "돋움", "pt": 10.0, "bold": True, "color": "#000000", "spacing": 0, "ratio": 100}


def _rid(): return str(random.randint(10**8, 2 * 10**9 - 1))


def load_rules(org):
    base = json.loads((ROOT / "rules/_전체.json").read_text("utf-8"))
    f = ROOT / f"rules/{org}.json"
    r = json.loads(f.read_text("utf-8")) if f.exists() else base
    r["_base"] = base
    return r


def load_layout(org):
    return json.loads((ROOT / "templates" / f"{org}.json").read_text("utf-8"))


def ministries():
    return sorted(p.stem for p in (ROOT / "templates").glob("*.json"))


def _img_size(b):
    if b[:8] == b"\x89PNG\r\n\x1a\n": return struct.unpack(">II", b[16:24])
    i = 2
    while i < len(b) - 9:
        if b[i] != 0xFF: i += 1; continue
        mk = b[i + 1]; ln = struct.unpack(">H", b[i + 2:i + 4])[0]
        if mk in (0xC0, 0xC1, 0xC2): h, w = struct.unpack(">HH", b[i + 5:i + 9]); return w, h
        i += 2 + ln
    return 800, 600


class Composer:
    def __init__(self, org, logo_path=None, slogan_path=None, placeholder_contact=False):
        self.org = org; self.R, self.L = self.load(org); self.cache = {}
        self.override = {}; self.items = {}; self._seq = 7000000  # polish 루프용: 문단 번호 → 자간
        self.header = B.header_xml(); self.base_para = "0"; self.base_char = "0"
        self.images = []   # [(id, ext, bytes)]
        pg = self.L.get("page", {})
        self.text_w = pg.get("width", 59528) - pg.get("left", 5669) - pg.get("right", 5669)
        self.logo_path, self.slogan_path, self.placeholder_contact = logo_path, slogan_path, placeholder_contact

    TH = {"fill": "#DFE6F7", "font": "맑은 고딕", "pt": 11.0, "bold": True}   # 표 머리 행(보고서는 기관 규칙값으로 바꿈)

    def load(self, org):
        return load_rules(org), load_layout(org)

    # ── 규칙값 ──
    def level(self, lv):
        L_ = self.R["levels"].get(lv) or self.R["_base"]["levels"].get(lv) or {}
        d = {"l1": ("□", 0, 1), "l2": ("ㅇ", 1, 1), "l3": ("-", 3, 1), "note": ("*", 2, 1), "ref": ("※", 1, 1), "p": ("", 2, 0)}[lv]
        out = {"mark": L_.get("mark") if L_.get("mark") is not None else d[0], "lead": L_.get("lead", d[1]), "gap": L_.get("gap", d[2]),
               "font": L_.get("font") or "바탕", "pt": L_.get("pt") or 14.0, "line": L_.get("line") or 160}
        base_lv = self.R["_base"]["levels"].get(lv) or {}
        if (L_.get("n") or 0) < 5 and base_lv.get("pt"): out["pt"] = base_lv["pt"]   # 표본이 적은 계층의 크기는 공통값
        if lv in ("l2", "l3"):  # 하위 항목은 상위 항목보다 오른쪽(공식: 2타씩) — 기관값이 이를 어기면 보정
            prev = self.level("l1" if lv == "l2" else "l2")
            min_lead = prev["lead"] + (1 if lv == "l2" else 2)
            out["lead"] = max(out["lead"], min_lead)
        if lv in ("note", "ref") and out["pt"] > 13: out["pt"] = 12.0
        if lv in ("l1", "l2", "l3", "p"):  # 본문 계층은 같은 본문 글꼴 계열로 (기관 실측의 이상값 방지)
            body = self.R["levels"].get("p" if self.R.get("style") == "para" else "l1") or {}
            if out["font"] in ("HY헤드라인M", "HY울릉도M", "궁서", "맑은 고딕", "돋움") and body.get("font") not in (None, out["font"]):
                out["font"] = body["font"]   # 서체만 본문 계열로, 크기는 그 계층 실측값 유지(□가 ㅇ보다 작아지는 역전 방지)
            if out["font"] in ("궁서", "HY헤드라인M", "HY울릉도M", "HY견명조"): out["font"] = "바탕"  # 본문은 일반 서체
        if lv in ("l2", "l3"):  # 하위 계층 글자는 상위보다 크지 않게(□ ≥ ㅇ ≥ -)
            out["pt"] = min(out["pt"], self.level("l1" if lv == "l2" else "l2")["pt"])
        return out

    def box_gap_pt(self, b):
        """강조 상자 다음 문단: 붙여 쓰지 않고 상자 관련 빈 줄 규칙값(box>b → table>b, 기관값→전체값)을 넣는다."""
        for src in (self.R, self.R["_base"]):
            for k in (f"box>{b}", f"table>{b}"):
                g = src.get("gaps", {}).get(k)
                if g and g.get("pt"): return g["pt"]
        return 10.0

    def gap_pt(self, a, b):
        if b == "h": return 14.0          # 소제목 앞은 한 줄
        if a == "h": return 6.0
        for src in (self.R, self.R["_base"]):
            g = src.get("gaps", {}).get(f"{a}>{b}")
            if g and g["n"] >= 3:
                return None if g.get("none", 0) > g["n"] else g["pt"]
        return 10.0 if a != b else 6.0

    # ── 모양 만들기 ──
    def font_id(self, face, lang="HANGUL"):
        blk = re.search(r'(<hh:fontface lang="%s"[^>]*>)(.*?)(</hh:fontface>)' % lang, self.header, re.S)
        m = re.search(r'<hh:font id="(\d+)" face="%s"' % re.escape(face), blk.group(2))
        if m: return m.group(1)
        nid = str(1 + max([int(v) for v in re.findall(r'<hh:font id="(\d+)"', blk.group(2))] + [-1]))
        nb = blk.group(1) + blk.group(2) + f'<hh:font id="{nid}" face="{face}" type="TTF" isEmbedded="0"/>' + blk.group(3)
        nb = re.sub(r'fontCnt="(\d+)"', lambda z: f'fontCnt="{int(z.group(1)) + 1}"', nb, count=1)
        self.header = self.header.replace(blk.group(0), nb); return nid

    def _add(self, kind, tag, el):
        nid = str(1 + max(int(x) for x in re.findall(r'<hh:%s id="(\d+)"' % tag, self.header)))
        el = re.sub(r'id="\d+"', f'id="{nid}"', el, count=1)
        self.header = self.header.replace(f"</hh:{kind}>", el + f"</hh:{kind}>")
        self.header = re.sub(r'<hh:%s itemCnt="(\d+)"' % kind, lambda z: f'<hh:{kind} itemCnt="{int(z.group(1)) + 1}"', self.header)
        return nid

    def char(self, face, pt, spacing=0, bold=False, color="#000000", ratio=100, sup=False):
        key = ("c", face, pt, spacing, bold, color, ratio, sup)
        if key in self.cache: return self.cache[key]
        base = re.search(r'<hh:charPr id="%s"[^>]*>.*?</hh:charPr>' % self.base_char, self.header, re.S).group(0)
        el = re.sub(r'height="\d+"', f'height="{int(pt * 100)}"', base, count=1)
        el = re.sub(r'textColor="[^"]+"', f'textColor="{color}"', el, count=1)
        el = re.sub(r"<hh:fontRef [^>]*/>", "<hh:fontRef " + " ".join(f'{l}="{self.font_id(face, l.upper())}"' for l in LANGS) + "/>", el)
        el = re.sub(r"<hh:spacing [^>]*/>", "<hh:spacing " + " ".join(f'{l}="{spacing}"' for l in LANGS) + "/>", el)
        el = re.sub(r"<hh:ratio [^>]*/>", "<hh:ratio " + " ".join(f'{l}="{ratio}"' for l in LANGS) + "/>", el)
        el = re.sub(r"<hh:(bold|italic)/>", "", el)
        if bold: el = re.sub(r"(<hh:offset [^>]*/>)", r"\1<hh:bold/>", el, count=1)
        el = re.sub(r"<hh:(supscript|subscript)/>", "", el)
        if sup: el = el.replace("</hh:charPr>", "<hh:supscript/></hh:charPr>")
        self.cache[key] = self._add("charProperties", "charPr", el); return self.cache[key]

    def para_pr(self, align="JUSTIFY", line=160, indent=0, left=0, prev=0, nxt=0, word=True, keep=False):
        key = ("p", align, line, indent, left, prev, nxt, word, keep)
        if key in self.cache: return self.cache[key]
        el = re.search(r'<hh:paraPr id="%s".*?</hh:paraPr>' % self.base_para, self.header, re.S).group(0)
        el = re.sub(r'horizontal="\w+"', f'horizontal="{align}"', el, count=1)
        el = re.sub(r'(<hh:lineSpacing type=")\w+(" value=")\d+', lambda m: f"{m.group(1)}PERCENT{m.group(2)}{line}", el)
        def mg(block, k):
            v = {"intent": indent, "left": left, "right": 0, "prev": prev, "next": nxt}
            for name, val in v.items():
                block = re.sub(r'(<hc:%s value=")-?\d+' % name, lambda m: m.group(1) + str(val * k), block)
            return block
        if "<hp:case" in el:
            el = re.sub(r"<hp:case.*?</hp:case>", lambda m: mg(m.group(0), 1), el, flags=re.S)
            el = re.sub(r"<hp:default>.*?</hp:default>", lambda m: mg(m.group(0), 2), el, flags=re.S)
        else: el = mg(el, 1)
        el = re.sub(r'<hh:border borderFillIDRef="\d+"', '<hh:border borderFillIDRef="1"', el)
        el = re.sub(r'keepWithNext="\d"', 'keepWithNext="%d"' % keep, el)  # 소제목·표 제목은 다음 문단과 같은 쪽에
        # 줄 나눔: 한글 어절 단위(HWPX 값 BREAK_WORD = 한글 '어절', KEEP_WORD = '글자' — 한글 기본 문서가 KEEP_WORD·글자)
        el = re.sub(r'breakNonLatinWord="\w+"', 'breakNonLatinWord="%s"' % ("BREAK_WORD" if word else "KEEP_WORD"), el)
        el = re.sub(r'widowOrphan="\d"', 'widowOrphan="1"', el)
        self.cache[key] = self._add("paraProperties", "paraPr", el); return self.cache[key]

    def border(self, fill=None, line="SOLID", width="0.12 mm", color="#000000"):
        key = ("b", fill, line, width, color)
        if key in self.cache: return self.cache[key]
        f = f'<hc:fillBrush><hc:winBrush faceColor="{fill}" hatchColor="#999999" alpha="0"/></hc:fillBrush>' if fill else ""
        side = lambda s: f'<hh:{s}Border type="{line}" width="{width}" color="{color}"/>'
        el = ('<hh:borderFill id="0" threeD="0" shadow="0" centerLine="NONE" breakCellSeparateLine="0"><hh:slash type="NONE" Crooked="0" isCounter="0"/>'
              '<hh:backSlash type="NONE" Crooked="0" isCounter="0"/>' + side("left") + side("right") + side("top") + side("bottom") +
              '<hh:diagonal type="NONE" width="0.1 mm" color="#000000"/>' + f + "</hh:borderFill>")
        self.cache[key] = self._add("borderFills", "borderFill", el); return self.cache[key]

    # ── 문단 ──
    def p(self, pid, segs, pno="0"):
        return f'<hp:p id="{pno}" paraPrIDRef="{pid}" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">' + \
               "".join(f'<hp:run charPrIDRef="{c}"><hp:t>{esc(t)}</hp:t></hp:run>' for c, t in segs) + "</hp:p>"

    def item(self, lv, text):
        """계층 문단: 기호·공백 접두 + 본문(**굵게** 지원), 내어쓰기 = 접두 폭, 자간 자동."""
        L_ = self.level(lv)
        if lv == "p":
            prefix = " " * L_["lead"]; hang = 0
        else:
            prefix = " " * L_["lead"] + L_["mark"] + " " * max(1, L_["gap"])
            hang = int(round((0.5 * L_["lead"] + MARK_W.get(L_["mark"], 1.0) + 0.5 * max(1, L_["gap"])) * L_["pt"] * 100))
        text = normalize(PUA.sub(lambda m: PUA_MAP.get(m.group(0), ""), text), lv)
        m_ref = re.search(r"(?<=[.다\)함임됨음정요])\s*(참고|붙임)\s?(\d+)\s*$", text)   # 보고서 명사형 종결(~함·~임) 뒤도
        ref_tag = None
        if m_ref: ref_tag = f"{m_ref.group(1)} {m_ref.group(2)}"; text = text[:m_ref.start()]  # 문장 끝 참고 표시
        plain = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
        self._seq += 1; pno = str(self._seq)
        ov = self.override.get(pno)
        ov = list(ov) if isinstance(ov, (tuple, list)) else ([ov, 100] if ov is not None else None)
        tail = ("\u3000" + "가" * -(-3386 // int(L_["pt"] * 100))) if ref_tag else ""   # 참고 표시 자리(빈칸+상자 폭)
        m_lab = HEAD_LABEL.match(text)   # 문단 앞머리 라벨 '(목적)' 등: 기호처럼 자간 0·장평 100 고정
        label = m_lab.group(0) if m_lab else ""
        if label: text = text[len(label):]; plain = plain[len(label):]
        fixed = prefix + label
        if ov: sp, ra, word = (ov + [True])[:3]
        else: (sp, ra), word = self.pick_spacing(plain + tail, L_, hang, fixed), True
        if word == "auto": sp = self.pick_spacing_word(prefix + label + plain, L_, hang); ra = 100; word = True
        self.items[pno] = {"lv": lv, "text": prefix + label + plain, "sp": (sp, ra, word)}
        n = self.char(L_["font"], L_["pt"], sp, ratio=ra); b = self.char(L_["font"], L_["pt"], sp, True, ratio=ra)
        segs = [(self.char(L_["font"], L_["pt"], 0), prefix)] if prefix else []   # 접두(공백·기호)는 자간 0: 같은 계층 기호 위치를 문단 자간과 무관하게 맞춤
        if label: segs.append((self.char(L_["font"], L_["pt"], 0), label))   # 앞머리 라벨도 자간 0·장평 100: 같은 글자 수 라벨은 폭이 같음
        sup = self.char(L_["font"], L_["pt"], sp, ratio=ra, sup=True)
        for k, part in enumerate(re.split(r"\*\*(.+?)\*\*", text)):
            if not part: continue
            for j, bit in enumerate(re.split(r"(?<=\S)(\*{1,3})(?=[\s),.]|$)", part)):  # 문장 속 각주 표시 → 위첨자
                if bit: segs.append((sup if j % 2 else (b if k % 2 else n), bit))
        para_xml = self.p(self.para_pr("JUSTIFY", L_["line"], -hang, word=word is not False, prev=300 if lv in ("note", "ref") and getattr(self, "_after_table", False) else 0), segs, pno)
        if ref_tag:  # 앞 글자와 빈칸 1칸(묶음 빈칸: 줄 끝에서 앞 어절과 떨어지지 않음), 자간 0으로 겹침 방지
            n0 = self.char(L_["font"], L_["pt"], 0, ratio=100)
            para_xml = para_xml.replace("</hp:p>", f'<hp:run charPrIDRef="{n0}"><hp:t><hp:nbSpace/></hp:t></hp:run><hp:run charPrIDRef="{n0}">{self.ref_box(ref_tag)}<hp:t/></hp:run></hp:p>')
        return para_xml

    RATIOS = (100, 98, 96, 95)   # 장평 후보(공무원 관행: 한 줄 맞춤에 장평도 씀)

    def pick_spacing(self, txt, L_, hang, fixed=""):
        """문단 자간·장평 고르기 → (자간, 장평). fixed(기호·라벨 접두)는 자간 0·장평 100 고정 폭으로 첫 줄에서 뺀다.
        ① 줄 수 최소(1~3자 넘치는 문단은 한 줄로) ② 마지막 줄 1~2자·30% 미만 방지 ③ 추정 오차(±2.5%)에도 안정
        ④ 장평 100 우선, 그다음 자간 0에 가까운 값. 장평 하한: 규칙 ratio_min 또는 95%."""
        w = WIDTHS.get(L_["font"]) or WIDTHS.get("바탕")
        fw = F.width(fixed, L_["pt"], 0, 100, w) if fixed else 0
        first, rest = self.text_w - fw, self.text_w - hang
        lo = self.R.get("spacing_min", -8)
        rmin = max(95, int(self.R.get("ratio_min", 95)))
        best = None
        def short(ls, sp, ra):
            last = ls[-1].strip()
            fill = F.width(last, L_["pt"], sp, ra, w) / (rest if len(ls) > 1 else first)
            return len(ls) > 1 and (fill < 0.3 or len(last.replace(" ", "")) <= 2)
        for ra in [r for r in self.RATIOS if r >= rmin]:
            for sp in range(0, max(lo - 3, -10) - 1, -1):   # 규칙 하한에서 안 되면 3%p까지 더 조임
                ls = F.wrap(txt, L_["pt"], sp, first, rest, ra, w, True)  # 어절 단위 줄 나눔
                alt = [F.wrap(txt, L_["pt"], sp, first * k, rest * k, ra, w, True) for k in (0.975, 1.025)]
                risky = sum(len(a) != len(ls) or short(a, sp, ra) for a in alt)
                mid = sum(1 for a, c in zip(ls, ls[1:]) if a and c and not a.endswith(" ") and a[-1].isalnum() and c[0].isalnum())
                key = (len(ls) + (risky > 0) * 1.5, short(ls, sp, ra), risky, sp < lo, mid, 100 - ra, -sp)
                if best is None or key < best[0]: best = (key, (sp, ra))
        return best[1]

    def pick_spacing_word(self, txt, L_, hang):
        """어절 단위 문단: 양쪽 정렬로 벌어지는 폭(줄 여유)이 가장 작은 자간."""
        w = WIDTHS.get(L_["font"]) or WIDTHS.get("바탕"); first, rest = self.text_w, self.text_w - hang
        best = None
        for sp in range(0, -9, -1):
            ls = F.wrap(txt, L_["pt"], sp, first, rest, 100, w, True)
            slack = max([((first if k == 0 else rest) - F.width(l.rstrip(), L_["pt"], sp, 100, w)) for k, l in enumerate(ls[:-1])] or [0])
            key = (len(ls), round(slack / (L_["pt"] * 50)), -sp)
            if best is None or key < best[0]: best = (key, sp)
        return best[1]

    def appx_rule(self):
        """참고·붙임 쪽 머리 규칙: rules_report/_참고머리.json(원본 보도자료 참고 구간 첫 표 실측) 공통값 + 기관값."""
        d = json.loads((ROOT / "rules_report/_참고머리.json").read_text("utf-8"))
        r = json.loads(json.dumps(d["common"])); o = d["orgs"].get((self.org or "").strip()) or {}
        for k in ("cols", "ratio"):
            if k in o: r[k] = o[k]
        for part in ("label", "heading"): r[part].update(o.get(part) or {})
        return r

    def border_sides(self, sides, width="0.4 mm", color="#000000", fill=None):
        """지정한 변에만 선이 있는 테두리. sides: 변 이름 묶음 또는 {변: 'mm 값' | ('mm 값', 색)}."""
        ws = dict(sides) if isinstance(sides, dict) else {s: width for s in sides}
        key = ("bs", tuple(sorted(ws.items())), color, fill)
        if key in self.cache: return self.cache[key]
        f = f'<hc:fillBrush><hc:winBrush faceColor="{fill}" hatchColor="#999999" alpha="0"/></hc:fillBrush>' if fill else ""
        wc = lambda s: ws[s] if isinstance(ws[s], tuple) else (ws[s], color)   # 변별 (굵기, 색)
        side = lambda s: (f'<hh:{s}Border type="SOLID" width="{wc(s)[0]}" color="{wc(s)[1]}"/>' if s in ws
                          else f'<hh:{s}Border type="NONE" width="0.1 mm" color="#000000"/>')
        el = ('<hh:borderFill id="0" threeD="0" shadow="0" centerLine="NONE" breakCellSeparateLine="0"><hh:slash type="NONE" Crooked="0" isCounter="0"/>'
              '<hh:backSlash type="NONE" Crooked="0" isCounter="0"/>' + "".join(side(s) for s in ("left", "right", "top", "bottom")) +
              '<hh:diagonal type="NONE" width="0.1 mm" color="#000000"/>' + f + "</hh:borderFill>")
        self.cache[key] = self._add("borderFills", "borderFill", el); return self.cache[key]

    HEAD_LINES = {"box": ("left", "right", "top", "bottom"), "topbottom": ("top", "bottom"), "bottom": ("bottom",), "none": ()}

    @classmethod
    def head_lines(cls, v):
        """제목 칸 선 규칙값 → 변 목록(box·topbottom·bottom·none 또는 'bottom+left' 같은 변 조합)."""
        v = v or "box"
        return cls.HEAD_LINES.get(v) or tuple(s for s in v.split("+") if s in ("left", "right", "top", "bottom"))

    def appx_head(self, label, heading=""):
        """참고·붙임 쪽 머리(원본 실측 형태): 1행 3칸 표 = 라벨 칸(기관 색 바탕·흰 글자) | 좁은 간격 칸(위아래 선 없음) | 제목 칸.
        제목 칸 선은 기관 실측(공통: 네 변 가는 선, 과기정통부 등: 위아래만, 관세청 등: 아래만). 간격 칸이 라벨과 제목을 떼어 놓는다."""
        A = self.appx_rule(); lb, hd = A["label"], A["heading"]
        tw = self.text_w - 200; ratio = A["ratio"] if A.get("cols", 3) == 3 else [A["ratio"][0], 0.016, 1 - A["ratio"][0] - 0.016]
        mm = lambda v: f"{float(v):g} mm"
        fill = lb.get("fill"); lpt = float(lb.get("pt") or 16.0); lfont = lb.get("font") or "HY헤드라인M"
        wd = WIDTHS.get(lfont) or WIDTHS["바탕"]
        w1 = max(int(tw * ratio[0]), int(F.width(label, lpt, 0, 100, wd) * 1.15 + 600))   # 라벨이 한 줄에 들어가게
        w2 = max(400, int(tw * ratio[1])); w3 = tw - w1 - w2
        h = int(max(lpt, float(hd.get("pt") or 16.0)) * 100 * 1.25 + 800)
        lab_cp = self.char(lfont, lpt, 0, bool(lb.get("bold")), (lb.get("color") or "#FFFFFF") if fill else "#000000")
        head_spec, _ = self.fit_title(heading, {"font": hd.get("font") or "HY헤드라인M", "pt": float(hd.get("pt") or 16.0), "bold": bool(hd.get("bold"))}, w3 - 900)
        head_cp = self.ch(head_spec)
        lw = mm(lb.get("line") or 0.12) if lb.get("line") else None
        bf1 = self.border_sides({s: lw for s in ("left", "right", "top", "bottom")}, color=fill or "#000000", fill=fill) if lw else self.border(fill, "NONE")
        hs = self.head_lines(hd.get("lines")); hw = mm(hd.get("line") or 0.12)
        bf3 = self.border_sides({s: hw for s in hs})
        bf2 = self.border_sides({**({"left": (lw, fill or "#000000")} if lw else {}), **({"right": (hw, "#000000")} if "left" in hs else {})}) if (lw or "left" in hs) else self.border(None, "NONE")
        c1 = self.cell(0, 0, w1, h, self.p(self.para_pr("CENTER", 100), [(lab_cp, label)]), bf1)
        c2 = self.cell(1, 0, w2, h, self.p(self.para_pr("CENTER", 100), [(self.char("바탕", 10.0), "")]), bf2, margin=(0, 0, 0, 0))
        c3 = self.cell(2, 0, w3, h, self.p(self.para_pr("LEFT", 100), [(head_cp, heading)]), bf3, margin=(566, 141, 141, 141))
        tbl = self.tbl_para([c1 + c2 + c3], 1, 3, tw, h, self.border(None, "NONE"), align="LEFT")
        tbl = re.sub(r'(<hp:p\b[^>]*?)pageBreak="0"', r'\1pageBreak="1"', tbl, count=1)   # 새 쪽에서 시작
        L_ = self.level("l1" if self.R.get("style") == "box" else "p")
        return tbl + self.p(self.para_pr("JUSTIFY", 160), [(self.char(L_["font"], 10.0), "")])

    def ref_box(self, label):
        """문장 끝 「참고 1」 표시: 연베이지 바탕·테두리 글상자, 글자처럼 취급(국세청 등 실물과 같은 방식)."""
        cp = self.char("맑은 고딕", 10.0); pp = self.para_pr("CENTER", 100)
        w, h = 3386, 1566
        return (f'<hp:rect id="{_rid()}" zOrder="30" numberingType="PICTURE" textWrap="TOP_AND_BOTTOM" textFlow="BOTH_SIDES" lock="0" dropcapstyle="None" href="" groupLevel="0" instid="{_rid()}" ratio="0">'
                f'<hp:offset x="0" y="0"/><hp:orgSz width="{w}" height="{h}"/><hp:curSz width="{w}" height="{h}"/><hp:flip horizontal="0" vertical="0"/>'
                f'<hp:rotationInfo angle="0" centerX="{w // 2}" centerY="{h // 2}" rotateimage="1"/><hp:renderingInfo><hc:transMatrix e1="1" e2="0" e3="0" e4="0" e5="1" e6="0"/><hc:scaMatrix e1="1" e2="0" e3="0" e4="0" e5="1" e6="0"/><hc:rotMatrix e1="1" e2="0" e3="0" e4="0" e5="1" e6="0"/></hp:renderingInfo>'
                '<hp:lineShape color="#000000" width="33" style="SOLID" endCap="FLAT" headStyle="NORMAL" tailStyle="NORMAL" headfill="1" tailfill="1" headSz="MEDIUM_MEDIUM" tailSz="MEDIUM_MEDIUM" outlineStyle="NORMAL" alpha="0"/>'
                '<hc:fillBrush><hc:winBrush faceColor="#F9F7F1" hatchColor="#000000" alpha="0"/></hc:fillBrush><hp:shadow type="NONE" color="#B2B2B2" offsetX="0" offsetY="0" alpha="0"/>'
                f'<hp:drawText lastWidth="{w}" name="" editable="0"><hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" vertAlign="CENTER" linkListIDRef="0" linkListNextIDRef="0" textWidth="0" textHeight="0" hasTextRef="0" hasNumRef="0">'
                f'<hp:p id="0" paraPrIDRef="{pp}" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0"><hp:run charPrIDRef="{cp}"><hp:t>{esc(label)}</hp:t></hp:run></hp:p></hp:subList>'
                '<hp:textMargin left="141" right="141" top="141" bottom="141"/></hp:drawText>'
                f'<hc:pt0 x="0" y="0"/><hc:pt1 x="{w}" y="0"/><hc:pt2 x="{w}" y="{h}"/><hc:pt3 x="0" y="{h}"/><hp:sz width="{w}" widthRelTo="ABSOLUTE" height="{h}" heightRelTo="ABSOLUTE" protect="0"/>'
                '<hp:pos treatAsChar="1" affectLSpacing="0" flowWithText="0" allowOverlap="1" holdAnchorAndSO="0" vertRelTo="PARA" horzRelTo="PARA" vertAlign="TOP" horzAlign="LEFT" vertOffset="0" horzOffset="0"/>'
                '<hp:outMargin left="0" right="0" top="0" bottom="0"/><hp:shapeComment>사각형입니다.</hp:shapeComment></hp:rect>')

    def gap(self, a, b):
        pt = self.box_gap_pt(b) if a == "box" else self.gap_pt(a, b)
        if pt is None: return None
        L_ = self.level("p" if self.R.get("style") == "para" else "l1")
        return self.p(self.para_pr("JUSTIFY", L_["line"]), [(self.char(L_["font"], pt), "")])

    def caption(self, text):
        return self.p(self.para_pr("CENTER", 160, keep=True), [(self.char("맑은 고딕", 13.0, -2, True), f"< {text.strip('<> ')} >")])

    # ── 표 ──
    def table(self, rows, head=None):
        rows = [[PUA.sub(lambda m: PUA_MAP.get(m.group(0), ""), str(c)) for c in r] for r in rows]
        if head is None: head = len(rows) > 1 and all(len(c.replace("\n", "")) <= 12 for c in rows[0]) and not all(len(r[0]) <= 8 and len(r) == 2 and len(r[1]) > 20 for r in rows)
        label_col = (not head) and max(len(r) for r in rows) >= 2 and all(len(r[0].replace("\n", "")) <= 8 for r in rows)
        ncol = max(len(r) for r in rows); total = self.text_w - 200
        lens = [max(len(str(r[c])) if c < len(r) else 0 for r in rows) + 3 for c in range(ncol)]
        word = [max([len(t) for r in rows if c < len(r) for t in re.split(r"\s+", str(r[c])) if t] or [2]) for c in range(ncol)]
        mins = [min(total * 0.45, word[c] * 1100 + 1300) for c in range(ncol)]  # 어절이 칸 안에서 갈리지 않게
        ws = [max(mins[c], total * lens[c] / sum(lens)) for c in range(ncol)]
        extra = sum(ws) - total
        if extra > 0:  # 넘치면 최소 폭을 넘는 열에서만 덜어냄
            room = [ws[c] - mins[c] for c in range(ncol)]
            ws = [ws[c] - extra * room[c] / max(1, sum(room)) for c in range(ncol)]
        ws = [int(w) for w in ws]
        th = self.TH; hb, bb = self.border(th.get("fill")), self.border(None)
        tpt = float(th.get("pt") or 11.0); ppc = int(tpt * 100)   # 글자 한 칸 폭(HWPUNIT) 추정
        trs, H = [], 0
        for ri, r in enumerate(rows):
            tcs, rh = [], 0
            for ci in range(ncol):
                v = str(r[ci]) if ci < len(r) else ""
                is_head = (head and ri == 0) or (label_col and ci == 0)
                num = bool(re.fullmatch(r"[\d,.%△▲▽+\-~() ]+[^\s]{0,3}", v.strip())) and any(c.isdigit() for c in v)
                align = "CENTER" if (is_head or len(v) <= 12 or ci == 0) else ("RIGHT" if num else "JUSTIFY")
                cp = self.char(th.get("font") or "맑은 고딕", tpt if is_head else min(tpt, 11.0), -2, is_head and th.get("bold", True))
                lines = v.split("\n") or [""]
                ps = "".join(self.p(self.para_pr(align, 130), [(cp, ln)]) for ln in lines)
                cw = ws[ci]; per = max(1, int((cw - 1020) / ppc))
                nl = sum(max(1, -(-len(ln) // per)) for ln in lines); h = int(nl * ppc * 1.3 + 400 + 282)
                rh = max(rh, h)
                tcs.append((ps, cw, hb if is_head else bb, ci))
            trs.append((tcs, rh)); H += rh
        out = []
        for ri, (tcs, rh) in enumerate(trs):
            cells = "".join(
                f'<hp:tc name="" header="{1 if (head and ri == 0) else 0}" hasMargin="0" protect="0" editable="0" dirty="0" borderFillIDRef="{bf}">'
                f'<hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" vertAlign="CENTER" linkListIDRef="0" linkListNextIDRef="0" textWidth="0" textHeight="0" hasTextRef="0" hasNumRef="0">{ps}</hp:subList>'
                f'<hp:cellAddr colAddr="{ci}" rowAddr="{ri}"/><hp:cellSpan colSpan="1" rowSpan="1"/><hp:cellSz width="{cw}" height="{rh}"/>'
                f'<hp:cellMargin left="510" right="510" top="141" bottom="141"/></hp:tc>' for ps, cw, bf, ci in tcs)
            out.append(f"<hp:tr>{cells}</hp:tr>")
        tbl = (f'<hp:tbl id="{_rid()}" zOrder="1" numberingType="TABLE" textWrap="TOP_AND_BOTTOM" textFlow="BOTH_SIDES" lock="0" dropcapstyle="None" pageBreak="CELL" repeatHeader="1" '
               f'rowCnt="{len(rows)}" colCnt="{ncol}" cellSpacing="0" borderFillIDRef="{bb}" noAdjust="0"><hp:sz width="{sum(ws)}" widthRelTo="ABSOLUTE" height="{H}" heightRelTo="ABSOLUTE" protect="0"/>'
               '<hp:pos treatAsChar="1" affectLSpacing="0" flowWithText="1" allowOverlap="0" holdAnchorAndSO="0" vertRelTo="PARA" horzRelTo="COLUMN" vertAlign="TOP" horzAlign="CENTER" vertOffset="0" horzOffset="0"/>'
               '<hp:outMargin left="0" right="0" top="0" bottom="0"/><hp:inMargin left="510" right="510" top="141" bottom="141"/>' + "".join(out) + "</hp:tbl>")
        return f'<hp:p id="0" paraPrIDRef="{self.para_pr("CENTER", 100)}" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0"><hp:run charPrIDRef="{self.char("맑은 고딕", 11.0)}">{tbl}<hp:t/></hp:run></hp:p>'

    def box(self, lines):
        """강조 상자: 연한 음영 1칸 표, 본문 글꼴."""
        L_ = self.level("p" if self.R.get("style") == "para" else "l1")
        bf = self.border("#F2F2F2"); cp = self.char(L_["font"], L_["pt"] - 1, -2)
        ps = "".join(self.p(self.para_pr("JUSTIFY", 150), [(cp, ln)]) for ln in lines)
        h = int(len(lines) * (L_["pt"] - 1) * 150 + 1200)
        tbl = (f'<hp:tbl id="{_rid()}" zOrder="1" numberingType="TABLE" textWrap="TOP_AND_BOTTOM" textFlow="BOTH_SIDES" lock="0" dropcapstyle="None" pageBreak="CELL" repeatHeader="0" rowCnt="1" colCnt="1" cellSpacing="0" borderFillIDRef="{bf}" noAdjust="0">'
               f'<hp:sz width="{self.text_w - 200}" widthRelTo="ABSOLUTE" height="{h}" heightRelTo="ABSOLUTE" protect="0"/><hp:pos treatAsChar="1" affectLSpacing="0" flowWithText="1" allowOverlap="0" holdAnchorAndSO="0" vertRelTo="PARA" horzRelTo="COLUMN" vertAlign="TOP" horzAlign="CENTER" vertOffset="0" horzOffset="0"/>'
               '<hp:outMargin left="0" right="0" top="0" bottom="0"/><hp:inMargin left="850" right="850" top="566" bottom="566"/>'
               f'<hp:tr><hp:tc name="" header="0" hasMargin="1" protect="0" editable="0" dirty="0" borderFillIDRef="{bf}"><hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" vertAlign="CENTER" linkListIDRef="0" linkListNextIDRef="0" textWidth="0" textHeight="0" hasTextRef="0" hasNumRef="0">{ps}</hp:subList>'
               f'<hp:cellAddr colAddr="0" rowAddr="0"/><hp:cellSpan colSpan="1" rowSpan="1"/><hp:cellSz width="{self.text_w - 200}" height="{h}"/><hp:cellMargin left="850" right="850" top="566" bottom="566"/></hp:tc></hp:tr></hp:tbl>')
        return f'<hp:p id="0" paraPrIDRef="{self.para_pr("CENTER", 100)}" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0"><hp:run charPrIDRef="{cp}">{tbl}<hp:t/></hp:run></hp:p>'

    # ── 본문 조립 ──
    LVMAP = {"l1": "l1", "l2": "l2", "l3": "l3", "note": "note", "ref": "ref", "p": "p", "plain": "p", "h": "l1",
             "caption": "caption", "table": "table", "box": "table", "image": "image"}
    LVMAP["h"] = "h"

    def blocks(self, blocks, out, first_page_break=False):
        prev = None
        for b in blocks:
            t = b["type"]; lv = self.LVMAP.get(t, "p")
            self._after_table = prev in ("table",) and lv in ("note", "ref")
            if prev is not None:
                g = None if lv == "caption" or prev == "caption" or self._after_table else self.gap(prev, lv)
                if g: out.append(g)
            if t in ("l1", "l2", "l3", "note", "ref", "p", "plain"): out.append(self.item(self.LVMAP[t], b["text"]))
            elif t == "h": out.append(self.heading(b["text"]))
            elif t == "caption": out.append(self.caption(b["text"]))
            elif t == "table": out.append(self.table(b["rows"]))
            elif t == "box": out.append(self.box(b["lines"]))
            elif t == "appx_h":
                out.append(self.appx_head(b["text"], b.get("heading", "")))
            elif t == "image":
                bid, w, h = self.add_image(b["path"])
                out.append(self.p_raw(self.para_pr("CENTER", 100), self.char("맑은 고딕", 10.0), self.picture(bid, w, h, min(b.get("width_mm", 150) * HU_MM, self.text_w - 200))))
            prev = "box" if t == "box" else lv

    def heading(self, text):
        """소제목: 본문 1계층 글꼴 +1pt 굵게, 다음 문단과 같은 쪽."""
        L_ = self.level("l1" if self.R.get("style") == "box" else "p")
        hc = self.char(L_["font"], L_["pt"] + 1, -2, True)
        return self.p(self.para_pr("JUSTIFY", L_["line"], keep=True), [(hc, text.strip("* "))])

    # ── 그림 ──
    def add_image(self, path):
        b = Path(path).expanduser().read_bytes(); ext = Path(path).suffix.lower().lstrip(".").replace("jpeg", "jpg")
        bid = f"image{len(self.images) + 1}"; self.images.append((bid, ext, b))
        w, h = _img_size(b); return bid, w, h

    def picture(self, bid, w_px, h_px, cw, ch=None):
        """글자처럼 취급하는 그림. cw·ch = 표시 크기(HWPUNIT). ch를 주면 비율 유지하며 cw×ch 안에 맞춤."""
        ow, oh = w_px * 75, h_px * 75
        cw = int(cw); r = h_px / max(1, w_px)
        if ch is not None and cw * r > ch: cw = int(ch / r)
        ch = int(cw * r)
        return (f'<hp:pic id="{_rid()}" zOrder="5" numberingType="PICTURE" textWrap="TOP_AND_BOTTOM" textFlow="BOTH_SIDES" lock="0" dropcapstyle="None" href="" groupLevel="0" instid="{_rid()}" reverse="0">'
                f'<hp:offset x="0" y="0"/><hp:orgSz width="{ow}" height="{oh}"/><hp:curSz width="{cw}" height="{ch}"/><hp:flip horizontal="0" vertical="0"/>'
                f'<hp:rotationInfo angle="0" centerX="{cw // 2}" centerY="{ch // 2}" rotateimage="1"/><hp:renderingInfo><hc:transMatrix e1="1" e2="0" e3="0" e4="0" e5="1" e6="0"/>'
                f'<hc:scaMatrix e1="{cw / ow:.6f}" e2="0" e3="0" e4="0" e5="{ch / oh:.6f}" e6="0"/><hc:rotMatrix e1="1" e2="0" e3="0" e4="0" e5="1" e6="0"/></hp:renderingInfo>'
                f'<hc:img binaryItemIDRef="{bid}" bright="0" contrast="0" effect="REAL_PIC" alpha="0"/><hp:imgRect><hc:pt0 x="0" y="0"/><hc:pt1 x="{ow}" y="0"/><hc:pt2 x="{ow}" y="{oh}"/><hc:pt3 x="0" y="{oh}"/></hp:imgRect>'
                f'<hp:imgClip left="0" right="{ow}" top="0" bottom="{oh}"/><hp:inMargin left="0" right="0" top="0" bottom="0"/><hp:imgDim dimwidth="{ow}" dimheight="{oh}"/><hp:effects/>'
                f'<hp:sz width="{cw}" widthRelTo="ABSOLUTE" height="{ch}" heightRelTo="ABSOLUTE" protect="0"/><hp:pos treatAsChar="1" affectLSpacing="0" flowWithText="1" allowOverlap="0" holdAnchorAndSO="0" vertRelTo="PARA" horzRelTo="COLUMN" vertAlign="TOP" horzAlign="CENTER" vertOffset="0" horzOffset="0"/>'
                f'<hp:outMargin left="0" right="0" top="0" bottom="0"/><hp:shapeComment>그림입니다.</hp:shapeComment></hp:pic>')

    def p_raw(self, pid, cid, inner, page_break=False):
        return (f'<hp:p id="0" paraPrIDRef="{pid}" styleIDRef="0" pageBreak="{int(page_break)}" columnBreak="0" merged="0">'
                f'<hp:run charPrIDRef="{cid}">{inner}<hp:t/></hp:run></hp:p>')

    # ── 머리·담당 표 공통 ──
    def ch(self, spec, **kw):
        s = dict(DEFAULT_CHAR); s.update({k: v for k, v in (spec or {}).items() if v is not None}); s.update(kw)
        return self.char(s["font"] or "바탕", float(s["pt"]), int(s.get("spacing") or 0), bool(s.get("bold")), s.get("color") or "#000000", int(s.get("ratio") or 100))

    def cell(self, col, row, w, h, paras, bf, colspan=1, rowspan=1, margin=(141, 141, 141, 141)):
        l, r, t, b = margin
        return (f'<hp:tc name="" header="0" hasMargin="1" protect="0" editable="0" dirty="0" borderFillIDRef="{bf}">'
                f'<hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" vertAlign="CENTER" linkListIDRef="0" linkListNextIDRef="0" textWidth="0" textHeight="0" hasTextRef="0" hasNumRef="0">{paras}</hp:subList>'
                f'<hp:cellAddr colAddr="{col}" rowAddr="{row}"/><hp:cellSpan colSpan="{colspan}" rowSpan="{rowspan}"/><hp:cellSz width="{int(w)}" height="{int(h)}"/>'
                f'<hp:cellMargin left="{l}" right="{r}" top="{t}" bottom="{b}"/></hp:tc>')

    def tbl_para(self, rows, nrow, ncol, width, height, bf, align="CENTER"):
        tbl = (f'<hp:tbl id="{_rid()}" zOrder="1" numberingType="TABLE" textWrap="TOP_AND_BOTTOM" textFlow="BOTH_SIDES" lock="0" dropcapstyle="None" pageBreak="CELL" repeatHeader="0" '
               f'rowCnt="{nrow}" colCnt="{ncol}" cellSpacing="0" borderFillIDRef="{bf}" noAdjust="0"><hp:sz width="{int(width)}" widthRelTo="ABSOLUTE" height="{int(height)}" heightRelTo="ABSOLUTE" protect="0"/>'
               f'<hp:pos treatAsChar="1" affectLSpacing="0" flowWithText="1" allowOverlap="0" holdAnchorAndSO="0" vertRelTo="PARA" horzRelTo="COLUMN" vertAlign="TOP" horzAlign="{align}" vertOffset="0" horzOffset="0"/>'
               '<hp:outMargin left="0" right="0" top="0" bottom="0"/><hp:inMargin left="141" right="141" top="141" bottom="141"/>'
               + "".join(f"<hp:tr>{r}</hp:tr>" for r in rows) + "</hp:tbl>")
        return self.p_raw(self.para_pr(align, 100), self.char("바탕", 10.0), tbl)

    def fit_widths(self, ws):
        tot = sum(ws); lim = self.text_w - 200
        return [int(w * lim / tot) for w in ws] if tot > lim else [int(w) for w in ws]

    def title_gap(self):
        """제목 → 첫 문단 빈 줄: 본문 첫 계층(□) 크기 한 줄(최소 12pt, 줄 간격 160%) — 6~12pt 빈 줄은 제목에 붙어 보임."""
        L_ = self.level("p" if self.R.get("style") == "para" else "l1")
        return self.p(self.para_pr("JUSTIFY", 160), [(self.char("바탕", max(12.0, float(L_["pt"]))), "")])

    def spacer(self, pt=6.0):
        return self.p(self.para_pr("JUSTIFY", 100), [(self.char("바탕", pt), "")])

    # ── 표지(로고 자리·'보도자료') ──
    def cover(self, doc):
        c = self.L.get("cover") or {"widths": [13352, 19012, 15333], "height": 4178, "label_col": 1, "logo_col": 0, "label": "보도자료",
                                    "label_char": {"font": "HY헤드라인M", "pt": 20.0, "bold": False}}
        ws = self.fit_widths(c["widths"]); h = c.get("height", 4178); none = self.border(None, "NONE")
        label = doc.get("kind") or c.get("label") or "보도자료"
        tcs = []
        for k, w in enumerate(ws):
            if k == c.get("label_col"):
                cp = self.ch(c.get("label_char")); paras = self.p(self.para_pr("CENTER", 100), [(cp, label)])
                bf = self.border(c.get("label_fill"), "NONE") if c.get("label_fill") else none
            elif k == c.get("logo_col"):
                bf = none
                if self.logo_path:   # 사용자가 지정한 기관 로고: 칸 크기 안에 비율 유지
                    bid, pw, ph = self.add_image(self.logo_path)
                    paras = self.p_raw(self.para_pr("CENTER", 100), self.char("바탕", 10.0), self.picture(bid, pw, ph, w - 400, h - 400))
                else:   # 로고 없음: 같은 크기의 자리표시 칸(얇은 회색 테두리 + 회색 '기관 로고') — 한글에서 글을 지우고 그림을 넣으면 됨
                    bf = self.border(None, "SOLID", "0.12 mm", "#A6A6A6")
                    paras = self.p(self.para_pr("CENTER", 100), [(self.char("맑은 고딕", 10.0, color="#A6A6A6"), "기관 로고")])
            else:
                bf = none; paras = self.p(self.para_pr("CENTER", 100), [(self.char("바탕", 10.0), "")])
            tcs.append(self.cell(k, 0, w, h, paras, bf))
        return self.tbl_para(["".join(tcs)], 1, len(ws), sum(ws), h, none)

    # ── 보도시점·배포 ──
    def release(self, doc):
        rel = doc.get("release") or ""; dist = doc.get("distribute") or doc.get("배포") or ""
        r = self.L.get("release")
        if not r:
            lab = (self.L.get("contact") or {}).get("label_char") or DEFAULT_CHAR
            r = {"cells": [{"role": "release_label", "label": "보도시점", "w": 5670, "h": 1700, "char": lab},
                           {"role": "release", "w": 12755, "h": 1700, "char": lab},
                           {"role": "distribute_label", "label": "배포", "w": 3401, "h": 1700, "char": lab},
                           {"role": "distribute", "w": 12755, "h": 1700, "char": lab}]}
        cs = [dict(c) for c in r["cells"]]; h = max(c.get("h", 1700) for c in cs)
        txt_of = lambda c: {"release": rel, "distribute": dist, "release_inline": f'{c.get("label", "보도시점")} : {rel}'}.get(c["role"], c.get("label", ""))
        ws = self.release_widths(cs, txt_of)
        tcs = []
        for k, (c, w) in enumerate(zip(cs, ws)):
            role = c["role"]
            txt = {"release": rel, "distribute": dist, "release_inline": f'{c.get("label", "보도시점")} : {rel}'.rstrip(" :") + (" " if not rel else ""),
                   "release_label": c.get("label", ""), "distribute_label": c.get("label", ""), "label": c.get("label", "")}.get(role, "")
            if role == "label" and txt and txt in rel: txt = ""   # 보도시점 값에 이미 들어간 말(예: 조간) 중복 방지
            bf = self.border(c.get("fill"), c.get("line") or "NONE")
            paras = self.p(self.para_pr(c.get("align") or "CENTER", 100), [(self.ch(c.get("char")), txt)])
            tcs.append(self.cell(k, 0, w, h, paras, bf))
        return self.tbl_para(["".join(tcs)], 1, len(cs), sum(ws), h, self.border(None, "NONE"))

    def release_widths(self, cs, txt_of):
        """날짜·시점 칸이 '2026. 1. 5.(월) 조간' 길이를 한 줄에 담도록: 필요 폭 = 추정 글자 폭×1.15 + 칸 여백.
        모자라면 ① 라벨·여유 칸에서 덜어오고 ② 표 폭을 본문 폭까지 늘리고 ③ 그래도 모자라면 그 칸 자간·장평을 줄인다."""
        def need(c, sp=None, ra=None):
            ch = dict(DEFAULT_CHAR, **{k: v for k, v in (c.get("char") or {}).items() if v is not None})
            w = WIDTHS.get(ch["font"]) or F.W
            return F.width(txt_of(c), float(ch["pt"]), int(ch.get("spacing") or 0) if sp is None else sp, int(ch.get("ratio") or 100) if ra is None else ra, w) * 1.15 + 600
        ws = [float(c["w"]) for c in cs]; nd = [need(c) for c in cs]
        lim = self.text_w - 200
        short = lambda: sum(max(0, nd[k] - ws[k]) for k in range(len(cs)))
        if short() > 0:
            room = [max(0, ws[k] - nd[k]) for k in range(len(cs))]
            take = min(short(), sum(room))
            if take > 0:
                for k in range(len(cs)): ws[k] -= take * room[k] / sum(room)
                gain = [max(0, nd[k] - ws[k]) for k in range(len(cs))]
                for k in range(len(cs)): ws[k] += take * gain[k] / max(1e-9, sum(gain))
            if short() > 0 and sum(ws) < lim:   # 표 폭을 본문 폭까지
                add = min(short(), lim - sum(ws)); gain = [max(0, nd[k] - ws[k]) for k in range(len(cs))]
                for k in range(len(cs)): ws[k] += add * gain[k] / sum(gain)
        ws = self.fit_widths(ws)
        for k, c in enumerate(cs):   # 마지막 수단: 자간 → 장평
            if need(c) <= ws[k] + 1: continue
            ch = dict(c.get("char") or {}); sp0 = int(ch.get("spacing") or 0)
            for sp, ra in [(s, 100) for s in range(sp0 - 1, -11, -1)] + [(-10, r) for r in range(95, 79, -5)]:
                if need(c, sp, ra) <= ws[k]: break
            ch.update(spacing=sp, ratio=ra); c["char"] = ch
        return ws

    # ── 제목·부제 ──
    def fit_spacing(self, text, spec, width):
        spec = dict(DEFAULT_CHAR, **{k: v for k, v in (spec or {}).items() if v is not None})
        w = WIDTHS.get(spec["font"]) or WIDTHS.get("바탕")
        for sp in range(int(spec.get("spacing") or 0), -16, -1):
            if F.width(text, float(spec["pt"]), sp, int(spec.get("ratio") or 100), w) <= width: return sp
        return int(spec.get("spacing") or 0)

    def fit_title(self, text, spec, width):
        """제목 맞춤: ① 자간을 규칙 하한까지 ② 글자 크기를 규칙 크기의 80%까지 1pt씩 ③ 어절 경계에서 두 줄.
        반환 (spec, 줄 목록). 글자 폭은 widths.json 추정값에 12% 여유를 둔다(한글 실제 글꼴 대체 대비)."""
        spec = dict(DEFAULT_CHAR, **{k: v for k, v in (spec or {}).items() if v is not None})
        w = WIDTHS.get(spec["font"]) or WIDTHS.get("바탕"); ra = int(spec.get("ratio") or 100)
        base_sp, pt0 = int(spec.get("spacing") or 0), float(spec["pt"])
        lo = min(base_sp, int(self.R.get("spacing_min", self.R["_base"].get("spacing_min", -8))))
        lim = width * 0.88
        fits = lambda t, pt, sp: F.width(t.strip(), pt, sp, ra, w) <= lim
        pts = [pt0] + [p for p in range(int(pt0) - 1, 0, -1) if p >= pt0 * 0.8 - 1e-9]
        for pt in pts:
            for sp in range(base_sp, lo - 1, -1):
                if fits(text, pt, sp): return dict(spec, pt=float(pt), spacing=sp), [text]
        words = text.split(" ")
        cands = [(" ".join(words[:k]), " ".join(words[k:])) for k in range(1, len(words))]
        cands.sort(key=lambda ab: max(F.width(ab[0], pt0, base_sp, ra, w), F.width(ab[1], pt0, base_sp, ra, w)))
        for pt in pts:
            for sp in range(base_sp, lo - 1, -1):
                for a, b in cands[:1]:
                    if fits(a, pt, sp) and fits(b, pt, sp): return dict(spec, pt=float(pt), spacing=sp), [a, b]
        return dict(spec, pt=float(pts[-1]), spacing=lo), ([*cands[0]] if cands else [text])

    def title(self, doc):
        t = self.L.get("title") or {"para": True, "char": {"font": "HY헤드라인M", "pt": 22.0, "bold": False}, "align": "CENTER"}
        subs = [f"- {s} -" for s in doc.get("subtitles", [])]
        if t.get("para"):
            spec, ls = self.fit_title(doc["title"], t["char"], self.text_w)
            out = [self.p(self.para_pr(t.get("align") or "CENTER", 130), [(self.ch(spec), ln)]) for ln in ls]
            out += [self.p(self.para_pr("CENTER", 130), [(self.ch(t["char"], pt=min(16.0, max(11.0, float(t["char"]["pt"]) - 6)), bold=False), s)]) for s in subs]
            return out
        width = min(t.get("width", self.text_w), self.text_w - 200); rows = []; H = 0
        for k, row in enumerate(t["rows"]):
            if row["role"] == "subtitle" and not subs: continue
            lines = [doc["title"]] if row["role"] == "title" else subs
            spec = dict(row.get("char") or {})
            if row["role"] == "title": spec, lines = self.fit_title(doc["title"], spec, width - 1700)
            cp = self.ch(spec)
            paras = "".join(self.p(self.para_pr(row.get("align") or "CENTER", 130), [(cp, ln)]) for ln in lines)
            b = row.get("border") or {}
            bf = self.border(row.get("fill"), b.get("line") or "SOLID", b.get("width") or "0.12 mm")
            h = max(row.get("h", 2000), int(len(lines) * float(spec.get("pt", 12)) * 130 + 1000))
            rows.append(self.cell(0, len(rows), width, h, paras, bf, margin=(850, 850, 566, 566))); H += h
        if subs and not any(r["role"] == "subtitle" for r in t["rows"]):   # 부제 칸이 없는 기관: 제목 표 아래 문단
            return [self.tbl_para(rows, len(rows), 1, width, H, self.border(None, "NONE"))] + \
                   [self.p(self.para_pr("CENTER", 130), [(self.ch(t["rows"][0].get("char"), pt=min(16.0, max(11.0, float((t["rows"][0].get("char") or {}).get("pt", 18)) - 6)), bold=False), s)]) for s in subs]
        return [self.tbl_para(rows, len(rows), 1, width, H, self.border(None, "NONE"))]

    # ── 담당 표 ──
    def contact(self, doc):
        c = doc.get("contact") or {}
        if not c.get("people") and self.placeholder_contact: c = PLACEHOLDER_CONTACT
        people = [(list(p) + ["", "", "", ""])[:4] if len(p) >= 4 else ["", *([""] * (3 - len(p))), *p] for p in c.get("people", [])]
        if not people: people = [["담당자", "", "", ""]]
        L_ = self.L.get("contact") or {"widths": [6236, 15167, 6081, 5605, 5605, 9003], "row_h": 1800}
        # 칸 높이: 기관값이 글자 크기에 비해 과도하면(실물은 두 줄 이름 등) 글자 크기 기준 한 줄 + 여백으로 줄임
        cpt = float((L_.get("value_char") or L_.get("label_char") or DEFAULT_CHAR).get("pt") or 10.0)
        h = int(min(max(L_.get("row_h", 1800), 1500), cpt * 100 * 1.6 + 700))
        n = len(people)
        ws = self.fit_widths(L_["widths"])
        line, lw = L_.get("line") or "SOLID", L_.get("line_width") or "0.12 mm"
        if line == "NONE": line = "SOLID"
        lab_bf = self.border(L_.get("label_fill"), line, lw); val_bf = self.border(L_.get("value_fill"), line, lw)
        lab_cp = self.ch(L_.get("label_char"), bold=True); val_cp = self.ch(L_.get("value_char") or L_.get("label_char"), bold=False)
        para = lambda cp, t: self.p(self.para_pr("CENTER", 100), [(cp, t)])
        rows = []
        for i, (kind, title, name, phone) in enumerate(people):
            tcs = ""
            if i == 0:
                tcs += self.cell(0, 0, ws[0], h * n, para(lab_cp, (L_.get("labels") or {}).get("dept", "담당 부서")), lab_bf, rowspan=n)
                tcs += self.cell(1, 0, ws[1], h * n, para(val_cp, c.get("dept", "")), val_bf, rowspan=n)
            tcs += self.cell(2, i, ws[2], h, para(lab_cp, kind), lab_bf)
            for k, v in ((3, title), (4, name), (5, phone)):
                tcs += self.cell(k, i, ws[k], h, para(val_cp, v), val_bf)
            rows.append(tcs)
        return self.tbl_para(rows, n, 6, sum(ws), h * n, self.border(None, "NONE"))

    # ── 조립 ──
    def build(self, doc, dst):
        out = [self.cover(doc), self.spacer(), self.release(doc), self.spacer(8.0)] + self.title(doc) + [self.title_gap()]
        sec = B.sec_pr(self.L.get("page", {}))
        out[0] = re.sub(r"(<hp:p\b[^>]*>)", lambda m: m.group(1) + f'<hp:run charPrIDRef="0">{sec}</hp:run>', out[0], count=1)
        body = doc.get("body", [])
        if self.R.get("style") == "para":  # 문단식 기관: □ㅇ 원고는 문단으로, 하위는 ○로
            conv = {"l1": "p", "l2": "l2", "l3": "l3"}
            body = [dict(b, type=conv.get(b["type"], b["type"])) for b in body]
        self.blocks(body, out)
        out.append(self.spacer(10.0))
        out.append(self.contact(doc))
        if self.slogan_path:   # 슬로건 그림(선택): 담당 표 아래 가운데
            bid, pw, ph = self.add_image(self.slogan_path)
            out += [self.spacer(10.0), self.p_raw(self.para_pr("CENTER", 100), self.char("바탕", 10.0), self.picture(bid, pw, ph, (self.text_w - 200) * 0.9, 4000))]
        for k, a in enumerate(doc.get("appendix", []), 1):   # 참고·붙임: 담당 표 다음 새 쪽
            self.blocks([{"type": "appx_h", "text": a.get("title") or f"참고 {k}", "heading": a.get("heading", "")}] + a.get("body", []), out)
        out = [o for o in out if o]
        section = B.section_xml(out)
        prv = "\n".join(t for t in (re.sub(r"<[^>]+>", "", x.replace("<hp:nbSpace/>", " ")) for x in re.findall(r"<hp:t>(.*?)</hp:t>", section)) if t.strip())
        B.save(dst, self.header, section, self.images, html.unescape(prv)[:1000])
        return dst


def compose(org, doc, dst, override=None, logo_path=None, slogan_path=None, placeholder_contact=False):
    c = Composer(org, logo_path=logo_path, slogan_path=slogan_path, placeholder_contact=placeholder_contact); c.override = override or {}
    c.build(doc, dst); return c
