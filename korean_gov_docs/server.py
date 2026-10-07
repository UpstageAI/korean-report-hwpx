"""korean-gov-docs — 한국 공문서(보고서·보도자료) 기관 서식 HWPX 생성 MCP 서버. 작성 Mia(윤승미)

원고를 공무원 공문서 양식 HWPX로 만든다. 서식은 정책브리핑 보도자료 2,670건 전수 조사로 정한 규칙값으로 직접 그린다.
- 보고서(개조식): rules_report/(참고·붙임 구간 1,326건, 기관 42곳 + 공통) — refs/보고서_서식_규칙.md
- 보도자료: rules/·templates/(52개 기관) — refs/보도자료_서식_규칙.md
원본 문서·기관 로고는 포함하지 않는다.
도구:
  write_document       — 원고 → Solar로 문서 종류 판단·구조화 → 기관 서식 HWPX (원고가 Solar API로 전송됨)
  build_from_structure — 구조 JSON → 기관 서식 HWPX (외부 전송 없음)
  list_ministries      — 지원 기관과 문서 종류별 지원 여부
  get_rules            — 기관·문서 종류별 서식 규칙값
  make_press_release   — (하위호환) write_document(doc_type='press_release')
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
from hwpx_doc import Hwpx  # noqa: E402
from . import solar  # noqa: E402

DOC_TYPES = ("report", "press_release")
LABEL = {"report": "보고서", "press_release": "보도자료"}

mcp = MCPServer(
    "korean-gov-docs", title="Korean Government Documents (공문서 HWPX — 보고서·보도자료)",
    instructions="사용자가 '공문서처럼 써 줘', '보고서로 만들어 줘', '보도자료로 만들어 줘'처럼 한국 공무원 문서 양식의 HWPX(한글 파일)를 원할 때 쓴다. "
                 "원고가 이미 구조화돼 있거나 민감정보가 있으면 build_from_structure(외부 전송 없음)를 쓴다. "
                 "write_document는 원고를 Solar API로 보내므로 개인정보 등 민감정보가 있으면 쓰지 않는다. "
                 "기관을 말하지 않으면 ministry를 비워 공통 서식으로 만든다. 담당자 예시는 가명(김○○ 사무관, 044-000-0000)으로 쓴다.")


def out_dir():
    d = Path(os.environ.get("KOREAN_GOV_DOCS_OUT_DIR") or os.environ.get("PRESS_RELEASE_OUT_DIR") or Path.home() / "korean-gov-docs")
    d.mkdir(parents=True, exist_ok=True); return d


CLASSIFY = """너는 한국 정부 문서 담당자다. 아래 원고를 어떤 공문서로 만들어야 하는지 판단한다.
- press_release(보도자료): 언론·국민에게 대외 발표·배포하려는 글(기사체, '~했다고 밝혔다', 보도시점·담당자, 인용문 등)
- report(보고서): 내부 보고·계획·검토·현황 정리용 글(추진계획, 검토안, 현황 보고, 회의 결과, 메모·요점 정리 등)
판단이 애매하면 report.
JSON 하나만 출력: {"doc_type": "report" 또는 "press_release", "reason": "판단 근거 한 문장"}

원고:
"""

PROMPT_PRESS = """너는 {org} 보도자료 편집자다. 아래 원고를 정부 보도자료 구조 JSON으로 정리한다.
이 기관의 본문 방식: {style}
규칙:
- 사실·숫자·인용은 바꾸거나 지어내지 않는다. 문장 다듬기·순서 정리만 한다. 날짜는 '2026. 10. 7.(수)', 시각은 '14:00'.
- title: 핵심 한 줄. subtitles: 부제 명사문 1~2개(앞뒤 '-' 없이).
- release: 보도시점(예: '2026. 10. 7.(수) 조간', '배포 즉시'). 없으면 "". distribute: 배포 일시, 없으면 "".
- body 블록 type:
  문단식 기관 → "p"(기사체 문단, 첫 문단은 누가·언제·무엇), 하위 나열이 필요할 때만 "l2"(ㅇ)·"l3"(-)
  □식 기관 → "l1"(□ 대항목, 두괄식 한 문장), "l2"(ㅇ 중항목), "l3"(- 소항목)
  공통 → "note"(* 각주: 바로 위 문단의 *표시 설명), "ref"(※ 참고), "caption"(표 제목, 꺾쇠 없이), "table"(rows: 2차원 배열, 첫 행 머리), "box"(lines: 강조 상자)
- 원고에 표·통계·일정·세부 목록 같은 참고 자료가 있으면 본문 대신 appendix로: [{{"title":"참고 1","heading":"제목","body":[블록...]}}], 본문 문장 끝에 '참고1' 표시
  소제목 "h"는 원고에 소제목이 있을 때만.
  text에는 기호(□ㅇ-*※)를 넣지 않는다. 각주 대상 단어 뒤에는 '*'를 붙인다(위첨자로 처리됨). 강조는 **굵게**.
