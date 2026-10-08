"""korean-report-hwpx — 한국 공문서(보고서·보도자료) 기관 서식 HWPX 생성 MCP 서버. 작성 Mia(윤승미)

외부 API 없이 로컬에서 동작한다. 원고 정리·구조화는 사용자 쪽 AI(Claude·ChatGPT 등)가 하고,
이 서버는 작성 규칙(get_writing_guide)을 알려 주고, 구조를 점검(check_structure)한 뒤 기관 서식 HWPX로 그린다(build_document).
서식은 정책브리핑 보도자료 2,670건 전수 조사로 정한 규칙값.
- 보고서(개조식): rules_report/(참고·붙임 구간 1,326건, 기관 42곳 + 공통) — refs/보고서_서식_규칙.md
- 보도자료: rules/·templates/(52개 기관) — refs/보도자료_서식_규칙.md
원본 문서·기관 로고는 포함하지 않는다.
도구:
  get_writing_guide    — 문서 종류 판단 기준·작성 규칙·구조 JSON 스키마와 예시 (MCP prompt로도 제공)
  check_structure      — 구조 JSON 생성 전 점검(고칠 점 목록)
  build_document       — 구조 JSON → 기관 서식 HWPX (+ 고칠 점 목록). build_from_structure는 별칭
  list_ministries      — 지원 기관과 문서 종류별 지원 여부
  get_rules            — 기관·문서 종류별 서식 규칙값
"""
import json
import os
import re
import sys
from pathlib import Path

from mcp.server.mcpserver import MCPServer

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "engine"))
import compose as C  # noqa: E402
import report as RP  # noqa: E402

DOC_TYPES = ("report", "press_release")
LABEL = {"report": "보고서", "press_release": "보도자료"}

mcp = MCPServer(
    "korean-report-hwpx", title="Korean Government Documents (공문서 HWPX — 보고서·보도자료)",
    instructions="사용자가 '공문서처럼 써 줘', '보고서로 만들어 줘', '보도자료로 만들어 줘'처럼 한국 공무원 문서 양식의 HWPX(한글 파일)를 원할 때 쓴다. "
                 "외부 API 없이 로컬에서 동작한다. 순서: get_writing_guide로 작성 규칙과 구조 스키마 확인 → 원고를 구조 JSON으로 정리 "
                 "→ (선택) check_structure → build_document. 결과의 warnings가 있으면 구조를 고쳐 다시 build_document. "
                 "기관을 말하지 않으면 ministry를 비워 공통 서식(보고서)으로 만든다. 원고에 없는 사실·숫자·담당자는 지어내지 않는다.")


def out_dir():
    d = Path(os.environ.get("KOREAN_REPORT_HWPX_OUT_DIR") or os.environ.get("KOREAN_GOV_DOCS_OUT_DIR") or Path.home() / "korean-report-hwpx")
    d.mkdir(parents=True, exist_ok=True); return d


# ── 작성 규칙(사용자 AI용) ──
CHOOSE = """[문서 종류 판단]
- press_release(보도자료): 언론·국민에게 대외 발표·배포하려는 글(기사체, '~했다고 밝혔다', 보도시점·담당자, 인용문 등). 기관(ministry) 지정 필수.
- report(보고서): 내부 보고·계획·검토·현황 정리용 글(추진계획, 검토안, 현황 보고, 회의 결과, 메모·요점 정리 등). 기관 선택(비우면 공통 서식).
- 애매하면 report."""

