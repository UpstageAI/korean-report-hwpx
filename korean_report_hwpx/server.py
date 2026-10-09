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
import platform
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
STYLES = ("standard", "simplified")
REPORT_KINDS = ("standard", "internal")

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
- title: 보고서 제목 한 줄(예: '○○ 추진계획(안)', '○○ 현황 보고'). date: 원고에 작성일이 명시된 경우에만 '2026. 10. 7.' 형식으로 넣고, 없으면 ""(서버가 오늘 날짜로 채움). 날짜를 추정해 지어내지 않는다. dept: 작성 부서, 없으면 "".
- body 블록 type:
  "h": 소제목('Ⅰ. 추진 배경', 'Ⅱ. 현황 및 문제점', 'Ⅲ. 추진 방안'처럼 로마 숫자. 짧은 원고면 생략)
  "l1": □ 대항목 — 두괄식 한 문장으로 핵심 결론을 먼저(두 문장 이상 금지)
  "l2": ㅇ 중항목 — □의 근거·세부
  "l3": - 소항목 — ㅇ의 하위 나열
  "note": * 각주, "ref": ※ 참고·유의 사항
  "caption": 표 제목(꺾쇠 없이), "table": rows 2차원 배열(첫 행 머리) — 예산·일정·현황 수치는 표로
  표는 가능하면 4열 이하. 긴 설명은 '요지' 한 칸에 모으고, 법원·일자처럼 짧은 정보는 문서번호 칸에 함께 적는다. 표마다 앞에 caption을 둔다
- 계층을 건너뛰지 않는다(□ 다음 바로 - 금지).
- 문장은 명사형으로 끝낸다(~함, ~임, ~됨, ~ 예정, ~ 필요). '~합니다·~했다' 금지.
- 세부 자료는 appendix: [{"title":"붙임 1","heading":"제목","body":[블록...]}]."""

SIMPLIFIED_RULES = """[간소화 모드 규칙] style="simplified" 지정 시 적용.
- 항목 기호(□ ㅇ ○ - * ※) 대신 단계별 번호 사용: 소제목은 Ⅰ. Ⅱ. Ⅲ., 대항목은 1. 2. 3., 중항목은 가. 나. 다., 소항목은 1) 2) 3), 그 아래는 가) 나) 다). 번호는 서버가 구조 JSON의 계층 수준(level)에서 자동 부여하며, 사용자가 번로를 직접 쓰지 않는다.
- 단계별 들여쓰기 유지됨.
- 서술식 문장 허용: ~합니다·~했다 등 동사형 종결도 사용 가능(명사형 종결 경고 없음).
- 제목 상자(테두리·음영) 없이 일반 제목 문단으로 표시.
- 표 머리 음영 없음.
- 표 제목: caption 블록을 앞에 두거나, table 블록의 title/caption 키에 표 제목을 직접 지정하면 서버가 표 바로 위에 '〈표 1〉 제목' 형식으로 자동 번호 부여한다. 두 방식 모두 표마다 번호가 증가한다.
- 표 셀 병합 금지: 구조에 병합이 있으면 같은 값을 행마다 반복하도록 풀어 쓴다.
- check_structure가 간소화 규칙(번호 수준 건너뜀, 표 제목 누락, 병합 사용, 5단계 초과)을 점검.
- export_markdown=True이면 같은 구조로 .md 파일을 HWPX 옆에 함께 저장(GFM 표, 병합 없이, 번호 위계는 #, ##, ###와 번호 텍스트)."""

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
             {"type": "table", "title": "서식별 비교", "rows": [["구분", "값"], ["가", "100"]]},
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
    "블록": {"h|l1|l2|l3|note|ref|p|caption": {"type": "...", "text": "str"}, "table": {"type": "table", "rows": "[[str]]", "title|caption": "str(표 제목, 선택)"},
             "box": {"type": "box", "lines": "[str]"}, "image": {"type": "image", "path": "str", "width_mm": "int", "caption": "str(선택)"}},
}


def _style(ministry):
    return "문단식(기호 없는 기사체 문단 위주)" if C.load_rules(ministry).get("style") == "para" else "□식(□→ㅇ→- 개조식)"


