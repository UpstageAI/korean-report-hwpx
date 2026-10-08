"""HWPX 읽기·분석 기본기 (자체 엔진). 작성 Mia(윤승미)
HWPX = zip(mimetype, Contents/header.xml(글자·문단 모양), Contents/section0.xml(본문), BinData/*).
본문은 최상위 문단(<hp:p>)의 나열이고, 문단은 paraPrIDRef(문단 모양) + 글자 조각(<hp:run charPrIDRef>)들로 이뤄진다."""
import html, re, zipfile
from pathlib import Path

T_RE = re.compile(r"<hp:t\b[^>]*>(.*?)</hp:t>|<hp:t\s*/>", re.S)


class Hwpx:
    def __init__(self, path):
        self.path = Path(path)
        with zipfile.ZipFile(self.path) as z:
            self.names = z.namelist()
            self.infos = {n: z.getinfo(n) for n in self.names}
            self.data = {n: z.read(n) for n in self.names}
        self.header = self.data["Contents/header.xml"].decode("utf-8")
        self.section = self.data["Contents/section0.xml"].decode("utf-8")
        self._fonts = {lang: dict(re.findall(r'<hh:font id="(\d+)" face="([^"]+)"', blk))
                       for lang, blk in re.findall(r'<hh:fontface lang="(\w+)".*?>(.*?)</hh:fontface>', self.header, re.S)}

    # ── 본문 구조 ──
    def paragraphs(self):
        """최상위 문단 [(start, end, xml)] — 표 안 문단은 포함하지 않음."""
        x, out, depth, start = self.section, [], 0, None
        for m in re.finditer(r"<hp:p\b[^>]*?(/?)>|</hp:p>", x):
            t = m.group(0)
            if t.startswith("</"):
                depth -= 1
                if depth == 0: out.append((start, m.end(), x[start:m.end()]))
            elif m.group(1) == "/":
                if depth == 0: out.append((m.start(), m.end(), t))
            else:
                if depth == 0: start = m.start()
                depth += 1
        return out

    @staticmethod
    def text(p, tables=False):
        body = p if tables else re.sub(r"<hp:tbl\b.*?</hp:tbl>", "", p, flags=re.S)
        return "".join(html.unescape(re.sub(r"<[^>]+>", "", (m.group(1) or "").replace("<hp:nbSpace/>", " "))) for m in T_RE.finditer(body))

    # ── 모양 ──
    def char(self, cid):
        m = re.search(r'<hh:charPr id="%s"[^>]*>.*?</hh:charPr>' % cid, self.header, re.S)
        if not m: return {}
        s = m.group(0)
        g = lambda pat, d=None: (re.search(pat, s) or [None, d])[1]
        return {"pt": int(g(r'height="(\d+)"', 1000)) / 100, "font": self._fonts.get("HANGUL", {}).get(g(r'<hh:fontRef hangul="(\d+)"', "0")),
                "spacing": int(g(r'<hh:spacing hangul="(-?\d+)"', 0)), "ratio": int(g(r'<hh:ratio hangul="(\d+)"', 100)),
                "bold": "<hh:bold" in s, "color": g(r'textColor="([^"]+)"')}

    def para(self, pid):
        m = re.search(r'<hh:paraPr id="%s"[^>]*>.*?</hh:paraPr>' % pid, self.header, re.S)
        if not m: return {}
        s = m.group(0)
        g = lambda pat, d=None: (re.search(pat, s) or [None, d])[1]
        return {"align": g(r'horizontal="(\w+)"'), "line": int(g(r'<hh:lineSpacing type="\w+" value="(\d+)"', 160)),
                "indent": int(g(r'<hc:intent value="(-?\d+)"', 0)), "left": int(g(r'<hc:left value="(-?\d+)"', 0)),
                "prev": int(g(r'<hc:prev value="(-?\d+)"', 0)), "next": int(g(r'<hc:next value="(-?\d+)"', 0))}

    @staticmethod
    def ids(p):
        pp = re.search(r'paraPrIDRef="(\d+)"', p).group(1)
        runs = re.findall(r'<hp:run charPrIDRef="(\d+)"[^>]*>(.*?)</hp:run>', p, re.S)
        # 글자가 가장 많은 조각의 글자 모양 = 대표
        best = max(runs, key=lambda r: len(Hwpx.text(r[1])), default=(None, ""))
        return pp, best[0]

    # ── 저장 ──
    def save(self, dst, section=None, header=None, extra=None):
        data = dict(self.data)
        if section is not None: data["Contents/section0.xml"] = section.encode("utf-8")
        if header is not None: data["Contents/header.xml"] = header.encode("utf-8")
        data.pop("Preview/PrvImage.png", None)
        data.update(extra or {})
        names = [n for n in self.names if n in data] + [n for n in (extra or {}) if n not in self.names]
        with zipfile.ZipFile(dst, "w") as z:
            for n in names:
                info = self.infos.get(n) or zipfile.ZipInfo(n)
                z.writestr(info, data[n], compress_type=zipfile.ZIP_STORED if n == "mimetype" else zipfile.ZIP_DEFLATED)


def balanced(x, tag):
    """중첩을 고려해 최상위 <hp:tag> 요소들만 [(시작, 끝, xml)] 로."""
    out, depth, start = [], 0, None
    for m in re.finditer(r"<hp:%s\b[^>]*?(/?)>|</hp:%s>" % (tag, tag), x):
        if m.group(0).startswith("</"):
            depth -= 1
            if depth == 0: out.append((start, m.end(), x[start:m.end()]))
        elif m.group(1) == "/":
            if depth == 0: out.append((m.start(), m.end(), m.group(0)))
        else:
            if depth == 0: start = m.start()
            depth += 1
    return out


def first_tbl(x):
    """첫 최상위 표 xml."""
    b = balanced(x, "tbl")
    return b[0][2] if b else None


def cells_of(tbl):
    """표의 직속 칸들(중첩 표 안 칸 제외): 표 안의 최상위 tr → 각 tr의 최상위 tc."""
    inner = tbl[tbl.index(">") + 1:]
    return [c for *_, tr in balanced(inner, "tr") for *_, c in balanced(tr[tr.index(">") + 1:], "tc")]


def rows_of(tbl):
    inner = tbl[tbl.index(">") + 1:]
    return [tr for *_, tr in balanced(inner, "tr")]


def tcs_of(tr):
    return [c for *_, c in balanced(tr[tr.index(">") + 1:], "tc")]


def paras_of(cell):
    """칸 안 직속 문단(subList 안 최상위 hp:p)."""
    sl = cell[cell.index("<hp:subList"):] if "<hp:subList" in cell else cell
    sl = sl[sl.index(">") + 1:]
    return [p for *_, p in balanced(sl, "p")]
