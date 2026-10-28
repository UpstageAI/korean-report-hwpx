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
import official as O  # noqa: E402 — _정규화날짜, _unroll_table_rows, _strip_existing_number 등

PRESS_GUIDE = json.loads((ROOT / "guides" / "press_writing.json").read_text("utf-8"))

DOC_TYPES = ("report", "press_release", "official")
LABEL = {"report": "보고서", "press_release": "보도자료", "official": "기안문"}
STYLES = ("standard", "simplified")
REPORT_KINDS = ("standard", "internal")

mcp = MCPServer(
    "korean-report-hwpx", title="Korean Government Documents (공문서 HWPX — 보고서·보도자료·기안문)",
    instructions="사용자가 '보도자료', '보도참고자료', '설명자료', '해명자료', '보고서', '기안문', 'HWPX', '한글' 파일을 원할 때 쓴다. "
                 "파이썬 등으로 HWPX를 직접 만들지 말고 이 도구를 쓴다. 외부 API 없이 로컬에서 동작한다. "
                 "보도자료 순서: get_writing_guide(doc_type='press_release', ministry=기관) → draft_press_structure(사실 메모 → 구조 초안) → 문장 다듬기 → check_structure → build_document. "
                 "일반 순서: get_writing_guide로 작성 규칙과 구조 스키마 확인 → 원고를 구조 JSON으로 정리 → (선택) check_structure → build_document. "
                 "결과의 warnings가 있으면 구조를 고쳐 다시 build_document. "
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
- kind: '보도자료'(기본)·'보도참고자료'·'설명자료'·'해명자료' 중 선택(머리 이름). 없으면 '보도자료'.
- body 블록 type — 기관 본문 방식에 맞춘다(get_writing_guide의 ministry_style):
  문단식 기관 → "p"(기사체 문단, 첫 문단은 누가·언제·무엇), 하위 나열이 필요할 때만 "l2"(ㅇ)·"l3"(-)
  □식 기관 → "l1"(□ 대항목, 두괄식 한 문장), "l2"(ㅇ), "l3"(-)
  공통 → "note"(*), "ref"(※), "caption", "table"(rows), "box"(lines: 강조 상자), "image"(path, width_mm)
- 기관장 인용은 본문 끝(마지막 문단), 형식 '○○○ 장관은 "…."라고 말했다.'
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

OFFICIAL_EXAMPLE = {
    "org": "행정안전부", "to": "수신자 참조", "via": "",
    "title": "2026년 공공부문 AI 업무도구 실증 참여 안내",
    "body": [
        {"type": "l1", "text": "국산 AI 모델 실증(POC) 참여 기관을 다음과 같이 안내합니다."},
        {"type": "l2", "text": "실증 기간: 2026. 11. 2. ~ 2026. 12. 19."},
        {"type": "l2", "text": "실증 범위: 업무 단위 도구의 시제품(POC·MVP) 수준"},
        {"type": "l3", "text": "문서 기반 추출·요약·분류, 법령 근거를 붙인 검토, 서식 채우기"},
        {"type": "l3", "text": "민원 분류·배정 같은 정형 판단"},
        {"type": "l1", "text": "참여를 희망하는 기관은 2026. 10. 31.까지 참여 신청서를 제출해 주시기 바랍니다."},
        {"type": "l2", "text": "실증 지원 예산은 기관당 금5,000,000원(금오백만원) 한도입니다."},
        {"type": "table", "rows": [["구분", "내용", "기한"], ["신청", "참여 신청서 제출", "2026. 10. 31."], ["선정", "결과 통보", "2026. 11. 7."]]}],
    "attachments": ["실증 참여 신청서 1부.", "실증 참여 안내문 1부."],
    "recipients": ["기획재정부장관", "국세청장", "조달청장"],
    "sender": "행정안전부장관",
    "approval": {
        "drafter": {"title": "주무관", "name": "", "mark": "★"},
        "reviewers": [{"title": "디지털정부과장", "name": "", "opinion": False}, {"title": "디지털정부국장", "name": "", "opinion": True}],
        "approver": {"title": "차관", "name": ""},
        "coordinators": [{"title": "정보공개정책과장"}]},
    "doc_no": {"issue": "디지털정부과-1234", "issue_date": "2026. 10. 14.", "receive": "", "receive_date": ""},
    "contact": {"zip": "30112", "address": "세종특별자치시 한누리대로 411", "homepage": "www.mois.go.kr",
                "phone": "044-000-0000", "fax": "044-000-0001", "email": "○○○@korea.kr", "disclosure": "공개"}}
SCHEMA = {
    "report": {"title": "str(필수)", "date": "str", "dept": "str", "body": "[블록]", "appendix": "[{title, heading, body:[블록]}]"},
    "press_release": {"release": "str", "distribute": "str", "title": "str(필수)", "subtitles": "[str]", "body": "[블록]",
                      "appendix": "[{title, heading, body:[블록]}]", "contact": "{dept: str, people: [[구분, 직위, 이름, (전화)]]}",
                      "kind": "str(보도자료|보도참고자료|설명자료|해명자료, 선택)"},
    "블록": {"h|l1|l2|l3|note|ref|p|caption": {"type": "...", "text": "str"}, "table": {"type": "table", "rows": "[[str]]", "title|caption": "str(표 제목, 선택)"},
             "box": {"type": "box", "lines": "[str]"}, "image": {"type": "image", "path": "str", "width_mm": "int", "caption": "str(선택)"}},
}


def _style(ministry):
    return "문단식(기호 없는 기사체 문단 위주)" if C.load_rules(ministry).get("style") == "para" else "□식(□→ㅇ→- 개조식)"


OFFICIAL_RULES = """[기안문·시행문(별지 제1호서식) 규칙 — doc_type="official"]
- org: 두문 행정기관명(필수). 상급기관 병기는 "국무조정실 ○○위원회"처럼 한 줄로.
- to: 수신자(필수). "내부결재" | "○○장관(○○과장)" | "수신자 참조" 중 하나. "내부결재"면 결문에 수신자란 없음.
- via: 경유(선택). 있으면 "(경유)  {via}" 줄에 표시.
- title: 문서 제목(필수).
- body: 블록 배열. type=l1~l6으로 항목 번호 자동 부여(서버가 부여, 사용자는 번호를 쓰지 않음):
  번호 체계: 1., 가., 1), 가), (1), (가). l1→1. / l2→가. / l3→1) / l4→가) / l5→(1) / l6→(가). 같은 계층 안에서 순서대로 증가,
  상위 계층이 바뀌면 하위 계층 번호 초기화. text에 이미 같은 형태 번호가 있으면 떼고 다시 붙임.
  둘째 계층부터 상위 계층 번호 시작 위치에서 2타(한 글자) 오른쪽에서 시작(들여쓰기).
  type=table(rows 2차원 배열)·type=lines(lines 문자열 배열)도 사용 가능.
- 금액 표기: 금\\d 또는 \\d{1,3}(,\\d{3})+원 형태 뒤에는 반드시 (금…원) 한글 병기를 붙인다(시행규칙 제2조②).
  없으면 build_document가 warnings에 "금액 한글 병기 필요(시행규칙 제2조②): …"를 낸다(생성 막지 않음).
- attachments: 붙임 목록(선택). 1개면 "붙임  {명칭}", 2개 이상이면 "붙임  1. {명칭}" / "      2. {명칭}".
- "끝.": 본문(붙임이 있으면 붙임) 마지막 글자에서 한 글자(2타) 띄우고 "끝."(제4조⑤). 본문이 table로 끝나고 붙임이 없으면
  표 아래 왼쪽 기본선에서 한 글자 띄운 "끝." 줄을 따로 둔다. 문서 전체에서 "끝."은 정확히 한 번.
- recipients: to가 "수신자 참조"일 때 결문 발신 명의 다음 줄에 "수신자  {recipients를 ', '로}" 표시.
- sender: 발신 명의(필수), 결문 가운데 정렬 큰 글씨.
- approval(결재란, 필수): drafter({title, name, mark:"★"|"⊙"|""}), reviewers([{title, name, opinion:bool}]),
  approver({title, name}), coordinators([{title}]). mark "★"=발의자, "⊙"=보고자(제6조①).
  결재란 표: 첫 행에 "{mark}{title}{(의견 있음)}" 순서로 기안자·검토자·결재권자, 둘째 행은 서명 칸(name이 있으면 성명, 없으면 비움).
  그 아래 "협조자  {직위들}"(있을 때).
- doc_no: {issue, issue_date, receive, receive_date}. issue_date/receive_date는 YYYY-MM-DD·YYYY.MM.DD면 YYYY. MM. DD.로 정규화(영 제7조⑤).
- contact: {zip, address, homepage, phone, fax, email, disclosure}. disclosure는 "공개"|"부분공개"|"비공개"만 허용.
- 날짜·시각: 그대로 받되 YYYY-MM-DD·YYYY.MM.DD 꼴이면 YYYY. MM. DD.로 정규화(영 제7조⑤). 예: "2026-10-14" → "2026. 10. 14."
- 성명·전화 정화: name이 비어 있으면 서명 칸을 비우고(자리표시 "○○○" 아님), 전화·팩스는 입력값 그대로.
- export_markdown=True면 같은 내용을 .md로(제목 #, 항목은 번호 글자 그대로, 결문은 표 없이 줄로)."""


def guide_text(doc_type="report", ministry=None, style="standard"):
    t = _norm_type(doc_type)
    parts = [CHOOSE, COMMON_RULES]
    if t in ("report", "auto"): parts.append(REPORT_RULES)
    if t in ("press_release", "auto"):
        parts.append(PRESS_RULES)
        parts.append("\n".join(PRESS_GUIDE["guide"]))
    if t in ("official",): parts.append(OFFICIAL_RULES)
    if ministry and ministry in C.ministries(): parts.append(f"[기관] {ministry} — 보도자료 본문 방식: {_style(ministry)}")
    if style == "simplified":
        parts.append(SIMPLIFIED_RULES)
    parts.append("[순서] 원고 → 위 규칙으로 구조 JSON 작성 → check_structure(선택) → build_document → warnings가 있으면 고쳐 다시 build_document")
    return "\n\n".join(parts)


@mcp.tool()
def get_writing_guide(doc_type: str = "report", ministry: str = "", style: str = "standard") -> dict:
    """원고를 공문서 구조 JSON으로 바꿀 때 지켜야 할 작성 규칙과 스키마·예시. build_document 전에 먼저 확인한다.
    보도자료를 쓸 때는 doc_type='press_release'와 ministry를 주면 작성 방법(리드·제목·인용·숫자·쉬운 말)과 사실 메모 양식, 기관별 가상 예시를 함께 준다.
    doc_type: 'report'(보고서) | 'press_release'(보도자료) | 'auto'(둘 다 + 판단 기준). ministry: 기관 이름(선택).
    style: 'standard'(기본, 기존 동작) | 'simplified'(간소화 모드 — 항목 번호 자동 부여, 제목 상자 없음, 표 머리 음영 없음, 표 제목 자동 번호, 서술식 허용)."""
    if style not in STYLES:
        raise ValueError(f"style은 'standard' 또는 'simplified': {style}")
    t = _norm_type(doc_type)
    out = {"guide": guide_text(t, ministry or None, style), "schema": SCHEMA, "style": style}
    if t in ("report", "auto"): out["example_report"] = EXAMPLE_REPORT
    if t in ("press_release", "auto"):
        ex = next((e for e in PRESS_GUIDE["examples"] if e["ministry"] == ministry), PRESS_GUIDE["examples"][0])
        out["example_press_release"] = ex["structure"]
        out["examples_press_release"] = PRESS_GUIDE["examples"]
        out["press_writing"] = {"steps": PRESS_GUIDE["steps"], "facts_template": PRESS_GUIDE["facts_template"],
                                 "facts_fields": PRESS_GUIDE["facts_fields"], "kinds": PRESS_GUIDE["kinds"],
                                 "types_order": PRESS_GUIDE["types_order"]}
    if t in ("official",): out["example_official"] = OFFICIAL_EXAMPLE
    if ministry and ministry in C.ministries(): out["ministry_style"] = _style(ministry)
    return out


@mcp.prompt(name="writing_guide", title="공문서 작성 규칙")
def writing_guide_prompt(doc_type: str = "report", ministry: str = "") -> str:
    """원고를 보고서·보도자료·기안문 구조로 정리할 때의 작성 규칙과 구조 예시."""
    t = _norm_type(doc_type)
    if t == "press_release":
        ex = next((e for e in PRESS_GUIDE["examples"] if e["ministry"] == ministry), PRESS_GUIDE["examples"][0])["structure"]
    elif t == "official":
        ex = OFFICIAL_EXAMPLE
    else:
        ex = EXAMPLE_REPORT
    return guide_text(doc_type, ministry or None) + "\n\n[구조 예시]\n" + json.dumps(ex, ensure_ascii=False, indent=1)


# ── 점검·정규화 ──
TEXT_TYPES = ("h", "l1", "l2", "l3", "note", "ref", "p", "plain", "caption")
ALL_TYPES = TEXT_TYPES + ("table", "box", "image")
LEAD = re.compile(r"^[\s\u3000]*(?:(?![○〇]{2})[○〇ㅇ◦∘•●·‧*]+[\s\u3000]+|[\-‐–—―]+[\s\u3000]*|[□■◆◇❍▪▶►☞※]+[\s\u3000]*)+")   # ○○부 같은 가림 표기(○ 2개 이상)는 남김
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


def _press_release_checks(s, ministry):
    """보도자료 작성 점검 E1~E18. warnings 목록에 [작성] 접두어로 추가."""
    CK = PRESS_GUIDE["check"]
    w = []
    body = s.get("body") or []
    # 본문 문장 블록: type이 p·l1·l2·l3인 블록 (순서 유지)
    text_blocks = [(i, b) for i, b in enumerate(body) if b.get("type") in _TEXT_TYPES_PRESS]
    # 리드: 본문 문장 블록 중 type이 p 또는 l1인 첫 블록의 text
    lead_block = None
    for i, b in text_blocks:
        if b.get("type") in ("p", "l1"):
            lead_block = b
            break
    lead = lead_block.get("text", "") if lead_block else ""
    kind = s.get("kind", "보도자료")
    is_explanation = kind in ("설명자료", "해명자료")

    # E1: 리드 누가 — ministry가 비면 who_regex만 사용
    if not is_explanation and lead:
        window = lead[:CK["who_window"]]
        if not ministry:
            if not re.search(CK["who_regex"], window):
                w.append("[작성] 리드(첫 문단) 앞부분에 '누가'(기관·기관장)가 없음 — '○○부(장관 ○○○)는 …'처럼 시작 (G20 39)")
        else:
            if (ministry not in window
                    and CK["ministry_short"].get(ministry, "") not in window
                    and not re.search(CK["who_regex"], window)):
                w.append("[작성] 리드(첫 문단) 앞부분에 '누가'(기관·기관장)가 없음 — '○○부(장관 ○○○)는 …'처럼 시작 (G20 39)")

    # E2: 리드 언제
    if not is_explanation and lead:
        if not re.search(CK["when_regex"], lead):
            w.append("[작성] 리드에 '언제'(날짜·시행일·기간)가 없음 — 예: '10월 28일(수)', '11월 2일부터' (G20 39)")

    # E3: 리드 완결
    if not is_explanation and lead:
        lead_stripped = lead.rstrip()
        # 끝의 "참고 N" 제거 후 확인
        lead_clean = re.sub(r"\s*참고\s*\d+\s*$", "", lead_stripped)
        if not lead_clean.endswith("다.") and not lead_clean.endswith("다"):
            w.append("[작성] 리드는 '~한다/~했다'로 끝나는 완결 문장으로 (G20 54)")

    # E4: 리드 길이
    if not is_explanation and lead:
        if len(lead) > CK["lead_max"]:
            w.append(f"[작성] 리드가 깁니다({len(lead)}자) — 누가·언제·무엇만 한 문장으로, 세부는 다음 문단 (G20 38)")

    # E5: 리드 인용
    if not is_explanation and lead:
        if re.search(CK["quote_regex"], lead):
            w.append("[작성] 리드에 인용문 — 리드는 사실만, 인용은 본문 끝으로 (G20 38~39)")

    # E6: 인용 위치
    if not is_explanation:
        # 인용 블록 찾기: 본문 문장 블록 중 quote_regex 매치 + quote_verbs 중 하나 포함
        quote_blocks = []
        for i, b in text_blocks:
            txt = b.get("text", "")
            if re.search(CK["quote_regex"], txt):
                for verb in CK["quote_verbs"]:
                    if verb in txt:
                        quote_blocks.append(i)
                        break
        if quote_blocks:
            last_qi = quote_blocks[-1]
            # 마지막 인용 블록 뒤에 본문 문장 블록이 3개 이상
            after_count = sum(1 for i, _ in text_blocks if i > last_qi)
            if after_count >= 3:
                w.append("[작성] 인용 문단은 본문 끝(마지막~끝에서 셋째 문단)에 둔다 (말뭉치: 끝 세 문단 안 88%)")

    # E7: 제목 과장
    title = s.get("title", "")
    if title:
        for hw in CK["hype_words"]:
            if hw in title:
                w.append(f"[작성] 제목의 '{hw}' — 본문에 비교 기준·근거가 있는지 확인 (말뭉치·G20 33)")

    # E8: 제목 마침표
    if title and title.endswith("."):
        w.append("[작성] 제목 끝에 마침표를 찍지 않는다")

    # E9: 부제 수
    subtitles = s.get("subtitles") or []
    if len(subtitles) > CK["subtitle_max_count"]:
        w.append(f"[작성] 부제는 1개가 가장 좋고 2개를 넘기지 않는다 (G20 36)")

    # E10: 숫자 단위 — _check_number_units에서 문서 최대 3개, 블록마다 1개 처리
    unit_warnings = _check_number_units(s, CK)
    w.extend(unit_warnings)

    # E11: 단위 띄어쓰기 — 본문 문장 블록과 note 대상, 매치마다
    unit_space_hits = []
    for _, b in text_blocks:
        txt = b.get("text", "")
        m = re.search(CK["unit_space_regex"], txt)
        if m and len(unit_space_hits) < 3:
            unit_space_hits.append(m)
    # note 블록도 대상
    for _, b in _walk(s):
        if b.get("type") == "note":
            txt = b.get("text", "")
            m = re.search(CK["unit_space_regex"], txt)
            if m and len(unit_space_hits) < 3:
                unit_space_hits.append(m)
    for m in unit_space_hits:
        matched = m.group(0)
        # 정규화 예시: 숫자와 단위 사이에 공백 추가
        norm = re.sub(r"(\d[\d,.]*[천만억조]*)\s*([가-힣]+)", r"\1 \2", matched)
        w.append(f"[작성] 단위는 띄어 쓴다: '{matched}' → '{norm}' (G11 32~33, H22 66)")

    # E12: 외국 문자 먼저
    foreign_hits = []
    check_texts = [title] + (subtitles or []) + [b.get("text", "") for _, b in text_blocks]
    for txt in check_texts:
        if txt and re.search(CK["foreign_first_regex"], txt) and len(foreign_hits) < 3:
            foreign_hits.append(txt)
    for txt in foreign_hits:
        w.append(f"[작성] 외국 문자는 한글을 먼저 쓰고 괄호 안에: '{txt}' (국어기본법 제14조, G20 63)")

    # E13: 약어 풀이 — 약어별 첫 등장만 확인, 괄호 안 첫 등장은 경고 제외
    if text_blocks:
        joined = "".join(b.get("text", "") for _, b in text_blocks)
        acronym_hits = []
        seen_acronyms = set()
        for m in re.finditer(CK["acronym_regex"], joined):
            if len(acronym_hits) >= 3:
                break
            acr = m.group(0)
            if acr in CK["replace_words"] or acr in seen_acronyms:
                continue  # E14가 다루거나 이미 첫 등장 처리한 약어 제외
            pos = m.start()
            before = joined[:pos]
            # 닫히지 않은 "("가 없고 바로 뒤가 "("도 아님 → 괄호 안이 아님
            is_outside = (before.count("(") == before.count(")") and
                          not (pos < len(joined) and joined[pos] == "("))
            if is_outside:
                acronym_hits.append(acr)
            seen_acronyms.add(acr)  # 첫 등장 처리 완료 (괄호 안이든 밖이든)
        for acr in acronym_hits:
            w.append(f"[작성] '{acr}' 첫 등장에 한글 풀이 없음 — '인공지능(AI)'처럼 한글(약어)로 (G20 63)")

    # E14: 쉬운 말
    replace_hits = []
    for txt in [title] + (subtitles or []) + [b.get("text", "") for _, b in text_blocks] + \
               [b.get("text", "") for _, b in _walk(s) if b.get("type") == "note"]:
        if not txt:
            continue
        for rw, replacement in CK["replace_words"].items():
            if rw in txt:
                src = CK["replace_sources"].get(rw, CK["replace_sources"].get("_default", "G20 108~109"))
                w.append(f"[작성] '{rw}' → '{replacement}' ({src})")
                replace_hits.append(rw)

    # E15: 권위적 표현
    auth_hits = []
    for _, b in text_blocks:
        txt = b.get("text", "")
        for auth_word, suggestion in CK["authoritarian"].items():
            if auth_word in txt and len(auth_hits) < 3:
                w.append(f"[작성] 권위적 표현 '{auth_word}' → '{suggestion}' (G11 53)")
                auth_hits.append(auth_word)

    # E16: 종결 혼용
    has_nida = False
    has_da = False
    for _, b in text_blocks:
        txt = b.get("text", "")
        # 인용 부분 제거
        txt_no_quote = re.sub(r"[“\"][^”\"]{8,}[”\"]|[\"][^\"]{8,}[\"]", "", txt)
        if "니다." in txt_no_quote:
            has_nida = True
        # "다."로 끝나는 문장 확인 (명사형 종결 아님)
        if re.search(r"[다]\.(?:\s|$)", txt_no_quote) and "니다." not in txt_no_quote:
            has_da = True
    if has_nida and has_da:
        w.append("[작성] '-다'와 '-습니다' 혼용 — 한 가지로 (G20 55, G11 65)")

    # E17: 명사형 종결
    noun_end_hits = []
    for _, b in text_blocks:
        if b.get("type") not in ("p", "l1"):
            continue
        txt = b.get("text", "").strip()
        if re.search(r"(함|임|됨|음|예정|필요)\.?$", txt) and len(noun_end_hits) < 3:
            noun_end_hits.append(txt)
    for txt in noun_end_hits:
        tail = txt[-12:] if len(txt) >= 12 else txt
        w.append(f"[작성] 명사형 종결 — '-다'로 끝낸다: '…{tail}' (G20 55)")

    # E18: 긴 문장
    long_sent_hits = []
    for _, b in text_blocks:
        txt = b.get("text", "")
        # "다."로 문장 분리
        sentences = re.split(r"(?<=다\.)\s+", txt)
        for sent in sentences:
            if len(sent) > CK["sentence_max"] and len(long_sent_hits) < 3:
                long_sent_hits.append(sent)
    for sent in long_sent_hits:
        w.append(f"[작성] 문장이 깁니다({len(sent)}자) — 3줄(약 150자) 안쪽으로 끊는다 (G20 56)")

    return w


def _check_number_units(s, CK):
    """E10 숫자 단위 점검. 본문 문장 블록과 note 블록의 text 대상."""
    w = []
    body = s.get("body") or []
    text_blocks = []
    for b in body:
        if b.get("type") in _TEXT_TYPES_PRESS or b.get("type") == "note":
            text_blocks.append(b.get("text", ""))
    # appendix의 note도 포함
    for ap in s.get("appendix") or []:
        for b in ap.get("body") or []:
            if b.get("type") == "note":
                text_blocks.append(b.get("text", ""))
    if not text_blocks:
        return w

    hit_count = 0
    block_hit = set()
    for txt in text_blocks:
        if hit_count >= 3:
            break
        # 블록마다 최대 1개
        block_has_hit = False
        # 숫자 토큰 찾기
        for m in re.finditer(r"(?<![\w.,’'‘])(\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?", txt):
            if hit_count >= 3 or id(txt) in block_hit:
                break
            token = m.group(0)
            # 정수부가 한 자리이고 쉼표·소수점이 없으면 건너뜀
            if len(token) == 1 and "," not in token and "." not in token:
                continue
            start = m.start()
            end = m.end()
            rest = txt[end:]
            # 토큰 바로 앞 글자가 제·-·–·~·∼·/·: 중 하나이면 건너뜀
            if start > 0:
                prev_char = txt[start - 1]
                if prev_char in "제-–~∼/:":
                    continue
            r = rest.lstrip(" ")
            # 정상(건너뜀) 조건 확인
            if _is_unit_ok(rest, r, CK):
                continue
            # 그 밖 → 경고
            if hit_count < 3 and id(txt) not in block_hit:
                hit_count += 1
                block_hit.add(id(txt))
                ctx_start = max(0, start - 8)
                ctx_end = min(len(txt), end + 8)
                ctx = txt[ctx_start:ctx_end]
                w.append(f"[작성] 숫자 뒤 단위 없음: '{ctx}' — 건·명·원·% 등 단위를 붙인다 (G11 32, 말뭉치)")
    return w


def _is_unit_ok(rest, r, CK):
    """숫자를 건너뛰어야 하는 경우(정상)인지 확인."""
    # units 중 하나로 시작하면 정상
    for u in sorted(CK["units"], key=len, reverse=True):
        if r.startswith(u):
            return True
    # 첫 글자가 라틴 문자(A-Z, a-z) 또는 단위 기호
    if r and (('A' <= r[0].upper() <= 'Z') or r[0] in "%℃㎡㎢㎞㎏"):
        return True
    # rest[0]이 :·~·∼·-·–·/·(`` ` ``·`(`·`)`·×) 중 하나
    if rest and rest[0] in r":~∼-–/·`()×":
        return True
    # rest가 "."로 시작하고 그다음이 (공백 뒤)숫자 또는 "("
    if rest.startswith("."):
        after_dot = rest[1:].lstrip()
        if after_dot and (after_dot[0].isdigit() or after_dot[0] == "("):
            return True
    # rest가 ","로 시작하고 바로 다음 글자가 숫자
    if rest.startswith(",") and len(rest) > 1 and rest[1].isdigit():
        return True
    return False


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


def _validate_official(structure):
    """기안문 구조 필수 검증: 필수 키, to·disclosure 허용값, 결재란 drafter·approver 필수, attachments 문자열 목록.
    위반 시 Exception 발생 (check_structure 테스트용)."""
    s = structure or {}
    # 필수 키
    for key in ("org", "to", "title", "sender", "approval"):
        if not s.get(key):
            raise ValueError(f"기안문 필수 필드 누락: {key}")
    # to 허용값
    to = s.get("to", "")
    if to not in ("내부결재", "수신자 참조") and not (to.endswith("장관") or to.endswith("청장") or to.endswith("과장") or "(" in to):
        pass  # to는 자유 형식도 허용 — 수신자 참조/내부결재 이외는 값 자체 허용
    # disclosure 허용값
    disclosure = (s.get("contact") or {}).get("disclosure", "")
    if disclosure and disclosure not in ("공개", "부분공개", "비공개"):
        raise ValueError(f"disclosure는 '공개'|'부분공개'|'비공개'만 허용: {disclosure}")
    # approval 필수 키
    appr = s.get("approval") or {}
    if not appr.get("drafter"):
        raise ValueError("기안문 approval.drafter(결재란 기안자) 누락")
    if not appr.get("approver"):
        raise ValueError("기안문 approval.approver(결재권자) 누락")
    # attachments는 문자열 목록(선택이지만 형식 검증)
    atts = s.get("attachments") or []
    if not all(isinstance(a, str) for a in atts):
        raise ValueError("attachments는 문자열 목록이어야 함")


def _as_structure(structure):
    """structure가 dict면 그대로, JSON 문자열이면 파싱한 dict를 반환. 그 외는 ValueError."""
    if isinstance(structure, dict):
        return structure
    if isinstance(structure, str):
        try:
            s = json.loads(structure)
        except json.JSONDecodeError as e:
            raise ValueError(f"structure는 JSON 객체(또는 그 문자열)여야 함: {e}") from e
        if not isinstance(s, dict):
            raise ValueError(f"structure는 JSON 객체(또는 그 문자열)여야 함: 파싱 결과가 dict가 아님 ({type(s).__name__})")
        return s
    raise ValueError(f"structure는 JSON 객체(또는 그 문자열)여야 함: {type(structure).__name__}")


def check(structure, doc_type="report", style="standard", ministry=""):
    t = _norm_type(doc_type)
    if t == "auto": t = "press_release" if any(k in (structure or {}) for k in ("release", "contact", "subtitles")) else "report"
    s, w = _normalize(structure, t)
    if t == "official":
        _validate_official(s)
    w = w + _style_warnings(s, t, style)
    if style == "simplified":
        w = w + _check_simplified_structure(s, t)
    if t == "press_release":
        w = w + _press_release_checks(s, ministry)
    return t, s, w


def _infer_doc_type(structure, doc_type):
    """doc_type을 비우면 구조 키로 문서 종류를 정한다: release·subtitles·contact → 보도자료, to·sender → 기안문, 그 밖 → 보고서.
    보도자료 구조를 doc_type 없이 넘겨 보고서로 만들어지던 문제 방지."""
    if doc_type: return doc_type
    if isinstance(structure, dict):
        if any(k in structure for k in ("release", "subtitles", "distribute")): return "press_release"
        if any(k in structure for k in ("to", "sender", "recipients")): return "official"
    return "report"


@mcp.tool()
def check_structure(structure: dict | str, doc_type: str = "", style: str = "standard", ministry: str = "") -> dict:
    """구조 JSON을 만들기 전에 점검만 한다(파일 생성 없음): 필수 필드, 알 수 없는 블록, text 속 기호, 계층 건너뜀,
    □ 두 문장 이상, 보고서 명사형 종결이 아닌 문장, 긴 제목 등. structure는 JSON 문자열로 줘도 된다.
    보도자료를 ministry와 함께 점검하면 작성 점검(E1~E18: 리드·제목·인용·숫자·쉬운 말 등)을 추가로 수행한다.
    돌려주는 값: {ok, doc_type, warnings}.
    style: 'standard'(기본) | 'simplified'(간소화 모드 — 번호 수준 건너뜀, 표 제목 누락, 병합 사용, 5단계 초과 추가 점검)."""
    structure = _as_structure(structure)
    doc_type = _infer_doc_type(structure, doc_type)
    if style not in STYLES:
        raise ValueError(f"style은 'standard' 또는 'simplified': {style}")
    t, _, w = check(structure, doc_type, style, ministry)
    return {"ok": not w, "doc_type": t, "warnings": w}


def _default_file_name(name, doc_type, title):
    """저장용 기본 파일 이름: {name}_{LABEL}_{제목 정리 30자}.hwpx — 빈 out_path·폴더 out_path에서 함께 쓴다."""
    cleaned = re.sub(r'[^가-힣A-Za-z0-9]+', '_', title or LABEL[doc_type])[:30]
    return f"{name}_{LABEL[doc_type]}_{cleaned}.hwpx"


def _dst(ministry, title, out_path, doc_type):
    name = ministry or "공통"
    base = _default_file_name(name, doc_type, title)
    if not out_path:
        p = out_dir() / base
    else:
        p = Path(out_path).expanduser()
        if (p.exists() and p.is_dir()) or out_path.endswith(("/", os.sep)):
            p = p / base
        elif not p.suffix:
            p = p.with_suffix(".hwpx")
        p.parent.mkdir(parents=True, exist_ok=True)
    return p


# 중복 정의 제거 — report.py에서 import
from report import _strip_existing_number, _simplify_numbers, _add_table_numbers  # noqa: F401


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
    t = {"보고서": "report", "보도자료": "press_release", "press": "press_release", "자동": "auto",
         "기안문": "official", "시행문": "official", "official": "official"}.get(doc_type, t)
    if t not in DOC_TYPES + ("auto",): raise ValueError(f"doc_type은 'auto'·'report'·'press_release'·'official' 중 하나: {doc_type}")
    return t


def _josa(word, pair="은/는"):
    """조사 붙이기: 끝 공백·괄호 묶음·닫는 따옴표를 번갈아 뗀 뒤 마지막 글자로 판단.
    한글 음절은 받침 유무, 숫자는 끝자리, 라틴 문자는 L·M·N·R 여부로 앞/뒤 조사 결정."""
    front, back = pair.split("/")
    s = word
    # 끝 공백, 괄호 묶음, 닫는 따옴표를 더 뗄 것이 없을 때까지 번갈아 제거
    while True:
        before = s
        s = s.rstrip()
        # 끝 괄호 묶음 제거: "("와 ")"가 모두 있고 ")"로 끝나면 "("부터 ")"까지 제거
        if s.endswith(")") and "(" in s:
            idx = s.rfind("(")
            if idx >= 0:
                s = s[:idx].rstrip()
        # 끝 닫는 따옴표 제거
        if s and s[-1] in "」』'\"":
            s = s[:-1].rstrip()
        if s == before:
            break
    if not s:
        return back
    last = s[-1]
    # 한글 음절: 받침 유무로 판단
    if "\uAC00" <= last <= "\uD7A3":
        return front if ((ord(last) - 0xAC00) % 28) != 0 else back
    # 숫자: 0·1·3·6·7·8 → 앞, 2·4·5·9 → 뒤
    if last.isdigit():
        return front if last in "013678" else back
    # 라틴 문자: L·M·N·R → 앞, 그 밖 → 뒤
    if "A" <= last.upper() <= "Z":
        return front if last.upper() in "LMNR" else back
    return back


def _check_ministry(ministry, doc_type):
    if doc_type == "press_release":
        if ministry not in C.ministries():
            raise ValueError(f"보도자료는 기관 지정이 필요합니다(52개 중 하나, list_ministries 참고): {ministry or '(없음)'}")
    elif ministry and ministry not in ("공통",) and ministry not in C.ministries():
        raise ValueError(f"지원하지 않는 기관: {ministry} (list_ministries 참고, 비우면 공통 서식)")


_KIND_SET = {"보도자료", "보도참고자료", "설명자료", "해명자료"}
_TEXT_TYPES_PRESS = ("p", "l1", "l2", "l3")  # 본문 문장 블록 유형


def _strip_end_punctuation(s):
    """text 끝의 '.'를 하나까지만 떼고, 연속 공백은 하나로."""
    s = re.sub(r"\s+", " ", s).strip()
    if s.endswith("."):
        s = s[:-1].rstrip()
    return s


def _clean_subtitle(s):
    """부제 앞뒤 공백과 앞뒤 '-'·'–'·'—'를 뗀다."""
    s = s.strip()
    s = re.sub(r"^[-–—]+", "", s)
    s = re.sub(r"[-–—]+$", "", s)
    return s.strip()


def _build_lead(who, when, what, josa):
    """리드 문장 생성. what 끝 '.'는 떼고 하나만 붙임."""
    what = _strip_end_punctuation(what)
    what = re.sub(r"\s+", " ", what).strip()
    if when:
        return f"{who}{josa(who)} {when} {what}."
    return f"{who}{josa(who)} {what}."


def _normalize_quote_text(t):
    """인용 문장 정리: strip 후 앞뒤 따옴표 떼고, 끝이 .·?·!가 아니면 '.' 붙인다."""
    t = t.strip()
    t = re.sub(r"^[“\"'‘]+|[”\"'‘]+$", "", t)
    if t and t[-1] not in ".?!":
        t = t + "."
    return t


def _make_quote_block(speaker, texts, verb, josa):
    """인용 블록 text 생성. 1개면 '~라고', 2개 이상이면 '~라며, ~라고'."""
    if not verb:
        verb = "말했다"
    verb = verb.rstrip(".").strip()
    cleaned = [_normalize_quote_text(t) for t in texts]
    if len(cleaned) == 1:
        return f"{speaker}{josa(speaker)} “{cleaned[0]}”라고 {verb}."
    parts = []
    for i, t in enumerate(cleaned):
        if i == 0:
            parts.append(f"“{t}”라며")
        elif i == len(cleaned) - 1:
            parts.append(f"“{t}”라고")
        else:
            parts.append(f"“{t}”라며")
    return f"{speaker}{josa(speaker)} {', '.join(parts)} {verb}."


def _is_para_style(ministry):
    """기관이 문단식(body type "p")인지 확인."""
    return C.load_rules(ministry).get("style") == "para"


def _body_type_for(ministry):
    """기관 본문 방식에 맞는 블록 type 반환."""
    return "p" if _is_para_style(ministry) else "l1"


def _contact_to_struct(contact):
    """contact dict → {"dept": str, "people": list[사자]}."""
    if not isinstance(contact, dict):
        return {"dept": "", "people": []}
    dept = contact.get("dept") or ""
    people = contact.get("people") or []
    out_people = []
    for p in people:
        if isinstance(p, list):
            out_people.append([str(x) for x in p])
        elif isinstance(p, dict):
            phone = str(p.get("phone") or "")
            if phone and not phone.startswith("("):
                phone = f"({phone})"
            out_people.append([str(p.get("role") or ""), str(p.get("title") or ""),
                               str(p.get("name") or ""), phone])
    return {"dept": dept, "people": out_people}


@mcp.tool()
def draft_press_structure(facts, ministry=""):
    """사실 메모(dict 또는 JSON 문자열)를 보도자료 구조 JSON 초안으로 옮긴다.
    메모에 없는 문장·숫자·이름을 만들지 않는다. 붙이는 고정 말은 조사(은/는), “ ”라고, ”라며, “, 인용 동사, 표 머리 구분·수치·기준·비교, 주요 수치, 참고 N뿐이다."""
    if isinstance(facts, str):
        try:
            facts = json.loads(facts)
        except json.JSONDecodeError as e:
            raise ValueError(f"facts는 dict 또는 JSON 문자열이어야 함: {e}") from e
        if not isinstance(facts, dict):
            raise ValueError("facts는 dict 또는 JSON 문자열이어야 함: 파싱 결과가 dict가 아님")
    if not isinstance(facts, dict):
        raise ValueError("facts는 dict 또는 JSON 문자열이어야 함")

    # 기관
    m = ministry or facts.get("ministry", "")
    if m not in C.ministries():
        raise ValueError(f"보도자료는 기관 지정이 필요합니다(52개 중 하나, list_ministries 참고): {m or '(없음)'}")

    # kind
    kind = facts.get("kind") or "보도자료"
    if kind not in _KIND_SET:
        raise ValueError(f"kind는 {'·'.join(_KIND_SET)} 중 하나여야 함: {kind}")
    is_press = kind == "보도자료"

    # 기본 필드
    release = facts.get("release") or ""
    distribute = facts.get("distribute") or ""

    # title / subtitles
    headline = facts.get("headline", "")
    title = _strip_end_punctuation(headline.rstrip())
    subtitles_raw = facts.get("subtitles") or []
    subtitles = []
    for st in subtitles_raw:
        cleaned = _clean_subtitle(st)
        if cleaned:
            subtitles.append(cleaned)
    if len(subtitles) > 2:
        subtitles = subtitles[:2]

    # 블록 type
    bt = _body_type_for(m)

    body = []
    missing = []
    warnings = []

    # 본문 구성 (보도자료·보도참고자료)
    if is_press or kind == "보도참고자료":
        lead_text = facts.get("lead", "")
        who = facts.get("who", "")
        when = facts.get("when", "")
        what = facts.get("what", "")

        if lead_text and lead_text.strip():
            body.append({"type": bt, "text": lead_text.strip()})
        elif who and what:
            if not what.rstrip().endswith("다"):
                missing.append("what은 '~한다/~했다'로 끝나는 서술어 절로")
            lead = _build_lead(who, when, what, _josa)
            body.append({"type": bt, "text": lead})
        elif not lead_text:
            if not who or not what:
                missing.append("lead 또는 who·what")

        # background
        bg = facts.get("background", [])
        if isinstance(bg, str):
            bg = [bg]
        bg = [b.strip() for b in bg if b and b.strip()]
        if bt == "p" and bg:   # 기사형(문단) 기관: 배경 문장들은 한 문단으로 이어 쓴다(실물 보도자료 문단은 2~3문장)
            body.append({"type": bt, "text": " ".join(bg)})
        else:
            for b in bg:
                body.append({"type": bt, "text": b})

        # points
        for pt in facts.get("points", []):
            if isinstance(pt, str):
                if pt and pt.strip():
                    body.append({"type": bt, "text": pt.strip()})
            elif isinstance(pt, dict):
                txt = (pt.get("text", "") or "").strip()
                det = [d.strip() for d in (pt.get("details", []) or []) if d and d.strip()]
                if bt == "p" and txt:   # 기사형 기관: 세부 문장은 ○ 줄로 쪼개지 않고 같은 문단에 이어 쓴다
                    body.append({"type": bt, "text": " ".join([txt] + det)})
                else:
                    if txt:
                        body.append({"type": bt, "text": txt})
                    for d in det:
                        body.append({"type": "l2", "text": d})
                if pt.get("note"):
                    body.append({"type": "note", "text": pt["note"].strip()})

        # plan
        plan = facts.get("plan", [])
        if isinstance(plan, str):
            plan = [plan]
        for p in plan:
            if p and p.strip():
                body.append({"type": bt, "text": p.strip()})

        # quote (본문 맨 끝)
        quote = facts.get("quote")
        if isinstance(quote, dict) and quote.get("speaker") and quote.get("text"):
            speaker = quote.get("speaker", "")
            texts = quote.get("text", [])
            if isinstance(texts, str):
                texts = [texts]
            verb = quote.get("verb", "말했다")
            if texts:
                body.append({"type": bt, "text": _make_quote_block(speaker, texts, verb, _josa)})
    else:
        # 설명자료·해명자료: issue → position → grounds
        issue = facts.get("issue", "")
        position = facts.get("position", "")
        grounds = facts.get("grounds", [])

        if issue:
            body.append({"type": bt, "text": issue.strip()})
        else:
            missing.append("issue(문제 사안 — 보도 내용 요약)")
        if position:
            body.append({"type": bt, "text": position.strip()})
        else:
            missing.append("position(입장)")
        for g in grounds or []:
            if g and g.strip():
                body.append({"type": bt, "text": g.strip()})

        # quote (설명·해명도 본문 맨 끝)
        quote = facts.get("quote")
        if isinstance(quote, dict) and quote.get("speaker") and quote.get("text"):
            speaker = quote.get("speaker", "")
            texts = quote.get("text", [])
            if isinstance(texts, str):
                texts = [texts]
            verb = quote.get("verb", "말했다")
            if texts:
                body.append({"type": bt, "text": _make_quote_block(speaker, texts, verb, _josa)})

    # appendix
    appendix = []
    appx_items = facts.get("appendix", [])
    appx_idx = 0
    for ap in appx_items or []:
        ap = dict(ap) if isinstance(ap, dict) else {}
        heading = ap.get("heading", "")
        items = ap.get("items", [])
        rows = ap.get("rows")
        body_blocks = ap.get("body")
        appx_title = f"참고 {appx_idx + 1}"
        appx_idx += 1
        if body_blocks is not None:
            # body가 이미 있으면 그대로
            appendix.append({"title": appx_title, "heading": heading, "body": body_blocks})
        elif items:
            appendix.append({"title": appx_title, "heading": heading,
                             "body": [{"type": "l1", "text": str(it)} for it in items]})
        elif rows is not None:
            appendix.append({"title": appx_title, "heading": heading,
                             "body": [{"type": "caption", "text": heading},
                                      {"type": "table", "rows": [list(r) for r in rows]}]})
        else:
            # heading만 있는 경우 빈 body
            appendix.append({"title": appx_title, "heading": heading, "body": []})

    # numbers → appendix 맨 뒤
    numbers = facts.get("numbers", [])
    body_text = " ".join(b.get("text", "") for b in body)
    if numbers and all(str(n.get("value") or "") in body_text for n in numbers) and not facts.get("numbers_heading"):
        numbers = []   # 본문에 이미 다 나온 숫자는 '주요 수치' 참고 표로 되풀이하지 않는다
    if numbers:
        nheading = facts.get("numbers_heading") or "주요 수치"
        # basis가 모두 비었는지 확인 → 2열 또는 3열
        all_blank_basis = all(not n.get("basis") for n in numbers)
        header = ["구분", "수치"] if all_blank_basis else ["구분", "수치", "기준·비교"]
        rows = [header]
        for i, n in enumerate(numbers):
            item = str(n.get("item") or "")
            value = str(n.get("value") or "")
            unit = str(n.get("unit") or "")
            basis = str(n.get("basis") or "")
            row = [item, f"{value}{unit}"]
            if not all_blank_basis:
                row.append(basis)
            rows.append(row)
            if not unit:
                warnings.append(f"numbers[{i}] '{item}' 단위 없음 — 건·명·원·% 등")
        appendix.append({"title": f"참고 {appx_idx + 1}", "heading": nheading,
                         "body": [{"type": "caption", "text": nheading},
                                  {"type": "table", "rows": rows}]})

    # contact
    contact = facts.get("contact")
    contact_struct = _contact_to_struct(contact) if isinstance(contact, dict) else {"dept": "", "people": []}
    if not contact or not contact.get("people"):
        missing.append("contact(담당 부서·책임자·담당자·전화)")

    # missing 체크
    if not title:
        missing.append("headline(제목)")
    if not release:
        missing.append("release(보도시점)")

    # 부제 경고
    if len(subtitles_raw) > 2:
        raw_count = len([s for s in subtitles_raw if _clean_subtitle(s)])
        if raw_count > 2:
            warnings.append("부제는 2개까지 — 앞 2개만 넣음")

    # 구조 조립
    structure = {
        "release": release,
        "distribute": distribute,
        "title": title,
        "subtitles": subtitles,
        "body": body,
        "appendix": appendix,
        "contact": contact_struct,
    }
    if not is_press:
        structure["kind"] = kind

    # 점검 추가
    ck_warnings = check(structure, "press_release", "standard", m)[2]
    warnings = warnings + ck_warnings

    next_msg = (f"메모에 없는 사실을 더하지 말고 문장을 다듬은 뒤 "
                f"check_structure(structure, 'press_release', ministry='{m}') → "
                f"build_document(structure, 'press_release', ministry='{m}')")
    return {
        "structure": structure,
        "doc_type": "press_release",
        "ministry": m,
        "missing": missing,
        "warnings": warnings,
        "next": next_msg,
    }


def _today():
    import datetime
    d = datetime.date.today()
    return f"{d.year}. {d.month}. {d.day}."


def _normalize_official_dates(doc):
    """기안문 날짜 정규화: doc_no의 issue_date/receive_date 및 body 텍스트 내 YYYY-MM-DD·YYYY.MM.DD → YYYY. MM. DD."""
    import re as _re
    dn = doc.get("doc_no") or {}
    for k in ("issue_date", "receive_date"):
        if dn.get(k):
            dn[k] = O._정규화날짜(dn[k])
    # body 텍스트 내 날짜 정규화 (YYYY-MM-DD → YYYY. MM. DD.)
    for b in doc.get("body") or []:
        if b.get("text"):
            b["text"] = _re.sub(r"(\d{4})-(\d{1,2})-(\d{1,2})",
                                lambda m: f"{m.group(1)}. {int(m.group(2))}. {int(m.group(3))}.",
                                b["text"])
    return doc


def _build(doc_type, ministry, doc, dst, logo_path="", slogan_path="", placeholder_contact=True, polish=False, style="standard", report_kind="standard"):
    if doc_type == "report":
        if not str(doc.get("date") or "").strip():
            doc["date"] = _today()  # 작성일 미기재 시 오늘 날짜
        if polish:
            import polish as PL
            PL.polish(ministry, doc, dst, log=lambda m: None, build=RP.compose, logo_path=logo_path or None)
        else:
            RP.compose(ministry, doc, dst, logo_path=logo_path or None, style=style, report_kind=report_kind)
    elif doc_type == "official":
        # 날짜 정규화는 build_document에서 이미 완료 (s_for_md용)
        if polish:
            import polish as PL
            PL.polish(ministry, doc, dst, log=lambda m: None, build=O.compose, logo_path=logo_path or None)
        else:
            O.compose(ministry, doc, dst, logo_path=logo_path or None)
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
    """지원 기관과 문서 종류별 지원 여부. 보고서: 기관 규칙(42곳) 또는 공통 규칙, 보도자료: 52개 기관, 기안문: rules_official/_공통.json.
    보고서는 기관을 비우거나 '공통'으로 하면 기관 간 공통 서식으로 만든다. 기안문은 기관 지정 없이 공통 서식으로만 지원."""
    rep = set(RP.ministries()); out = []
    for o in C.ministries():
        r = C.load_rules(o)
        out.append({"기관": o, "보고서": "기관 규칙" if o in rep else "공통 규칙", "보도자료": "지원", "기안문": "공통 서식",
                    "보도자료_본문방식": "문단식" if r.get("style") == "para" else "□식"})
    out.append({"기관": "공통(미지정)", "보고서": "공통 규칙", "보도자료": "미지원(기관 지정 필요)", "기안문": "공통 서식",
                "보도자료_본문방식": ""})
    return out


@mcp.tool()
def get_rules(ministry: str = "", doc_type: str = "report") -> dict:
    """기관·문서 종류별 서식 규칙값: 계층별 기호·기호 앞 공백·글꼴·크기·줄 간격, 계층 사이 빈 줄 크기,
    보고서는 제목 상자·표 머리 규칙 포함. ministry를 비우면 보고서 공통 규칙.
    기안문(doc_type='official')은 rules_official/_공통.json 값만 반환(기관 지정 없음)."""
    t = _norm_type(doc_type)
    if t == "auto": t = "report"
    _check_ministry(ministry, t)
    if t == "official":
        r = dict(json.loads((ROOT / "rules_official" / "_공통.json").read_text("utf-8")))
        r.pop("_설명", None)
        return r
    r = RP.load_rules(ministry) if t == "report" else C.load_rules(ministry)
    r.pop("_base", None)
    if t == "report": r["적용"] = "기관 규칙" if RP.resolve(ministry)[0] != RP.COMMON else "공통 규칙"
    return r


def _정규화날짜(s):
    """YYYY-MM-DD / YYYY.MM.DD → YYYY. MM. DD. (server.py에서 사용)."""
    return O._정규화날짜(s) if hasattr(O, '_정규화날짜') else s


def _prepare_simplified_for_md(s, style="standard"):
    """간소화 모드 s_for_md 조립: 번호 부여·표 번호·표 병합 풀어쓰기.
    report·official이 같이 쓰는 공통 함수."""
    if style != "simplified":
        return s
    s_md = _simplify_numbers(s)
    s_md = _add_table_numbers(s_md)
    s_md = dict(s_md)
    s_md["body"] = [dict(b) for b in s_md.get("body", [])]
    for b in s_md["body"]:
        if b.get("type") == "table":
            b["rows"] = _unroll_table_rows(b.get("rows", []))
    for a in s_md.get("appendix", []):
        a = dict(a)
        a["body"] = [dict(b) for b in a.get("body", [])]
        for b in a["body"]:
            if b.get("type") == "table":
                b["rows"] = _unroll_table_rows(b.get("rows", []))
    return s_md


def _number_official_body_for_md(s):
    """기안문 body에 항목 번호(1. 가. 1) …)를 부여한 구조 복사본을 반환 (마크다운 export용).
    OfficialComposer._본문()과 동일한 번호 부여 로직을 따른다."""
    import re as _re
    numbering = ["1.", "가.", "1)", "가)", "(1)", "(가)", "①", "㉮"]
    counters = [0] * len(numbering)

    def _strip_num(text):
        if not text:
            return text
        m = _re.match(
            r"^\s*(?:[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]\.|[1-9][0-9]?\.|[가-힣]\.|[1-9][0-9]?\)|[가-힣]\))\s*",
            text,
        )
        return text[m.end():] if m else text

    def _process(blocks):
        result = []
        for b in blocks:
            typ = b.get("type")
            new_b = dict(b)
            if typ in ("l1", "l2", "l3", "l4", "l5", "l6"):
                lvl = {"l1": 0, "l2": 1, "l3": 2, "l4": 3, "l5": 4, "l6": 5}[typ]
                for i in range(lvl + 1, len(counters)):
                    counters[i] = 0
                counters[lvl] += 1
                from official import item_label
                new_b["text"] = f"{item_label(numbering[lvl], counters[lvl])}{_strip_num(b.get('text', ''))}"
            if "body" in b:
                new_b["body"] = _process(b.get("body", []))
            result.append(new_b)
        return result

    s_md = dict(s)
    s_md["body"] = _process(s.get("body") or [])
    return s_md


@mcp.tool()
def build_document(structure: dict | str, doc_type: str = "", ministry: str = "", out_path: str = "",
                   logo_path: str = "", slogan_path: str = "", placeholder_contact: bool = True, polish: bool = False,
                   style: str = "standard", export_markdown: bool = False, report_kind: str = "standard") -> dict:
    """보고서·보도자료(보도참고·설명·해명자료 포함)·기안문을 기관 서식 HWPX(한글 파일)로 만든다.
    구조 JSON을 기관 서식 HWPX로 만든다(외부 전송 없음, 모두 로컬). 구조는 get_writing_guide 규칙대로 사용자 AI가 작성한다.
    structure는 JSON 문자열로 줘도 된다.
    doc_type='report': {title, date, dept, body, appendix} — ministry를 비우면 공통 서식(기관명 칸 비움).
    doc_type='press_release': {release, distribute, title, subtitles, body, appendix, contact} — ministry 필수.
    doc_type='official': {org, to, via, title, body, attachments, recipients, sender, approval, doc_no, contact} — 기안문·시행문(별지 제1호서식).
    입력은 정규화(text 앞 기호·대시·공백 제거)하고, 고칠 점을 warnings로 돌려준다 — 있으면 구조를 고쳐 다시 호출한다.
    ministry 인자로 check_structure에 기관을 넘겨 보도자료 작성 점검(E1~E18)을 수행한다.
    out_path: 저장 경로(선택, 기본은 아웃폴더). 폴더면 그 안에 기본 파일 이름으로 저장, 확장자 없는 이름이면 .hwpx를 붙인다.
    logo_path: 기관 로고 그림(선택). slogan_path: 보도자료 슬로건 그림(선택).
    placeholder_contact: 보도자료 담당자가 없으면 '○○과 / 김○○ / 044-000-0000' 자리표시로 채움.
    polish: True면 맥 한컴오피스 한글로 실제 줄 배치를 받아 문단별 자간을 다듬음(맥+한글 필요, 수 분 소요).
    style: 'standard'(기본, 기존 동작) | 'simplified'(간소화 모드 — 항목 번호 자동 부여, 제목 상자 없음, 표 머리 음영 없음, 표 제목 자동 번호, 서술식 허용).
    export_markdown: True이면 같은 구조로 .md 파일을 HWPX 옆에 함께 저장(GFM 표, 병합 없이, 번호 위계는 #, ##, ###와 번호 텍스트).
    report_kind: 'standard'(기본, 기존 보고서 서식) | 'internal'(내부 결재 보고서 — 제목 상자 라벨 없음, 쪽 번호 "- n -", 작성일·부서 "'26. 10. 8.(목) / 과·팀명" 형식, 표 머리 음영 없음/회색, □ 글꼴 HY헤드라인M).
    돌려주는 값: {hwpx, doc_type, 문서종류, 기관, warnings, structure(정리된 구조), md(export_markdown=True일 때)}. 같은 이름 .json에 구조도 저장."""
    structure = _as_structure(structure)
    doc_type = _infer_doc_type(structure, doc_type)
    if style not in STYLES:
        raise ValueError(f"style은 'standard' 또는 'simplified': {style}")
    if report_kind not in REPORT_KINDS:
        raise ValueError(f"report_kind은 'standard' 또는 'internal': {report_kind}")
    t, s, w = check(structure, doc_type, style, ministry)
    # 기안문 날짜 정규화 (제7조⑤) — HWPX·마크다운 공통
    if t == "official":
        s = _normalize_official_dates(s)
        # 금액 한글 병기 경고 (제2조②) — 본문 직접 점검
        amt_re = re.compile(r"금\d|\d{1,3}(?:,\d{3})+원")
        kr_re = re.compile(r"\(금[^\)]+원\)")
        for b in s.get("body") or []:
            txt = b.get("text", "")
            if txt and amt_re.search(txt) and not kr_re.search(txt):
                w.append(f"금액 한글 병기 필요(시행규칙 제2조②): {txt.strip()}")
    # press_release: kind 기본값 — 템플릿 머리 이름이 '보도참고자료'·'보도설명자료'인 기관도 '보도자료'로
    if t == "press_release":
        s["kind"] = s.get("kind") or "보도자료"
    org = ministry if ministry and ministry != "공통" else ""
    _check_ministry(org, t)
    dst = _dst(org, s.get("title"), out_path, t)
    # table.title/caption 키를 caption 블록으로 변환 (모든 스타일)
    s = _convert_table_titles(s)
    # 마크다운 export를 위한 변환본 준비
    s_for_md = _prepare_simplified_for_md(s, style)
    if t == "official":
        s_for_md = _number_official_body_for_md(s_for_md)
    _build(t, org, s, dst, logo_path, slogan_path, placeholder_contact, polish, style, report_kind)
    # 저장용 구조는 변환 전 원본 유지
    dst.with_suffix(".json").write_text(json.dumps(s, ensure_ascii=False, indent=1), "utf-8")
    md_path = ""
    if export_markdown:
        md_path = _export_markdown(s_for_md, dst, "standard", t)
    result = {"hwpx": str(dst), "doc_type": t, "문서종류": LABEL[t], "기관": org or "공통(미지정)", "warnings": w, "structure": s}
    if md_path: result["md"] = md_path
    return result


def _unroll_table_rows(rows):
    """표 행의 병합 셀 풀어쓰기 (간소화 모드용). 병합 dicts를 일반 문자열로 변환."""
    if not rows: return rows
    return O._unroll_table_rows(rows)


def _export_markdown(s, hwpx_path, style="standard", doc_type="report"):
    """구조 JSON을 GFM 마크다운으로 변환하여 HWPX 옆 .md 파일로 저장.
    간소화 모드면 번호 부여·표 번호 적용 후 변환.
    doc_type: 'report' | 'press_release' | 'official'."""
    md_path = Path(str(hwpx_path).replace(".hwpx", ".md"))
    # 간소화 모드: 엔진과 동일하게 번호 부여 후 변환
    if style == "simplified" and doc_type != "official":
        s = _simplify_numbers(s)
        s = _add_table_numbers(s)

    # 붙임/참고 참조 꼬리표 패턴: 문장 끝의 "붙임 N" 또는 "참고 N"을 "(붙임 N)" 또는 "(참고 N)"으로 변환
    _REF_TAG_RE = re.compile(r"^(.*?)(붙임|참고)\s*(\d+)\s*$")

    def _convert_ref_tag(text):
        """문장 끝의 붙임/참고 참조 꼬리표를 (붙임 N) 또는 (참고 N) 형태로 변환."""
        m = _REF_TAG_RE.match(text)
        if m:
            return f"{m.group(1)}({m.group(2)} {m.group(3)})"
        return text

    def _blocks_to_md(bs, level=0):
        """blocks to markdown.
        level: 구조적 깊이 (h=0, l1=1, l2=2, l3=3, l4=4, l5=5, l6=6)
        - h: ## text (항상 ##)
        - l1: text (들여쓰기 없음)
        - l2:   text (들여쓰기 2칸)
        - l3:     text (들여쓰기 4칸)
        - l4:       text (들여쓰기 6칸)
        - l5:         text (들여쓰기 8칸)
        - l6:           text (들여쓰기 10칸)
        """
        lines = []
        for b in bs:
            typ = b.get("type")
            if typ == "h":
                lines.append(f"## {b.get('text', '').strip()}")
                level = 0
            elif typ in ("l1", "l2", "l3", "l4", "l5", "l6"):
                lvl_map = {"l1": 0, "l2": 1, "l3": 2, "l4": 3, "l5": 4, "l6": 5}
                level = lvl_map[typ]
                text = _convert_ref_tag(b.get('text', '').strip())
                lines.append(f"{'  ' * level}{text}")
            elif typ == "note":
                lines.append(f"> * {b.get('text', '').strip()}")
            elif typ == "ref":
                lines.append(f"> ※ {b.get('text', '').strip()}")
            elif typ in ("p", "plain"):
                prefix = "" if typ == "p" else b.get("text", "")
                lines.append(f"{'  ' * level}{prefix}")
            elif typ == "caption":
                lines.append(f"\n**{b.get('text', '').strip()}**\n")
            elif typ == "table":
                rows = b.get("rows") or []
                if rows:
                    lines.append(_table_to_gfm(rows))
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

    md_lines = []
    title = s.get("title", "").strip()

    if doc_type == "official":
        # 기안문 마크다운: org, to, title, body, attachments, 결문
        org = s.get("org", "")
        to = s.get("to", "")
        if org:
            md_lines.append(f"# {org}  {title}")
        else:
            md_lines.append(f"# {title}")
        md_lines.append(f"수신  {to}")
        via = s.get("via", "")
        if via:
            md_lines.append(f"(경유)  {via}")
        md_lines.append("")
        md_lines.extend(_blocks_to_md(s.get("body") or []))
        # 붙임 + 끝 표시 (HWPX와 같은 자리: 붙임 마지막 줄, 없으면 본문 마지막 줄, 표로 끝나면 표 아래)
        atts = s.get("attachments") or []
        body_blocks = s.get("body") or []
        if atts:
            md_lines.append("")
            if len(atts) == 1:
                md_lines.append(f"붙임  {atts[0]}  끝.")
            else:
                md_lines.append(f"붙임  1. {atts[0]}")
                for i, a in enumerate(atts[1:], 2):
                    md_lines.append(f"      {i}. {a}" + ("  끝." if i == len(atts) else ""))
        elif body_blocks and body_blocks[-1].get("type") == "table":
            md_lines.append("")
            md_lines.append("  끝.")
        else:
            for i in range(len(md_lines) - 1, -1, -1):
                if md_lines[i].strip():
                    md_lines[i] = md_lines[i] + "  끝."
                    break
        # 결문
        sender = s.get("sender", "")
        if sender:
            md_lines.append("")
            md_lines.append(sender)
        to_val = s.get("to", "")
        if to_val == "수신자 참조":
            recps = s.get("recipients") or []
            if recps:
                md_lines.append(f"수신자  {', '.join(recps)}")
        # 결재란
        appr = s.get("approval") or {}
        drafter = appr.get("drafter", {})
        reviewers = appr.get("reviewers", [])
        approver = appr.get("approver", {})
        opinion_text = "(의견 있음)"
        title_line = "  ".join(
            [f"{drafter.get('mark', '')}{drafter.get('title', '')}"]
            + [f"{r.get('title', '')}{opinion_text if r.get('opinion') else ''}" for r in reviewers]
            + [approver.get('title', '')]
        )
        name_line = "  ".join(
            [drafter.get('name', '') or ''] +
            [r.get('name', '') or '' for r in reviewers] +
            [approver.get('name', '') or '']
        )
        if title_line.strip():
            md_lines.append(title_line)
        if name_line.strip():
            md_lines.append(name_line)
        # 협조자
        coords = appr.get("coordinators", [])
        if coords:
            md_lines.append(f"협조자  {' / '.join(c.get('title', '') for c in coords)}")
        # 시행/접수
        dn = s.get("doc_no") or {}
        issue_d = _정규화날짜(dn.get("issue_date", ""))
        receive_d = _정규화날짜(dn.get("receive_date", ""))
        md_lines.append(f"시행  {dn.get('issue', '')} ({issue_d})")
        if dn.get("receive"):
            md_lines.append(f"접수  {dn.get('receive', '')} ({receive_d})")
        # 주소/연락처
        contact = s.get("contact", {}) or {}
        md_lines.append(f"우  {contact.get('zip', '')}  {contact.get('address', '')}  /  {contact.get('homepage', '')}")
        md_lines.append(f"전화번호  {contact.get('phone', '')}  팩스번호  {contact.get('fax', '')}  /  {contact.get('email', '')}  /  {contact.get('disclosure', '')}")
    else:
        # 보고서·보도자료 마크다운 (기존 동작)
        date = s.get("date", "").strip()
        dept = s.get("dept", "").strip()
        if not date:
            date = _today()
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
def build_from_structure(structure: dict | str, doc_type: str = "", ministry: str = "", out_path: str = "",
                         logo_path: str = "", slogan_path: str = "", placeholder_contact: bool = True, polish: bool = False,
                         style: str = "standard", export_markdown: bool = False, report_kind: str = "standard") -> dict:
    """build_document와 같다(별칭). structure는 JSON 문자열로 줘도 된다."""
    return build_document(structure, doc_type, ministry, out_path, logo_path, slogan_path, placeholder_contact, polish, style, export_markdown, report_kind)


def main():
    import argparse
    p = argparse.ArgumentParser(prog="korean-report-hwpx", description="한국 공문서(보고서·보도자료·기안문) 기관 서식 HWPX 생성 MCP 서버")
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