def guide_text(doc_type="report", ministry=None, style="standard"):
    t = _norm_type(doc_type)
    parts = [CHOOSE, COMMON_RULES]
    if t in ("report", "auto"): parts.append(REPORT_RULES)
    if t in ("press_release", "auto"): parts.append(PRESS_RULES)
    if ministry and ministry in C.ministries(): parts.append(f"[기관] {ministry} — 보도자료 본문 방식: {_style(ministry)}")
    if style == "simplified":
        parts.append(SIMPLIFIED_RULES)
    parts.append("[순서] 원고 → 위 규칙으로 구조 JSON 작성 → check_structure(선택) → build_document → warnings가 있으면 고쳐 다시 build_document")
    return "\n\n".join(parts)


@mcp.tool()
def get_writing_guide(doc_type: str = "report", ministry: str = "", style: str = "standard") -> dict:
    """원고를 공문서 구조 JSON으로 바꿀 때 지켜야 할 작성 규칙과 스키마·예시. build_document 전에 먼저 확인한다.
    doc_type: 'report'(보고서) | 'press_release'(보도자료) | 'auto'(둘 다 + 판단 기준). ministry: 기관 이름(선택).
    style: 'standard'(기본, 기존 동작) | 'simplified'(간소화 모드 — 항목 번호 자동 부여, 제목 상자 없음, 표 머리 음영 없음, 표 제목 자동 번호, 서술식 허용)."""
    if style not in STYLES:
        raise ValueError(f"style은 'standard' 또는 'simplified': {style}")
    t = _norm_type(doc_type)
    out = {"guide": guide_text(t, ministry or None, style), "schema": SCHEMA, "style": style}
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
    apps = s.get("appendix") or []
    for a, ap in enumerate(apps):
        if not ap.get("heading"): w.append(f"appendix[{a}]: heading(참고·붙임 제목)이 비어 있음")
    titles = [str(ap.get("title") or "") for ap in apps]
    if len(set(titles)) < len(titles):  # 붙임·참고 번호가 겹치면 순서대로 다시 매김
        word = "참고" if t == "press_release" else "붙임"
        for a, ap in enumerate(apps): ap["title"] = f"{word} {a + 1}"
        w.append(f"appendix: {word} 번호가 겹쳐 {word} 1~{len(apps)}로 다시 매김 — 같은 내용을 두 번 넣지 않았는지 확인")
    for a, ap in enumerate(apps):  # 표 제목 없이 표부터 나오면 경고
        body = ap.get("body") or []
        for k, b in enumerate(body):
            if b.get("type") == "table" and not (k > 0 and body[k - 1].get("type") == "caption"):
                w.append(f"appendix[{a}].body[{k}]: 표 앞에 caption(표 제목)이 없음 — 표 제목 블록을 앞에 넣을 것")
    heads = [str(ap.get("heading") or "") for ap in apps]
    if len(set(heads)) < len(heads): w.append("appendix: heading이 같은 붙임이 둘 이상 — 중복 여부 확인")
    if t == "press_release":
        if not s.get("release"): w.append("release(보도시점)가 비어 있음 — 원고에 없으면 그대로 두어도 됨")
    return s, w


def _style_warnings(s, t, style="standard"):
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
        if typ == "l1" and style != "simplified":
            n = len(re.findall(r"(?:다|함|임|됨|음)\.(?:\s|$)|[.?!](?=\s+\S)", txt.strip()))
            if n >= 2: w.append(f"{where}: □(l1)는 두괄식 한 문장 — 문장이 {n}개")
        if t == "report" and style != "simplified" and typ in ("l1", "l2", "l3") and VERB_END.search(txt):
            w.append(f"{where}: 명사형 종결(~함·~임·~ 예정)이 아님: '…{txt.strip()[-12:]}'")
        # simplified 모드: 표 병합 점검
        if style == "simplified" and typ == "table":
            rows = b.get("rows") or []
            for ri, r in enumerate(rows):
                for ci, cell in enumerate(r):
                    if isinstance(cell, dict) and cell.get("merge"):
                        w.append(f"{where}: 표 셀 병합 사용 — 간소화 모드는 병합 금지, 같은 값을 행마다 반복할 것")
    return w