COMMON_RULES = """[공통 규칙]
- 사실·숫자·고유명사·인용·일정은 원고에 있는 것만 쓴다. 원고에 없는 내용(효과 수치, 예산, 기관명, 담당자 등)을 지어내지 않는다.
- text에는 기호(□ ㅇ ○ - * ※)를 넣지 않는다 — 계층은 type으로 표시하고 기호는 서식이 붙인다. 대시(–—)·앞 공백도 넣지 않는다.
- 각주 대상 단어 뒤에는 '*'를 붙이고(위첨자로 처리) 바로 아래 note 블록에 설명. 강조는 **굵게**(꼭 필요할 때만).
- 표·통계·일정·세부 목록 같은 참고 자료는 appendix로 빼고, 본문 해당 문장 끝에 '참고 1'(보도자료) 또는 '붙임 1'(보고서)을 적는다.
- 담당자·전화가 원고에 없으면 비운다(보도자료는 placeholder_contact=True면 '○○과 / 김○○ / 044-000-0000' 자리표시).
- 날짜는 '2026. 10. 7.(수)', 시각은 '14:00'."""

REPORT_RULES = """[보고서(개조식) 규칙]
- title: 보고서 제목 한 줄(예: '○○ 추진계획(안)', '○○ 현황 보고'). date: 원고에 작성일이 있으면 '2026. 10. 7.', 없으면 "". dept: 작성 부서, 없으면 "".
- body 블록 type:
  "h": 소제목('Ⅰ. 추진 배경', 'Ⅱ. 현황 및 문제점', 'Ⅲ. 추진 방안'처럼 로마 숫자. 짧은 원고면 생략)
  "l1": □ 대항목 — 두괄식 한 문장으로 핵심 결론을 먼저(두 문장 이상 금지)
  "l2": ㅇ 중항목 — □의 근거·세부
  "l3": - 소항목 — ㅇ의 하위 나열
  "note": * 각주, "ref": ※ 참고·유의 사항
  "caption": 표 제목(꺾쇠 없이), "table": rows 2차원 배열(첫 행 머리) — 예산·일정·현황 수치는 표로
- 계층을 건너뛰지 않는다(□ 다음 바로 - 금지).
- 문장은 명사형으로 끝낸다(~함, ~임, ~됨, ~ 예정, ~ 필요). '~합니다·~했다' 금지.
- 세부 자료는 appendix: [{"title":"붙임 1","heading":"제목","body":[블록...]}]."""

PRESS_RULES = """[보도자료 규칙]
- title: 핵심 한 줄. subtitles: 부제 명사문 1~2개(앞뒤 '-' 없이).
- release: 보도시점(예: '2026. 10. 7.(수) 조간', '배포 즉시'), 없으면 "". distribute: 배포 일시, 없으면 "".
- body 블록 type — 기관 본문 방식에 맞춘다(get_writing_guide의 ministry_style):
  문단식 기관 → "p"(기사체 문단, 첫 문단은 누가·언제·무엇), 하위 나열이 필요할 때만 "l2"(ㅇ)·"l3"(-)
  □식 기관 → "l1"(□ 대항목, 두괄식 한 문장), "l2"(ㅇ), "l3"(-)
  공통 → "note"(*), "ref"(※), "caption", "table"(rows), "box"(lines: 강조 상자), "image"(path, width_mm)
- 기관장 인용은 마지막 문단으로.
- contact: {"dept": 부서명, "people": [[구분, 직위, 이름, "(전화)"], ...]}. 원고에 있으면 본문에서는 뺀다.
- 참고 자료는 appendix: [{"title":"참고 1","heading":"제목","body":[블록...]}]."""

EXAMPLE_REPORT = {
    "title": "○○ 서비스 도입 추진계획(안)", "date": "2026. 10. 7.", "dept": "○○과",
    "body": [{"type": "h", "text": "Ⅰ. 추진 배경"},
             {"type": "l1", "text": "민원 창구 대기 시간 장기화로 개선 필요"},
             {"type": "l2", "text": "하루 평균 창구 민원 약 400건, 재방문 비율 18%"},
             {"type": "l3", "text": "서류 미비로 인한 재방문이 대부분임"},
             {"type": "caption", "text": "소요 예산"}, {"type": "table", "rows": [["구분", "금액(억 원)"], ["시스템 구축", "2"]]},
             {"type": "l1", "text": "단계별 확대 예정 붙임 1"}],
    "appendix": [{"title": "붙임 1", "heading": "세부 일정", "body": [{"type": "l1", "text": "1~2월 시범 운영"}]}]}
