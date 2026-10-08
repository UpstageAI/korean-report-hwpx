"""기관 표지·담당 표 서식 수치 추출 (유지보수용, 공개판 실행에는 필요 없음). 작성 Mia(윤승미)

원본 보도자료 HWPX(공개판에 포함하지 않음)를 읽어 서식 수치만 templates/<기관>.json으로 쓴다.
담는 것: 쪽 크기·여백, 표지 표/보도시점 표/제목 표/담당 표의 칸 폭·높이·글꼴·크기·굵기·색·바탕색·테두리.
담지 않는 것: 원본 문서 번호·제목·본문·이름·전화·그림, XML 조각.

사용: python scripts/extract_layout.py <원본 templates 폴더(틀 JSON + 기관 폴더)> <출력 templates 폴더>
"""
import json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "korean_report_hwpx" / "engine"))
from hwpx_doc import Hwpx, first_tbl, cells_of, rows_of, tcs_of, paras_of  # noqa: E402

RELEASE_LABEL = re.compile(r"^[/\s]*(보도\s*(시점|일시)|배\s*포(\s*(일시|시점))?)\s*[:：]?\s*$")
INLINE = re.compile(r"^\s*(보도\s*(시점|일시))\s*[:：]\s*\S")
COVER_CELL = re.compile(r"\s*(보\s*도\s*)?(참\s*고\s*|설\s*명\s*|해\s*명\s*)?자\s*료\s*")


def is_cover(p):
    return any(COVER_CELL.fullmatch(text(c)) for c in cells_of(first_tbl(p)))


def text(x):
    return re.sub(r"\s+", " ", Hwpx.text(x, True)).strip()


def border_fill(d, bid):
    m = re.search(r'<hh:borderFill id="%s".*?</hh:borderFill>' % bid, d.header, re.S)
    if not m: return {"fill": None, "line": "SOLID", "width": "0.12 mm", "color": "#000000"}
    s = m.group(0)
    face = re.search(r'faceColor="([^"]+)"', s)
    fill = face.group(1) if face and face.group(1).lower() not in ("none", "#ffffff") else None
    sides = re.findall(r'<hh:(left|right|top|bottom)Border type="(\w+)" width="([^"]+)" color="([^"]+)"', s)
    vis = [x for x in sides if x[1] != "NONE"]
    side = vis[0] if vis else ("top", "NONE", "0.1 mm", "#000000")
    return {"fill": fill, "line": side[1], "width": side[2], "color": side[3],
            "sides": {k: t for k, t, *_ in sides}}


def char_of(d, x):
    """칸·문단에서 글자가 가장 많은 조각의 글자 모양."""
    runs = re.findall(r'<hp:run charPrIDRef="(\d+)"[^>]*>(.*?)</hp:run>', x, re.S)
    if not runs: return None
    cid = max(runs, key=lambda r: len(Hwpx.text(r[1])))[0]
    c = d.char(cid)
    return {"font": c.get("font"), "pt": c.get("pt"), "bold": c.get("bold"), "color": c.get("color"),
            "spacing": c.get("spacing", 0), "ratio": c.get("ratio", 100)}


def align_of(d, x):
    m = re.search(r'paraPrIDRef="(\d+)"', x)
    return d.para(m.group(1)).get("align", "CENTER") if m else "CENTER"


def cell_info(d, c):
    w, h = re.search(r'<hp:cellSz width="(\d+)" height="(\d+)"', c).groups()
    bf = re.search(r'borderFillIDRef="(\d+)"', c).group(1)
    span = re.search(r'<hp:cellSpan colSpan="(\d+)" rowSpan="(\d+)"', c).groups()
    ps = [p for p in paras_of(c) if Hwpx.text(p).strip()] or paras_of(c)
    return {"w": int(w), "h": int(h), "colspan": int(span[0]), "rowspan": int(span[1]), "border": border_fill(d, bf),
            "char": char_of(d, ps[0]) if ps else None, "align": align_of(d, ps[0]) if ps else "CENTER", "text": text(c)}


def table_box(d, p):
    tb = first_tbl(p)
    w, h = re.search(r'<hp:sz width="(\d+)" widthRelTo="\w+" height="(\d+)"', tb).groups()
    return {"width": int(w), "height": int(h), "border": border_fill(d, re.search(r'borderFillIDRef="(\d+)"', tb).group(1))}