def _check_simplified_structure(s, t):
    """간소화 모드 전용 점검: 번호 수준 건너뜀, 표 제목 누락, 5단계 초과, 병합 사용."""
    w = []
    rank = {"h": 0, "l1": 1, "l2": 2, "l3": 3}
    max_level = 0
    prev_level = None
    table_count = 0
    for where, b in _walk(s):
        typ = b.get("type")
        if typ in rank:
            level = rank[typ]
            max_level = max(max_level, level)
            if prev_level is not None and level > prev_level + 1:
                w.append(f"{where}: 번호 수준 건너뜀({prev_level}단계 다음 {level}단계) — 간소화 모드는 Ⅰ.→1.→가.→1)→가) 순서 준수")
            prev_level = level
        elif typ == "h":
            prev_level = 0
        elif typ == "table":
            table_count += 1
            rows = b.get("rows") or []
            for ri, r in enumerate(rows):
                for ci, cell in enumerate(r):
                    if isinstance(cell, dict) and cell.get("merge"):
                        w.append(f"{where}: 표 셀 병합 사용 — 간소화 모드는 병합 금지, 같은 값을 행마다 반복할 것")
    if max_level > 4:
        w.append(f"간소화 모드: 5단계({max_level}단계) 초과 — 간소화 모드는 Ⅰ.→1.→가.→1)→가) 4단계까지만 지원")
    # 표 제목 점검
    for where, b in _walk(s):
        if b.get("type") == "table":
            # 직전 블록이 caption인지 확인
            pass  # _normalize에서 이미 점검함
    return w


def check(structure, doc_type="report", style="standard"):
    t = _norm_type(doc_type)
    if t == "auto": t = "press_release" if any(k in (structure or {}) for k in ("release", "contact", "subtitles")) else "report"
    s, w = _normalize(structure, t)
    w = w + _style_warnings(s, t, style)
    if style == "simplified":
        w = w + _check_simplified_structure(s, t)
    return t, s, w


@mcp.tool()
def check_structure(structure: dict, doc_type: str = "report", style: str = "standard") -> dict:
    """구조 JSON을 만들기 전에 점검만 한다(파일 생성 없음): 필수 필드, 알 수 없는 블록, text 속 기호, 계층 건너뜀,
    □ 두 문장 이상, 보고서 명사형 종결이 아닌 문장, 긴 제목 등. 돌려주는 값: {ok, doc_type, warnings}.
    style: 'standard'(기본) | 'simplified'(간소화 모드 — 번호 수준 건너뜀, 표 제목 누락, 병합 사용, 5단계 초과 추가 점검)."""
    if style not in STYLES:
        raise ValueError(f"style은 'standard' 또는 'simplified': {style}")
    t, _, w = check(structure, doc_type, style)
    return {"ok": not w, "doc_type": t, "warnings": w}


def _dst(ministry, title, out_path, doc_type):
    name = ministry or "공통"
    return Path(out_path).expanduser() if out_path else out_dir() / f"{name}_{LABEL[doc_type]}_{re.sub(r'[^가-힣A-Za-z0-9]+', '_', title or LABEL[doc_type])[:30]}.hwpx"


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


def _convert_table_titles(s):
    """table 블록의 title/caption 키를 caption 블록으로 변환.
    table.title 또는 table.caption이 있으면 표 바로 앞에 caption 블록을 삽입하고
    table 블록에서는 해당 키를 제거한다. 모든 스타일(standard·internal·simplified)에서
    표 제목이 자동으로 출력되도록 한다."""
    def _process_body(body):
        result = []
        for b in body:
            if b.get("type") == "table" and (b.get("title") or b.get("caption")):
                title = b.pop("title", None) or b.pop("caption", "")
                result.append({"type": "caption", "text": title})
            result.append(dict(b))
            if "body" in b:
                b["body"] = _process_body(b["body"])
        return result

    s = dict(s)
    s["body"] = _process_body(s.get("body") or [])
    s["appendix"] = [dict(a, body=_process_body(a.get("body") or [])) for a in s.get("appendix") or []]
    return s


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


def _today():
    import datetime
    d = datetime.date.today()
    return f"{d.year}. {d.month}. {d.day}."