EXAMPLE_PRESS = {
    "release": "2026. 10. 7.(수) 조간", "distribute": "2026. 10. 6.(화) 10:00",
    "title": "○○시, AI 민원 안내 서비스 시범 운영", "subtitles": ["민원 처리 시간 단축 기대"],
    "body": [{"type": "p", "text": "○○부는 10월 7일(수)부터 AI 민원 안내 서비스를 시범 운영한다고 밝혔다."},
             {"type": "l2", "text": "자주 찾는 민원 20종을 우선 안내 참고 1"}],
    "appendix": [{"title": "참고 1", "heading": "서비스 개요", "body": [{"type": "l1", "text": "(대상) 자주 찾는 민원 20종"}]}],
    "contact": {"dept": "", "people": []}}
SCHEMA = {
    "report": {"title": "str(필수)", "date": "str", "dept": "str", "body": "[블록]", "appendix": "[{title, heading, body:[블록]}]"},
    "press_release": {"release": "str", "distribute": "str", "title": "str(필수)", "subtitles": "[str]", "body": "[블록]",
                      "appendix": "[{title, heading, body:[블록]}]", "contact": "{dept: str, people: [[구분, 직위, 이름, (전화)]]}"},
    "블록": {"h|l1|l2|l3|note|ref|p|caption": {"type": "...", "text": "str"}, "table": {"type": "table", "rows": "[[str]]"},
             "box": {"type": "box", "lines": "[str]"}, "image": {"type": "image", "path": "str", "width_mm": "int", "caption": "str(선택)"}},
}


def _style(ministry):
    return "문단식(기호 없는 기사체 문단 위주)" if C.load_rules(ministry).get("style") == "para" else "□식(□→ㅇ→- 개조식)"


def guide_text(doc_type="report", ministry=None):
    t = _norm_type(doc_type)
    parts = [CHOOSE, COMMON_RULES]
    if t in ("report", "auto"): parts.append(REPORT_RULES)
    if t in ("press_release", "auto"): parts.append(PRESS_RULES)
    if ministry and ministry in C.ministries(): parts.append(f"[기관] {ministry} — 보도자료 본문 방식: {_style(ministry)}")
    parts.append("[순서] 원고 → 위 규칙으로 구조 JSON 작성 → check_structure(선택) → build_document → warnings가 있으면 고쳐 다시 build_document")
    return "\n\n".join(parts)


@mcp.tool()
def get_writing_guide(doc_type: str = "report", ministry: str = "") -> dict:
    """원고를 공문서 구조 JSON으로 바꿀 때 지켜야 할 작성 규칙과 스키마·예시. build_document 전에 먼저 확인한다.
    doc_type: 'report'(보고서) | 'press_release'(보도자료) | 'auto'(둘 다 + 판단 기준). ministry: 기관 이름(선택)."""
    t = _norm_type(doc_type)
    out = {"guide": guide_text(t, ministry or None), "schema": SCHEMA}
    if t in ("report", "auto"): out["example_report"] = EXAMPLE_REPORT
    if t in ("press_release", "auto"): out["example_press_release"] = EXAMPLE_PRESS
    if ministry and ministry in C.ministries(): out["ministry_style"] = _style(ministry)
    return out


@mcp.prompt(name="writing_guide", title="공문서 작성 규칙")
def writing_guide_prompt(doc_type: str = "report", ministry: str = "") -> str:
    """원고를 보고서·보도자료 구조로 정리할 때의 작성 규칙과 구조 예시."""
    ex = EXAMPLE_PRESS if _norm_type(doc_type) == "press_release" else EXAMPLE_REPORT
    return guide_text(doc_type, ministry or None) + "\n\n[구조 예시]\n" + json.dumps(ex, ensure_ascii=False, indent=1)