- 기관장 인용은 마지막 문단으로.
- contact: {{"dept": 부서명, "people": [[구분, 직위, 이름, "(전화)"], ...]}}. 원고에 있으면 본문에서는 뺀다. 원고에 없으면 빈 값.
JSON 하나만 출력: {{"release":"","distribute":"","title":"","subtitles":[],"body":[{{"type":"p","text":""}}],"appendix":[],"contact":{{"dept":"","people":[]}}}}

원고:
"""

PROMPT_REPORT = """너는 {org} 공무원이다. 아래 원고를 개조식 보고서 구조 JSON으로 정리한다.
규칙:
- 사실·숫자·고유명사·일정은 바꾸거나 지어내지 않는다. 원고에 없는 내용(효과 수치, 예산, 기관명 등)을 보태지 않는다.
- title: 보고서 제목 한 줄(예: '○○ 추진계획(안)', '○○ 현황 보고'). date: 원고에 작성일이 있으면 '2026. 10. 7.' 형식, 없으면 "". dept: 작성 부서, 없으면 "".
- body 블록 type:
  "h": 소제목(원고 흐름에 따라 'Ⅰ. 추진 배경', 'Ⅱ. 현황 및 문제점', 'Ⅲ. 추진 방안'처럼 로마 숫자. 짧은 원고면 생략)
  "l1": □ 대항목 — 두괄식 한 문장으로 핵심 결론을 먼저
  "l2": ㅇ 중항목 — □의 근거·세부
  "l3": - 소항목 — ㅇ의 하위 나열
  "note": * 각주(바로 위 문단에서 '*'를 붙인 단어 설명), "ref": ※ 참고·유의 사항
  "caption": 표 제목(꺾쇠 없이), "table": rows 2차원 배열(첫 행 머리) — 예산·일정·현황 수치는 표로
- 문장은 명사형으로 끝낸다(~함, ~임, ~됨, ~ 예정, ~ 필요). '~합니다·~했다' 금지.
- text에는 기호(□ㅇ-*※)를 넣지 않는다. 강조는 **굵게**(꼭 필요할 때만).
- 세부 자료(상세 일정, 사업 개요, 세부 목록)는 appendix로: [{{"title":"붙임 1","heading":"제목","body":[블록...]}}], 본문 해당 문장 끝에 '붙임 1' 표시
JSON 하나만 출력: {{"title":"","date":"","dept":"","body":[{{"type":"l1","text":""}}],"appendix":[]}}