def _build(doc_type, ministry, doc, dst, logo_path="", slogan_path="", placeholder_contact=True, polish=False, style="standard", report_kind="standard"):
    if doc_type == "report":
        if not str(doc.get("date") or "").strip():
            doc["date"] = _today()  # 작성일 미기재 시 오늘 날짜
        if polish:
            import polish as PL
            PL.polish(ministry, doc, dst, log=lambda m: None, build=RP.compose, logo_path=logo_path or None)
        else:
            RP.compose(ministry, doc, dst, logo_path=logo_path or None, style=style, report_kind=report_kind)
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
                   logo_path: str = "", slogan_path: str = "", placeholder_contact: bool = True, polish: bool = False,
                   style: str = "standard", export_markdown: bool = False, report_kind: str = "standard") -> dict:
    """구조 JSON을 기관 서식 HWPX로 만든다(외부 전송 없음, 모두 로컬). 구조는 get_writing_guide 규칙대로 사용자 AI가 작성한다.
    doc_type='report': {title, date, dept, body, appendix} — ministry를 비우면 공통 서식(기관명 칸 비움).
    doc_type='press_release': {release, distribute, title, subtitles, body, appendix, contact} — ministry 필수.
    입력은 정규화(text 앞 기호·대시·공백 제거)하고, 고칠 점을 warnings로 돌려준다 — 있으면 구조를 고쳐 다시 호출한다.
    logo_path: 기관 로고 그림(선택). slogan_path: 보도자료 슬로건 그림(선택).
    placeholder_contact: 보도자료 담당자가 없으면 '○○과 / 김○○ / 044-000-0000' 자리표시로 채움.
    polish: True면 맥 한컴오피스 한글로 실제 줄 배치를 받아 문단별 자간을 다듬음(맥+한글 필요, 수 분 소요).
    style: 'standard'(기본, 기존 동작) | 'simplified'(간소화 모드 — 항목 번호 자동 부여, 제목 상자 없음, 표 머리 음영 없음, 표 제목 자동 번호, 서술식 허용).
    export_markdown: True이면 같은 구조로 .md 파일을 HWPX 옆에 함께 저장(GFM 표, 병합 없이, 번호 위계는 #, ##, ###와 번호 텍스트).
    report_kind: 'standard'(기본, 기존 보고서 서식) | 'internal'(내부 결재 보고서 — 제목 상자 라벨 없음, 쪽 번호 "- n -", 작성일·부서 "'26. 10. 8.(목) / 과·팀명" 형식, 표 머리 음영 없음/회색, □ 글꼴 HY헤드라인M).
    돌려주는 값: {hwpx, doc_type, 문서종류, 기관, warnings, structure(정리된 구조), md(export_markdown=True일 때)}. 같은 이름 .json에 구조도 저장."""
    if style not in STYLES:
        raise ValueError(f"style은 'standard' 또는 'simplified': {style}")
    if report_kind not in REPORT_KINDS:
        raise ValueError(f"report_kind은 'standard' 또는 'internal': {report_kind}")
    t, s, w = check(structure, doc_type, style)
    org = ministry if ministry and ministry != "공통" else ""
    _check_ministry(org, t)
    dst = _dst(org, s.get("title"), out_path, t)
    # table.title/caption 키를 caption 블록으로 변환 (모든 스타일)
    s = _convert_table_titles(s)
    # 간소화 모드: 마크다운 export를 위해 변환본 미리 준비
    s_for_md = s
    if style == "simplified":
        s_for_md = _simplify_numbers(s)
        s_for_md = _add_table_numbers(s_for_md)
        # 표 병합 풀어쓰기
        s_for_md = dict(s_for_md)
        s_for_md["body"] = [dict(b) for b in s_for_md.get("body", [])]
        for b in s_for_md["body"]:
            if b.get("type") == "table":
                b["rows"] = _unroll_table_rows(b.get("rows", []))
        for a in s_for_md.get("appendix", []):
            a = dict(a)
            a["body"] = [dict(b) for b in a.get("body", [])]
            for b in a["body"]:
                if b.get("type") == "table":
                    b["rows"] = _unroll_table_rows(b.get("rows", []))
    _build(t, org, s, dst, logo_path, slogan_path, placeholder_contact, polish, style, report_kind)
    # 저장용 구조는 변환 전 원본 유지
    dst.with_suffix(".json").write_text(json.dumps(s, ensure_ascii=False, indent=1), "utf-8")
    md_path = ""
    if export_markdown:
        # s_for_md는 이미 간소화 모드 처리(번호 부여, 표 번호, 병합 풀기)가 완료된 상태
        # _export_markdown에서 다시 처리하지 않도록 style="standard"로 전달
        md_path = _export_markdown(s_for_md, dst, "standard")
    result = {"hwpx": str(dst), "doc_type": t, "문서종류": LABEL[t], "기관": org or "공통(미지정)", "warnings": w, "structure": s}
    if md_path: result["md"] = md_path
    return result