# ── 점검·정규화 ──
TEXT_TYPES = ("h", "l1", "l2", "l3", "note", "ref", "p", "plain", "caption")
ALL_TYPES = TEXT_TYPES + ("table", "box", "image")
LEAD = re.compile(r"^[\s\u3000]*(?:[○〇ㅇ◦∘•●·‧*]+[\s\u3000]+|[\-‐–—―]+[\s\u3000]*|[□■◆◇❍▪▶►☞※]+[\s\u3000]*)+")   # ○○부 같은 가림 표기는 남김
DASH = re.compile(r"[‐–—―]")
VERB_END = re.compile(r"(니다|했다|한다|이다|된다|있다|없다|였다|밝혔다)\.?\s*(붙임\s?\d+|참고\s?\d+)?\s*$")


def _walk(structure):
    for k, b in enumerate(structure.get("body") or []): yield f"body[{k}]", b
    for a, ap in enumerate(structure.get("appendix") or []):
        for k, b in enumerate(ap.get("body") or []): yield f"appendix[{a}].body[{k}]", b


def _normalize(structure, t):
    """기호·대시·앞 공백 제거, 블록 형식 검증. (정리된 구조, 고칠 점) 반환. 원본은 바꾸지 않는다."""
    s = json.loads(json.dumps(structure or {})); w = []
    if not (s.get("title") or "").strip(): w.append("title(제목)이 비어 있음")
    elif len(s["title"]) > 40: w.append(f"제목이 깁니다({len(s['title'])}자) — 40자 안쪽 권장(긴 제목은 두 줄·축소됨)")
    s.setdefault("body", [])
    if not s["body"]: w.append("body가 비어 있음")
    for where, b in _walk(s):
        typ = b.get("type")
        if typ not in ALL_TYPES: w.append(f"{where}: 알 수 없는 type '{typ}' (가능: {', '.join(ALL_TYPES)})"); continue
        if typ in TEXT_TYPES:
            txt = b.get("text")
            if not isinstance(txt, str) or not txt.strip(): w.append(f"{where}: text가 비어 있음"); continue
            new = DASH.sub("-", txt)
            if typ not in ("caption",):
                stripped = LEAD.sub("", new) if typ != "h" else new.strip()
                if stripped != new.strip(): w.append(f"{where}: 앞 기호·공백 제거함('{txt[:8]}…') — text에 기호를 넣지 말 것")
                new = stripped
            b["text"] = new.strip()
        elif typ == "table":
            if not b.get("rows") or not all(isinstance(r, list) for r in b["rows"]): w.append(f"{where}: table.rows는 2차원 배열이어야 함")
        elif typ == "box":
            if not b.get("lines"): w.append(f"{where}: box.lines가 비어 있음")
        elif typ == "image":
            if not b.get("path") or not Path(str(b["path"])).expanduser().exists(): w.append(f"{where}: image.path 파일이 없음")
    for a, ap in enumerate(s.get("appendix") or []):
        if not ap.get("heading"): w.append(f"appendix[{a}]: heading(참고·붙임 제목)이 비어 있음")
    if t == "press_release":
        if not s.get("release"): w.append("release(보도시점)가 비어 있음 — 원고에 없으면 그대로 두어도 됨")
    return s, w


def _style_warnings(s, t):
    w = []; prev = None
    rank = {"h": -1, "l1": 0, "l2": 1, "l3": 2}
    for where, b in _walk(s):
        typ, txt = b.get("type"), (b.get("text") or "")
        if where.endswith("[0]") and where.startswith("appendix"): prev = None
        if typ in ("l1", "l2", "l3"):
            if prev is not None and rank[typ] - rank.get(prev, 0) > 1: w.append(f"{where}: 계층 건너뜀({prev} 다음 {typ})")
            if prev is None and typ == "l3": w.append(f"{where}: 첫 계층 항목이 '-'(l3)임")
            prev = typ
        elif typ == "h": prev = None
        if typ == "l1":
            n = len(re.findall(r"(?:다|함|임|됨|음)\.(?:\s|$)|[.?!](?=\s+\S)", txt.strip()))
            if n >= 2: w.append(f"{where}: □(l1)는 두괄식 한 문장 — 문장이 {n}개")
        if t == "report" and typ in ("l1", "l2", "l3") and VERB_END.search(txt):
            w.append(f"{where}: 명사형 종결(~함·~임·~ 예정)이 아님: '…{txt.strip()[-12:]}'")
    return w


