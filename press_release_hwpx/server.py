"""press-release-hwpx — 정부 보도자료 서식 HWPX 생성 MCP 서버. 작성 Mia(윤승미)

원고를 중앙행정기관별 보도자료 서식(HWPX)으로 만든다. 서식은 정책브리핑 보도자료 2,670건 전수 조사로 정한 규칙값
(refs/보도자료_서식_규칙.md, rules/, templates/)으로 직접 그린다. 원본 문서·기관 로고는 포함하지 않는다.
도구:
  list_ministries      — 지원 기관과 본문 방식(문단식/□식)
  get_rules            — 기관 서식 규칙값(계층별 기호·글꼴·크기·빈 줄)
  build_from_structure — 구조 JSON → 기관 서식 HWPX (외부 전송 없음)
  make_press_release   — 원고 → Solar로 구조화 → 기관 서식 HWPX (원고가 Solar API로 전송됨)
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
from hwpx_doc import Hwpx  # noqa: E402
from . import solar  # noqa: E402

mcp = MCPServer(
    "press-release-hwpx", title="Korean Government Press Release (보도자료 서식 HWPX)",
    instructions="정부 보도자료 HWPX를 만들 때 쓴다. 원고가 이미 구조화돼 있으면 build_from_structure(외부 전송 없음)를 먼저 쓴다. "
                 "make_press_release는 원고를 Solar API로 보내므로 개인정보 등 민감정보가 있으면 쓰지 않는다. "
                 "담당자 예시는 가명(김○○ 사무관, 044-000-0000)으로 쓴다.")


def out_dir():
    d = Path(os.environ.get("PRESS_RELEASE_OUT_DIR") or Path.home() / "press-release-hwpx")
    d.mkdir(parents=True, exist_ok=True); return d


PROMPT = """너는 {org} 보도자료 편집자다. 아래 원고를 정부 보도자료 구조 JSON으로 정리한다.
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


def _dst(ministry, title, out_path):
    return Path(out_path).expanduser() if out_path else out_dir() / f"{ministry}_{re.sub(r'[^가-힣A-Za-z0-9]+', '_', title or '보도자료')[:30]}.hwpx"


@mcp.tool()
def list_ministries() -> list[dict]:
    """지원하는 중앙행정기관 목록과 각 기관의 본문 방식(문단식=기사체 문단, □식=□ㅇ- 개조식)."""
    out = []
    for o in C.ministries():
        r = C.load_rules(o); out.append({"기관": o, "본문방식": "문단식" if r.get("style") == "para" else "□식", "실측문단수": r.get("n_paras")})
    return out


@mcp.tool()
def get_rules(ministry: str) -> dict:
    """기관 서식 규칙값: 계층별 기호·기호 앞 공백·글꼴·크기·줄 간격, 계층 사이 빈 줄 크기."""
    if ministry not in C.ministries(): raise ValueError(f"지원하지 않는 기관: {ministry}")
    r = C.load_rules(ministry); r.pop("_base", None); return r


@mcp.tool()
def build_from_structure(ministry: str, structure: dict, out_path: str = "", logo_path: str = "", slogan_path: str = "",
                         placeholder_contact: bool = True) -> str:
    """구조 JSON({release,distribute,title,subtitles,body,appendix,contact})을 기관 보도자료 서식 HWPX로 만든다(외부 전송 없음).
    logo_path: 기관 로고 그림(선택, 없으면 같은 크기의 '기관 로고' 자리표시). slogan_path: 슬로건 그림(선택).
    placeholder_contact: 담당자가 없으면 '○○과 / 김○○ / 044-000-0000' 자리표시로 채움. 만든 파일 경로를 돌려준다."""
    if ministry not in C.ministries(): raise ValueError(f"지원하지 않는 기관: {ministry}")
    dst = _dst(ministry, structure.get("title"), out_path)
    C.compose(ministry, structure, dst, logo_path=logo_path or None, slogan_path=slogan_path or None, placeholder_contact=placeholder_contact)
    return str(dst)


@mcp.tool()
def make_press_release(ministry: str, text: str = "", file_path: str = "", out_path: str = "",
                       images: list[dict] | None = None, logo_path: str = "", slogan_path: str = "",
                       placeholder_contact: bool = True, polish: bool = False) -> dict:
    """원고(text 또는 .hwpx/.hwp/.pdf/.docx/.txt/.md 파일)를 Solar로 보도자료 구조로 정리한 뒤 기관 서식 HWPX로 만든다.
    주의: 원고가 Upstage API(api.upstage.ai, 또는 PRESS_RELEASE_SOLAR_BASE_URL의 내부 Solar)로 전송된다. 개인정보 등 민감정보는 넣지 않는다.
    images: [{"path": "사진.jpg", "caption": "설명", "width_mm": 120}] — 본문 끝(담당 표 앞)에 가운데 정렬로 넣음.
    placeholder_contact: 원고에 담당자가 없으면 담당 표를 '○○과 / 김○○ / 044-000-0000' 자리표시로 채움(기본).
    polish: True면 맥 한컴오피스 한글로 실제 줄 배치를 받아 문단별 자간을 다듬음(맥+한글 필요, 수 분 소요).
    돌려주는 값: 만든 HWPX 경로와 구조 JSON(고쳐서 build_from_structure로 다시 만들 수 있음)."""
    if ministry not in C.ministries(): raise ValueError(f"지원하지 않는 기관: {ministry}")
    src = text or (_read(file_path) if file_path else "")
    if not src.strip(): raise ValueError("text 또는 file_path 필요")
    style = "문단식(기호 없는 기사체 문단 위주)" if C.load_rules(ministry).get("style") == "para" else "□식(□→ㅇ→- 개조식)"
    doc = solar.chat_json(PROMPT.format(org=ministry, style=style) + src)
    doc.setdefault("body", [])
    for im in images or []:
        doc["body"].append({"type": "image", "path": str(Path(im["path"]).expanduser()), "width_mm": im.get("width_mm", 120)})
        if im.get("caption"): doc["body"].append({"type": "caption", "text": im["caption"]})
    dst = _dst(ministry, doc.get("title"), out_path)
    if polish:
        import polish as PL
        PL.polish(ministry, doc, dst, log=lambda m: None, logo_path=logo_path or None, slogan_path=slogan_path or None,
                  placeholder_contact=placeholder_contact)
    else:
        C.compose(ministry, doc, dst, logo_path=logo_path or None, slogan_path=slogan_path or None, placeholder_contact=placeholder_contact)
    dst.with_suffix(".json").write_text(json.dumps(doc, ensure_ascii=False, indent=1), "utf-8")
    return {"hwpx": str(dst), "structure": doc}


def main():
    import argparse
    p = argparse.ArgumentParser(prog="press-release-hwpx", description="정부 보도자료 서식 HWPX 생성 MCP 서버")
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