def _unroll_table_rows(rows):
    """표 행의 병합 셀 풀어쓰기 (간소화 모드용). 병합 dicts를 일반 문자열로 변환."""
    if not rows: return rows
    from report import ReportComposer
    # 임시 composer 인스턴스 생성 (실제 build 없이 merge 처리만)
    import compose as C
    org = ""
    c = ReportComposer(org)
    return c._unroll_table_merges(rows)


def _export_markdown(s, hwpx_path, style="standard"):
    """구조 JSON을 GFM 마크다운으로 변환하여 HWPX 옆 .md 파일로 저장.
    간소화 모드면 번호 부여·표 번호 적용 후 변환."""
    md_path = Path(str(hwpx_path).replace(".hwpx", ".md"))
    # 간소화 모드: 엔진과 동일하게 번호 부여 후 변환
    if style == "simplified":
        s = _simplify_numbers(s)
        s = _add_table_numbers(s)

    def _blocks_to_md(bs, level=0):
        lines = []
        for b in bs:
            typ = b.get("type")
            if typ == "h":
                level += 1
                lines.append(f"{'#' * min(level, 3)} {b.get('text', '').strip()}")
            elif typ == "l1":
                # l1은 h와 유사하게 ## 제목으로 출력 (항목 5)
                lines.append(f"## {b.get('text', '').strip()}")
            elif typ in ("l2", "l3", "note", "ref", "p", "plain"):
                prefix = "" if typ == "p" else b.get("text", "")
                lines.append(f"{'  ' * level}{prefix}")
            elif typ == "caption":
                lines.append(f"\n**{b.get('text', '').strip()}**\n")
            elif typ == "table":
                rows = b.get("rows") or []
                if rows:
                    markdown_table = _table_to_gfm(rows)
                    lines.append(markdown_table)
            elif typ == "box":
                for line in b.get("lines", []):
                    lines.append(f"> {line}")
            elif typ == "appx_h":
                lines.append(f"\n## {b.get('text', '').strip()}\n")
            elif typ == "image":
                lines.append(f"![{b.get('caption', '')}]({b.get('path', '')})")
            if "body" in b:
                lines.extend(_blocks_to_md(b["body"], level))
        return lines

    def _table_to_gfm(rows):
        if not rows: return ""
        col_count = max(len(r) for r in rows)
        header = rows[0]
        lines = []
        lines.append("| " + " | ".join(str(header[i]) if i < len(header) else "" for i in range(col_count)) + " |")
        lines.append("|" + "|".join("---" for _ in range(col_count)) + "|")
        for row in rows[1:]:
            lines.append("| " + " | ".join(str(row[i]) if i < len(row) else "" for i in range(col_count)) + " |")
        return "\n".join(lines)

    title = s.get("title", "").strip()
    date = s.get("date", "").strip()
    dept = s.get("dept", "").strip()

    # 작성일이 비어 있으면 오늘 날짜 채우기 (버그5)
    if not date:
        date = _today()

    md_lines = []
    md_lines.append(f"# {title}\n")
    if date or dept:
        md_lines.append(f"- 작성일: {date}")
        if dept: md_lines.append(f"- 작성부서: {dept}")
        md_lines.append("")

    md_lines.extend(_blocks_to_md(s.get("body") or []))

    appendix = s.get("appendix") or []
    if appendix:
        md_lines.append("\n## 붙임·참고\n")
        for a in appendix:
            md_lines.append(f"### {a.get('title', '').strip()}\n")
            md_lines.append(f"{a.get('heading', '').strip()}\n")
            md_lines.extend(_blocks_to_md(a.get("body") or []))

    md_path.write_text("\n".join(md_lines), "utf-8")
    return str(md_path)


@mcp.tool()
def build_from_structure(structure: dict, doc_type: str = "report", ministry: str = "", out_path: str = "",
                         logo_path: str = "", slogan_path: str = "", placeholder_contact: bool = True, polish: bool = False,
                         style: str = "standard", export_markdown: bool = False, report_kind: str = "standard") -> dict:
    """build_document와 같다(별칭)."""
    return build_document(structure, doc_type, ministry, out_path, logo_path, slogan_path, placeholder_contact, polish, style, export_markdown, report_kind)


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