def check(structure, doc_type="report"):
    t = _norm_type(doc_type)
    if t == "auto": t = "press_release" if any(k in (structure or {}) for k in ("release", "contact", "subtitles")) else "report"
    s, w = _normalize(structure, t)
    return t, s, w + _style_warnings(s, t)


@mcp.tool()
def check_structure(structure: dict, doc_type: str = "report") -> dict:
    """구조 JSON을 만들기 전에 점검만 한다(파일 생성 없음): 필수 필드, 알 수 없는 블록, text 속 기호, 계층 건너뜀,
    □ 두 문장 이상, 보고서 명사형 종결이 아닌 문장, 긴 제목 등. 돌려주는 값: {ok, doc_type, warnings}."""
    t, _, w = check(structure, doc_type)
    return {"ok": not w, "doc_type": t, "warnings": w}


def _dst(ministry, title, out_path, doc_type):
    name = ministry or "공통"
    return Path(out_path).expanduser() if out_path else out_dir() / f"{name}_{LABEL[doc_type]}_{re.sub(r'[^가-힣A-Za-z0-9]+', '_', title or LABEL[doc_type])[:30]}.hwpx"


def _norm_type(doc_type):
    t = (doc_type or "auto").strip().lower().replace("-", "_")
    t = {"보고서": "report", "보도자료": "press_release", "press": "press_release", "자동": "auto"}.get(doc_type, t)
    if t not in DOC_TYPES + ("auto",): raise ValueError(f"doc_type은 'auto'·'report'·'press_release' 중 하나: {doc_type}")
    return t


def _check_ministry(ministry, doc_type):
    if doc_type == "press_release":
        if ministry not in C.ministries():
            raise ValueError(f"보도자료는 기관 지정이 필요합니다(52개 중 하나, list_ministries 참고): {ministry or '(없음)'}")
    elif ministry and ministry not in ("공통",) and ministry not in C.ministries():
        raise ValueError(f"지원하지 않는 기관: {ministry} (list_ministries 참고, 비우면 공통 서식)")


def _build(doc_type, ministry, doc, dst, logo_path="", slogan_path="", placeholder_contact=True, polish=False):
    if doc_type == "report":
        if polish:
            import polish as PL
            PL.polish(ministry, doc, dst, log=lambda m: None, build=RP.compose, logo_path=logo_path or None)
        else:
            RP.compose(ministry, doc, dst, logo_path=logo_path or None)
    else:
        kw = dict(logo_path=logo_path or None, slogan_path=slogan_path or None, placeholder_contact=placeholder_contact)
        if polish:
            import polish as PL
            PL.polish(ministry, doc, dst, log=lambda m: None, **kw)
        else:
            C.compose(ministry, doc, dst, **kw)
    return dst


@mcp.tool()
def list_ministries() -> list[dict]:
    """지원 기관과 문서 종류별 지원 여부. 보고서: 기관 규칙(42곳) 또는 공통 규칙, 보도자료: 52개 기관.
    보고서는 기관을 비우거나 '공통'으로 하면 기관 간 공통 서식으로 만든다."""
    rep = set(RP.ministries()); out = []
    for o in C.ministries():
        r = C.load_rules(o)
        out.append({"기관": o, "보고서": "기관 규칙" if o in rep else "공통 규칙", "보도자료": "지원",
                    "보도자료_본문방식": "문단식" if r.get("style") == "para" else "□식"})
    out.append({"기관": "공통(미지정)", "보고서": "공통 규칙", "보도자료": "미지원(기관 지정 필요)", "보도자료_본문방식": ""})
    return out