원고:
"""


def _read(path):
    """원고 읽기: HWPX·DOCX·TXT·MD (HWP는 hwp5txt, PDF는 pdftotext가 설치돼 있으면)."""
    import subprocess, zipfile
    p = Path(path).expanduser(); ext = p.suffix.lower()
    if ext == ".hwpx":
        d = Hwpx(p); return "\n".join(t for *_, q in d.paragraphs() if (t := Hwpx.text(q, tables=True).strip()))
    if ext == ".hwp":
        return subprocess.run(["hwp5txt", str(p)], capture_output=True, text=True).stdout
    if ext == ".pdf":
        return subprocess.run(["pdftotext", "-layout", str(p), "-"], capture_output=True, text=True).stdout
    if ext == ".docx":
        x = zipfile.ZipFile(p).read("word/document.xml").decode("utf-8")
        return "\n".join(re.sub(r"<[^>]+>", "", para) for para in re.findall(r"<w:p\b.*?</w:p>", x, re.S))
    return p.read_text("utf-8")


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
def build_from_structure(structure: dict, doc_type: str = "report", ministry: str = "", out_path: str = "",
                         logo_path: str = "", slogan_path: str = "", placeholder_contact: bool = True) -> str:
    """구조 JSON을 기관 서식 HWPX로 만든다(외부 전송 없음). 만든 파일 경로를 돌려준다.
    doc_type='report': {title, date, dept, body, appendix} — body 블록 type: h(소제목)·l1(□)·l2(ㅇ)·l3(-)·note(*)·ref(※)·caption·table(rows)·box(lines).
      ministry를 비우면 공통 서식(기관명 칸 비움).
    doc_type='press_release': {release, distribute, title, subtitles, body, appendix, contact} — ministry 필수.
    logo_path: 기관 로고 그림(선택, 보도자료는 없으면 '기관 로고' 자리표시). slogan_path: 보도자료 슬로건 그림(선택).
    placeholder_contact: 보도자료 담당자가 없으면 '○○과 / 김○○ / 044-000-0000' 자리표시로 채움."""
    t = _norm_type(doc_type)
    if t == "auto": t = "press_release" if ("release" in structure or "contact" in structure or "subtitles" in structure) else "report"
    _check_ministry(ministry, t)
    dst = _dst(ministry, structure.get("title"), out_path, t)
    _build(t, ministry, structure, dst, logo_path, slogan_path, placeholder_contact)
    return str(dst)


@mcp.tool()
def write_document(text: str = "", file_path: str = "", doc_type: str = "auto", ministry: str = "", out_path: str = "",
                   logo_path: str = "", images: list[dict] | None = None, slogan_path: str = "",
                   placeholder_contact: bool = True, polish: bool = False) -> dict:
    """원고(text 또는 .hwpx/.hwp/.pdf/.docx/.txt/.md 파일)를 Solar(solar-pro4)로 공문서 구조로 정리한 뒤 기관 서식 HWPX로 만든다.
    "이 내용 공문서처럼 써 줘", "이 메모를 행안부 보고서로", "보도자료로 만들어 줘" 같은 요청에 쓴다.
    doc_type: 'auto'(기본, Solar가 원고 성격으로 판단 — 대외 발표·배포용이면 보도자료, 내부 보고·계획·검토면 보고서) | 'report' | 'press_release'.
    ministry: 기관 이름(선택). 보고서는 비우면 공통 서식, 보도자료는 필수(auto에서 보도자료로 판단됐는데 기관이 없으면 보고서로 만듦).
    주의: 원고가 Upstage API(api.upstage.ai, 또는 KOREAN_GOV_DOCS_SOLAR_BASE_URL의 내부 Solar)로 전송된다. 개인정보 등 민감정보는 넣지 않는다.
    images(보도자료): [{"path": "사진.jpg", "caption": "설명", "width_mm": 120}] — 본문 끝에 가운데 정렬로 넣음.
    polish: True면 맥 한컴오피스 한글로 실제 줄 배치를 받아 문단별 자간을 다듬음(맥+한글 필요, 수 분 소요).
    돌려주는 값: HWPX 경로, 문서 종류와 판단 근거, 구조 JSON(고쳐서 build_from_structure로 다시 만들 수 있음)."""
    t = _norm_type(doc_type)
    src = text or (_read(file_path) if file_path else "")
    if not src.strip(): raise ValueError("text 또는 file_path 필요")
    if ministry and ministry != "공통" and ministry not in C.ministries(): raise ValueError(f"지원하지 않는 기관: {ministry} (list_ministries 참고)")
    reason = "doc_type 지정"
    if t == "auto":
        j = solar.chat_json(CLASSIFY + src[:6000], max_tokens=300)
        t = j.get("doc_type") if j.get("doc_type") in DOC_TYPES else "report"
        reason = j.get("reason") or ""
        if t == "press_release" and ministry not in C.ministries():
            t = "report"; reason += " (보도자료는 기관 지정이 필요해 보고서로 만듦 — ministry를 주면 보도자료로 만들 수 있음)"
    _check_ministry(ministry, t)
    org = ministry if ministry and ministry != "공통" else ""
    if t == "report":
        doc = solar.chat_json(PROMPT_REPORT.format(org=org or "중앙행정기관") + src)
    else:
        style = "문단식(기호 없는 기사체 문단 위주)" if C.load_rules(ministry).get("style") == "para" else "□식(□→ㅇ→- 개조식)"
        doc = solar.chat_json(PROMPT_PRESS.format(org=ministry, style=style) + src)
        for im in images or []:
            doc.setdefault("body", []).append({"type": "image", "path": str(Path(im["path"]).expanduser()), "width_mm": im.get("width_mm", 120)})
            if im.get("caption"): doc["body"].append({"type": "caption", "text": im["caption"]})
    doc.setdefault("body", [])
    dst = _dst(org, doc.get("title"), out_path, t)
    _build(t, org, doc, dst, logo_path, slogan_path, placeholder_contact, polish)
    dst.with_suffix(".json").write_text(json.dumps(doc, ensure_ascii=False, indent=1), "utf-8")
    return {"hwpx": str(dst), "doc_type": t, "문서종류": LABEL[t], "판단근거": reason,
            "기관": org or "공통(미지정)", "structure": doc}


@mcp.tool()
def make_press_release(ministry: str, text: str = "", file_path: str = "", out_path: str = "",
                       images: list[dict] | None = None, logo_path: str = "", slogan_path: str = "",
                       placeholder_contact: bool = True, polish: bool = False) -> dict:
    """(하위호환) 원고 → Solar로 보도자료 구조화 → 기관 보도자료 서식 HWPX. write_document(doc_type='press_release')와 같다.
    주의: 원고가 Upstage API(또는 내부 Solar)로 전송된다. 개인정보 등 민감정보는 넣지 않는다."""
    return write_document(text=text, file_path=file_path, doc_type="press_release", ministry=ministry, out_path=out_path,
                          logo_path=logo_path, images=images, slogan_path=slogan_path, placeholder_contact=placeholder_contact, polish=polish)


def main():
    import argparse
    p = argparse.ArgumentParser(prog="korean-gov-docs", description="한국 공문서(보고서·보도자료) 기관 서식 HWPX 생성 MCP 서버")
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