def extract(org, t, src):
    d = Hwpx(src)
    ps = [p for *_, p in d.paragraphs()]
    pg = re.search(r'<hp:pagePr[^>]*width="(\d+)" height="(\d+)"', d.section).groups()
    mg = dict(re.findall(r'(\w+)="(\d+)"', re.search(r"<hp:margin [^>]*/>", d.section).group(0)))
    out = {"org": org, "page": {"width": int(pg[0]), "height": int(pg[1]), **{k: int(v) for k, v in mg.items()}}}
    head = [i for i in t["head"] if "<hp:tbl" in ps[i]]
    title_i = t["title"][0] if t.get("title") and t["title"][2] == "table" else None
    if title_i is not None and is_cover(ps[title_i]):   # 표지 표를 제목으로 잘못 학습한 경우: 표지·보도시점 다음 표
        title_i = next((i for i in head if i > title_i and not is_cover(ps[i]) and not any(RELEASE_LABEL.match(text(c)) for c in cells_of(first_tbl(ps[i])))), None)

    # 표지(기관명·'보도자료') 표: '보도…자료' 글이 있는 첫 표
    cover_i = next((i for i in head if is_cover(ps[i]) and i != title_i), None)
    if cover_i is not None:
        cs = [cell_info(d, c) for c in cells_of(first_tbl(ps[cover_i]))]
        k = next(j for j, c in enumerate(cs) if COVER_CELL.fullmatch(c["text"]))
        lab = re.sub(r"\s+", "", cs[k]["text"])
        out["cover"] = {**table_box(d, ps[cover_i]), "widths": [c["w"] for c in cs], "label_col": k,
                        "label": lab if lab in ("보도자료", "보도참고자료", "보도설명자료", "보도해명자료") else "보도자료",
                        "label_char": cs[k]["char"], "label_fill": cs[k]["border"]["fill"],
                        "logo_col": max((j for j in range(len(cs)) if j != k), key=lambda j: (j < k, cs[j]["w"]), default=None)}

    # 보도시점·배포 표: 이름표 칸이 있는 머리 표(첫 행만)
    rel_i = next((i for i in head if i not in (cover_i, title_i) and any(RELEASE_LABEL.match(text(c)) or INLINE.match(text(c)) for c in cells_of(first_tbl(ps[i])))), None)
    if rel_i is not None:
        row = tcs_of(rows_of(first_tbl(ps[rel_i]))[0])
        cells = []
        for c in row:
            ci = cell_info(d, c); m = RELEASE_LABEL.match(ci["text"])
            if INLINE.match(ci["text"]): role, lab = "release_inline", re.sub(r"\s+", "", INLINE.match(ci["text"]).group(1))
            elif m and re.search(r"보\s*도", m.group(0)): role, lab = "release_label", re.sub(r"\s+", "", m.group(1))
            elif m: role, lab = "distribute_label", "배포"
            elif ci["text"] and not re.search(r"\d", ci["text"]) and len(ci["text"]) <= 8 and not re.search(r"즉시|시점|이후|부터", ci["text"]):
                role, lab = "label", ci["text"]   # 그 밖의 이름표(온라인·방송 등)
            else: role, lab = "value", ""
            cells.append({"role": role, "label": lab, "w": ci["w"], "h": ci["h"], "char": ci["char"], "fill": ci["border"]["fill"], "line": ci["border"]["line"], "align": ci["align"]})
        for j, c in enumerate(cells):   # 보도시점 바로 뒤 '배포 즉시'류 값은 이름표가 아님
            if j and c["role"] == "distribute_label" and cells[j - 1]["role"] == "release_label": c["role"], c["label"] = "value", ""
        for j, c in enumerate(cells):   # 값 칸 성격: 바로 앞 이름표
            if c["role"] == "value":
                c["role"] = {"release_label": "release", "distribute_label": "distribute"}.get(cells[j - 1]["role"], "blank") if j else "blank"
        out["release"] = {**table_box(d, ps[rel_i]), "cells": cells}

    # 제목 표: 제목 칸(+부제 칸)
    if title_i is not None:
        cs = [cell_info(d, c) for c in cells_of(first_tbl(ps[title_i]))]
        k = t["title"][1] if title_i == t["title"][0] else 0
        rows = [{"role": "title", **{x: cs[k][x] for x in ("w", "h", "char", "align")}, "fill": cs[k]["border"]["fill"], "border": cs[k]["border"]}]
        if k + 1 < len(cs):
            rows.append({"role": "subtitle", **{x: cs[k + 1][x] for x in ("w", "h", "char", "align")}, "fill": cs[k + 1]["border"]["fill"], "border": cs[k + 1]["border"]})
        out["title"] = {**table_box(d, ps[title_i]), "rows": rows}
    elif t.get("title"):
        q = ps[t["title"][0]]
        out["title"] = {"para": True, "char": char_of(d, q), "align": align_of(d, q)}

    # 담당 표: 6칸 행(담당 부서|부서명|구분|직위|이름|전화)의 폭·글꼴·바탕색
    if t.get("contact") is not None:
        tb = first_tbl(ps[t["contact"]])
        row = next((r for r in rows_of(tb) if len(tcs_of(r)) == 6), rows_of(tb)[0])
        cs = [cell_info(d, c) for c in tcs_of(row)]
        total = sum(c["w"] for c in cs)
        widths = [c["w"] for c in cs] if len(cs) == 6 else [int(total * r) for r in (0.14, 0.24, 0.12, 0.13, 0.13, 0.24)]
        lab = cs[0] if len(cs) == 6 else cs[0]
        val = next((c for c in cs[1:] if c["char"]), cs[-1])
        out["contact"] = {**table_box(d, ps[t["contact"]]), "widths": widths, "row_h": max(c["h"] for c in cs) if len(cs) == 6 else 1800,
                          "label_char": lab["char"] or val["char"], "label_fill": lab["border"]["fill"], "value_char": val["char"],
                          "value_fill": val["border"]["fill"], "line": lab["border"]["line"], "line_width": lab["border"]["width"],
                          "labels": {"dept": "담당 부서", "head": "책임자", "staff": "담당자"}}
    out["heading"] = t.get("heading", {})
    return out


if __name__ == "__main__":
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    dst.mkdir(parents=True, exist_ok=True)
    for f in sorted(src.glob("*.json")):
        if not (src / f.stem).is_dir(): continue
        t = json.loads(f.read_text("utf-8"))
        o = extract(f.stem, t, src / f.stem / t["hwpx"])
        (dst / f"{f.stem}.json").write_text(json.dumps(o, ensure_ascii=False, indent=1), "utf-8")
        print(f.stem, "cover" in o, "release" in o and [c["role"] for c in o["release"]["cells"]], "title" in o and len(o["title"].get("rows", [])), "contact" in o)