@mcp.tool()
def get_rules(ministry: str = "", doc_type: str = "report") -> dict:
    """기관·문서 종류별 서식 규칙값: 계층별 기호·기호 앞 공백·글꼴·크기·줄 간격, 계층 사이 빈 줄 크기,
    보고서는 제목 상자·표 머리 규칙 포함. ministry를 비우면 보고서 공통 규칙."""
    t = _norm_type(doc_type)
    if t == "auto": t = "report"
    _check_ministry(ministry, t)
    r = RP.load_rules(ministry) if t == "report" else C.load_rules(ministry)
    r.pop("_base", None)
    if t == "report": r["적용"] = "기관 규칙" if RP.resolve(ministry)[0] != RP.COMMON else "공통 규칙"
    return r


@mcp.tool()
def build_document(structure: dict, doc_type: str = "report", ministry: str = "", out_path: str = "",
                   logo_path: str = "", slogan_path: str = "", placeholder_contact: bool = True, polish: bool = False) -> dict:
    """구조 JSON을 기관 서식 HWPX로 만든다(외부 전송 없음, 모두 로컬). 구조는 get_writing_guide 규칙대로 사용자 AI가 작성한다.
    doc_type='report': {title, date, dept, body, appendix} — ministry를 비우면 공통 서식(기관명 칸 비움).
    doc_type='press_release': {release, distribute, title, subtitles, body, appendix, contact} — ministry 필수.
    입력은 정규화(text 앞 기호·대시·공백 제거)하고, 고칠 점을 warnings로 돌려준다 — 있으면 구조를 고쳐 다시 호출한다.
    logo_path: 기관 로고 그림(선택). slogan_path: 보도자료 슬로건 그림(선택).
    placeholder_contact: 보도자료 담당자가 없으면 '○○과 / 김○○ / 044-000-0000' 자리표시로 채움.
    polish: True면 맥 한컴오피스 한글로 실제 줄 배치를 받아 문단별 자간을 다듬음(맥+한글 필요, 수 분 소요).
    돌려주는 값: {hwpx, doc_type, 문서종류, 기관, warnings, structure(정리된 구조)}. 같은 이름 .json에 구조도 저장."""
    t, s, w = check(structure, doc_type)
    org = ministry if ministry and ministry != "공통" else ""
    _check_ministry(org, t)
    dst = _dst(org, s.get("title"), out_path, t)
    _build(t, org, s, dst, logo_path, slogan_path, placeholder_contact, polish)
    dst.with_suffix(".json").write_text(json.dumps(s, ensure_ascii=False, indent=1), "utf-8")
    return {"hwpx": str(dst), "doc_type": t, "문서종류": LABEL[t], "기관": org or "공통(미지정)", "warnings": w, "structure": s}


@mcp.tool()
def build_from_structure(structure: dict, doc_type: str = "report", ministry: str = "", out_path: str = "",
                         logo_path: str = "", slogan_path: str = "", placeholder_contact: bool = True, polish: bool = False) -> dict:
    """build_document와 같다(별칭)."""
    return build_document(structure, doc_type, ministry, out_path, logo_path, slogan_path, placeholder_contact, polish)


def main():
    import argparse
    p = argparse.ArgumentParser(prog="korean-report-hwpx", description="한국 공문서(보고서·보도자료) 기관 서식 HWPX 생성 MCP 서버")
    p.add_argument("--http", action="store_true"); p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8002)))
    a = p.parse_args()
    if a.http:
        import uvicorn
        uvicorn.run(mcp.streamable_http_app(streamable_http_path="/mcp", host=a.host), host=a.host, port=a.port)
    else:
        mcp.run("stdio")


if __name__ == "__main__":
    main()
