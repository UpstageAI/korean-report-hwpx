# korean-report-hwpx — Korean Government Documents MCP (reports and press releases as HWPX)

<!-- mcp-name: io.github.UpstageAI/korean-report-hwpx -->

![Demo: one memo → standard and simplified reports (HWPX)](https://raw.githubusercontent.com/UpstageAI/korean-report-hwpx/main/docs/demo.gif)

[![PyPI](https://img.shields.io/pypi/v/korean-report-hwpx)](https://pypi.org/project/korean-report-hwpx/) [![MCP Registry](https://img.shields.io/badge/MCP%20Registry-korean--gov--docs-blue)](https://registry.modelcontextprotocol.io/v0/servers?search=korean-report-hwpx) [![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE) [![Built with Upstage Solar Pro 4](https://img.shields.io/badge/Built%20with-Upstage%20Solar%20Pro%204-7A3FF2)](https://www.upstage.ai/) · [한국어](README.md)

> **Developed with Upstage Solar Pro 4 since 0.2.0.** Simplified mode, Markdown output and internal approval reports were written by Solar Pro 4 and verified by Claude.

**Korean civil-service documents (reports and press releases) as HWPX, in each agency's format.** Your own AI (Claude, ChatGPT, …) structures the memo or draft, and the server draws a Hangul (HWPX) file from format rules for 52 central government agencies.

**Nothing leaves your machine · no API key** — everything runs locally; the draft is never sent anywhere by this server.

> One request — "write this up like an official document" (공문서처럼 써 줘) — produces an outline-style report (□ → ㅇ → -) or a press release in the agency's format. Rules were measured from 2,670 published press releases; no source documents or logos are bundled.

**Try asking**

- "Turn this memo into a report for <agency name>"
- "These are meeting notes — format them as an official document" (no agency given → common format)
- "Make this a National Tax Service (국세청) press release — embargo 2026. 10. 8.(Thu) morning papers"
- "Rebuild the report from before with a new □ sentence in section Ⅲ"
- "Show the report format rules for 산림청 (marks, fonts, sizes per level)"

**One-line install** — `claude mcp add korean-report-hwpx -- uvx korean-report-hwpx`

## Document types

| Type | Layout | Agency | Rules |
|---|---|---|---|
| **Report (개조식 outline)** | Title box, date/department line (optional), section headings (Ⅰ. Ⅱ.) → □ → ㅇ → - → *, ※ notes, tables, attachment pages (붙임·참고) | Optional — 42 agencies have their own rules; others or none use common rules | `rules_report/` (1,326 report-style sections) |
| **Press release (보도자료)** | Cover (logo slot), embargo/distribution, title and subtitles, body (paragraph / □ outline), contact table, appendix pages | Required — 52 agencies | `rules/`, `templates/` (2,670 releases) |
| **Draft approval document / official notice (기안문·시행문, 별지 제1호서식)** | Header (org centered), body with auto-numbered items (1.→가.→1)→가)→(1)→(가)), attachments, "끝." end mark, closing block (sender, recipients, approval table, coordinators, issue/receive, address, contact, disclosure) | Common format (rules_official/_공통.json), no agency needed | `rules_official/_공통.json` (Regulation Art.7, Enforcement Rule Art.2/4/6) |

**Flow** — ask your AI "turn this memo into a <agency name> report" → it reads `get_writing_guide` → writes the structure JSON → calls `build_document` → if `warnings` come back, it fixes the structure and builds again.

Type choice (in the guide): public announcement or distribution → press release; internal reporting, plans or reviews → report; for a draft approval document / official notice (별지 제1호서식) → `official`.

## Install

With [uv](https://docs.astral.sh/uv/) it runs without a separate install.

```json
{
  "mcpServers": {
    "korean-report-hwpx": {
      "command": "uvx",
      "args": ["korean-report-hwpx"]
    }
  }
}
```

Claude Code: `claude mcp add korean-report-hwpx -- uvx korean-report-hwpx`

- No API key or environment variables required.
- Files are written to `~/korean-report-hwpx/` (override with `KOREAN_REPORT_HWPX_OUT_DIR`; the old `KOREAN_GOV_DOCS_OUT_DIR` is also read).

## Tools

| Tool | What it does |
|---|---|
| `get_writing_guide` | Type-choice criteria, writing rules (□ one-sentence conclusion first, ㅇ grounds, - details, noun-form endings, no invented facts/numbers, no marks in text, appendix structure, official doc item numbering/dates/amounts/end mark/attachments), structure JSON schema and examples. Also as MCP prompt `writing_guide` |
| `check_structure` | Pre-build check: required fields, marks in text, skipped levels, multi-sentence □, non-noun-form endings, long titles; for official docs also: required keys, to/disclosure allowed values, approval drafter/approver required, attachments must be string list |
| `build_document` | Structure JSON → agency-format HWPX; normalizes input (strips marks, dashes, leading spaces) and returns `warnings`. `build_from_structure` is an alias. For official docs use `doc_type="official"`; amount Korean annotation warnings and date normalization included |
| `list_ministries` | Supported agencies and support per document type (reports: agency/common rules; press releases: body style; official docs: common format) |
| `get_rules` | Format rules per agency and document type (marks, fonts, sizes, indents, gaps, title box, table header; official docs: rules_official/_공통.json) |
| `draft_press_structure` | Turns a fact memo (who·when·what, background·key points·plan, quote, contact, numbers, etc.) into a press-release structure JSON draft. It does not invent sentences, numbers, or names not in the memo; it places the lead, quote, tables, and appendix per the rules. |

## How to write a press release (National Institute of Korean Language guidelines · Korea.kr measurement)

Call `get_writing_guide(doc_type='press_release', ministry=agency)` to get press-release writing guidance (lead, title, quote, numbers, plain language) plus the fact-memo template and per-agency example structures. The guidance is based on the National Institute of Korean Language's press-release writing guides and a measurement of 2,667 Korea.kr press releases.

**Fact-memo example (과학기술정보통신부, fictitious):**
```json
{
  "kind": "보도자료",
  "ministry": "과학기술정보통신부",
  "release": "2026. 10. 29.(목) 조간",
  "headline": "고영향 인공지능 확인 요청 128건, 평균 21일 만에 처리",
  "subtitles": ["인공지능기본법 시행 9개월 확인제도 운영 결과 발표"],
  "who": "과학기술정보통신부(장관 ○○○)",
  "when": "10월 28일(수)",
  "what": "「인공지능 발전과 신뢰 기반 조성 등에 관한 기본법」 시행 9개월을 맞아 고영향 인공지능 확인제도 운영 결과를 발표했다",
  "points": ["1월 22일부터 10월 21일까지 확인 요청은 모두 128건 접수됐고, 이 가운데 117건을 처리했다."],
  "numbers": [{"item": "확인 요청 접수", "value": "128", "unit": "건", "basis": "2026. 1. 22.~10. 21."}],
  "quote": {"speaker": "○○○ 과학기술정보통신부 장관", "text": ["기업이 예측 가능하게 인공지능을 개발할 수 있도록 확인제도를 빠르고 투명하게 운영하겠다."], "verb": "말했다"},
  "contact": {"dept": "과학기술정보통신부 인공지능신뢰정책과", "people": [["책임자", "과장", "○○○", "(044-202-0000)"]]}
}
```

Then: `draft_press_structure(facts, ministry)` → structure JSON draft + missing/warnings → refine sentences → `check_structure(structure, 'press_release', ministry=agency)` → `build_document(structure, 'press_release', agency)`.

**Sources:**
- National Institute of Korean Language, 『유형별로 알아보는 보도자료 작성 길잡이』 (2020) — G20
- National Institute of Korean Language, 『보도자료 유형별 표준안 개발』 (2020) — R20
- National Institute of Korean Language, 『보도 자료 쓰기 길잡이』 (2011) — G11
- National Institute of Korean Language, 『개정판 한눈에 알아보는 공공언어 바로 쓰기』 (2022) — H22
- Ministry of Culture, Sports and Tourism·National Institute of Korean Language, 『쉬운 공공언어 쓰기 길잡이』 (2014) — E14
- Korea.kr (정책브리핑) press releases, 2,667 documents, body text measurement (52 central agencies) — C

Report structure JSON:

```json
{
  "title": "○○ 서비스 도입 추진계획(안)", "date": "2026. 10. 7.", "dept": "○○과",
  "body": [{"type": "h", "text": "Ⅰ. 추진 배경"},
           {"type": "l1", "text": "..."}, {"type": "l2", "text": "..."}, {"type": "l3", "text": "..."},
           {"type": "note", "text": "..."}, {"type": "ref", "text": "..."},
           {"type": "caption", "text": "소요 예산"}, {"type": "table", "rows": [["구분", "금액"], ["가", "100"]]}],
  "appendix": [{"title": "붙임 1", "heading": "...", "body": [{"type": "l1", "text": "..."}]}]
}
```

Press release structure: `{release, distribute, title, subtitles, body, appendix, contact}` (same block types plus `p` paragraph, `box`, `image`). Without a contact, the contact table is filled with placeholders `○○과 / 김○○ / 044-000-0000` (`placeholder_contact`).

Official document (기안문·시행문, 별지 제1호서식) structure — use `doc_type="official"`:
```json
{
  "org": "행정안전부",            // Header agency name (required). Upper agency combined in one line, e.g. "국무조정실 ○○위원회"
  "to": "수신자 참조",             // Required. "내부결재" | "○○장관(○○과장)" | "수신자 참조"
  "via": "",                       // Via (optional). If present, shown as "(경유)  {via}"
  "title": "2026년 ○○ 계획 알림",  // Required
  "body": [                        // Item numbers (1.→가.→1)→가)→(1)→(가)) assigned by the server
    {"type": "l1", "text": "..."},
    {"type": "l2", "text": "..."},
    {"type": "l3", "text": "..."},
    {"type": "table", "rows": [[...]]},
    {"type": "lines", "lines": ["..."]}
  ],
  "attachments": ["○○ 계획서 1부.", "○○ 명단 1부."],  // Optional
  "recipients": ["○○부장관", "○○청장"],                // Shown in closing when to="수신자 참조"
  "sender": "행정안전부장관",            // Sender name (required)
  "approval": {                          // Approval block (required: drafter and approver)
    "drafter":   {"title": "주무관", "name": "", "mark": "★"},
    "reviewers": [{"title": "과장", "name": "", "opinion": false}],
    "approver":  {"title": "국장", "name": ""},
    "coordinators": [{"title": "○○과장"}]
  },
  "doc_no": {"issue": "○○과-1234", "issue_date": "2026. 10. 14.", "receive": "", "receive_date": ""},
  "contact": {"zip": "30112", "address": "세종특별자치시 ○○로 00", "homepage": "www.mois.go.kr",
              "phone": "044-000-0000", "fax": "044-000-0001", "email": "○○○@korea.kr", "disclosure": "공개"}
}
```
Item numbering: l1→1. / l2→가. / l3→1) / l4→가) / l5→(1) / l6→(가). Numbers increment sequentially within the same level, and reset when a higher level changes (제2조①). Second level and below are indented 2 characters (2타) to the right from the higher-level number start. Amounts must be written with Korean annotation, e.g. `금113,560원(금일십일만삼천오백육십원)`; if missing, `warnings` will contain "금액 한글 병기 필요(시행규칙 제2조②)" (제2조②). Dates are normalized from YYYY-MM-DD / YYYY.MM.DD to YYYY. MM. DD. (영 제7조⑤). `disclosure` must be one of "공개", "부분공개", "비공개".

## Supported agencies (52)

| Agency | Report | Press release | Agency | Report | Press release |
|---|---|---|---|---|---|
| 개인정보보호위원회 | agency rules | paragraph | 법무부 | agency rules | □ outline |
| 경찰청 | agency rules | paragraph | 법제처 | agency rules | paragraph |
| 고용노동부 | agency rules | paragraph | 병무청 | common rules | paragraph |
| 공정거래위원회 | agency rules | paragraph | 보건복지부 | agency rules | paragraph |
| 과학기술정보통신부 | agency rules | paragraph | 산림청 | agency rules | paragraph |
| 관세청 | agency rules | paragraph | 산업통상부 | agency rules | paragraph |
| 교육부 | agency rules | paragraph | 새만금개발청 | common rules | □ outline |
| 국가교육위원회 | agency rules | paragraph | 성평등가족부 | agency rules | □ outline |
| 국가데이터처 | agency rules | □ outline | 소방청 | common rules | □ outline |
| 국가보훈부 | agency rules | paragraph | 식품의약품안전처 | agency rules | paragraph |
| 국가유산청 | agency rules | paragraph | 외교부 | common rules | paragraph |
| 국무조정실 | agency rules | □ outline | 우주항공청 | agency rules | paragraph |
| 국민권익위원회 | agency rules | □ outline | 원자력안전위원회 | common rules | □ outline |
| 국방부 | agency rules | □ outline | 인구전략위원회 | common rules | paragraph |
| 국세청 | agency rules | □ outline | 인사혁신처 | agency rules | paragraph |
| 국토교통부 | agency rules | □ outline | 재외동포청 | common rules | □ outline |
| 금융위원회 | agency rules | paragraph | 재정경제부 | agency rules | paragraph |
| 기본사회위원회 | common rules | □ outline | 조달청 | agency rules | paragraph |
| 기상청 | agency rules | paragraph | 중소벤처기업부 | agency rules | paragraph |
| 기획예산처 | agency rules | paragraph | 지식재산처 | agency rules | paragraph |
| 기후에너지환경부 | agency rules | paragraph | 질병관리청 | agency rules | paragraph |
| 농림축산식품부 | agency rules | paragraph | 통일부 | common rules | □ outline |
| 농촌진흥청 | agency rules | paragraph | 해양경찰청 | common rules | □ outline |
| 문화체육관광부 | agency rules | paragraph | 해양수산부 | agency rules | paragraph |
| 방송미디어통신위원회 | agency rules | paragraph | 행정안전부 | agency rules | paragraph |
| 방위사업청 | agency rules | paragraph | 행정중심복합도시건설청 | agency rules | paragraph |

Report: agency rules = measured from that agency's attachment sections (42 agencies); common rules = most common values across agencies (agency name left blank when none is given). Press release: paragraph = article-style paragraphs; □ outline = □ → ㅇ → -.

## Agency logos

Government symbols and agency logos are not bundled (usage regulations). Agency staff should supply their own logo file.

- `logo_path` places the logo in the press release cover's logo slot (sized per agency) or above the report title box. `slogan_path` adds a press release slogan image.
- Without it, press releases get a same-size 「기관 로고」 placeholder; delete the text in Hangul and insert the picture.

## Data transmission

- Everything is local. This server calls no external API and sends neither drafts nor output files anywhere.
- Structuring the draft is done by the AI you use; check that service's own data policy.

## Basis

- Full parse of **2,670 press release HWPX files (52 central agencies)** from Korea.kr (정책브리핑). Press release body formatting measured on 2,016 releases: 35,465 paragraphs, 35,434 blank lines, 32,392 table cells.
- Report formatting comes from the **1,326** releases that contain a report-style attachment section (13,757 paragraphs), per agency (42 agencies with 3+ documents). The common skeleton (□ - * ※ marks, one space after the mark, one-row title box, table header in 맑은 고딕 centered bold) agrees across 90%+ of agencies.
- Official standards: item numbering in the Enforcement Rule of the Regulation on Administrative Business Operation and Innovation (1. → 가. → 1) → 가) …), and Gyeonggi Provincial Office of Education's guide 「한 곳에 정리한 공문서 작성법」 (wrapped lines align to the item's first character, one space after the mark, sub-items indented by two spaces, etc.).
- Measurement: 2,670 Korea.kr press releases from 52 agencies (1,326 with a report section), from which per-agency marks, fonts, blank lines and cover-table values were derived.
- Rule documents: `korean_report_hwpx/refs/`. Rule values: `rules/`, `rules_report/`; press release cover/contact numbers: `templates/`.
- Source releases are published on Korea.kr under KOGL (공공누리). This repository contains no source files, text or images — only format numbers.

## Notes

- Output is a draft. Check it in Hangul before use.
- Line ends (e.g. a one- or two-character last line) are fitted from estimated glyph widths, so some may remain. With **macOS + Hancom Office Hangul**, `polish=True` reads the real line layout and re-chooses spacing per paragraph (Hangul windows open several times; takes minutes).
- Fonts render with whatever is installed; missing fonts (e.g. 휴먼명조, HY헤드라인M) are substituted.
- Draft approval documents / official notices (기안문·시행문) are supported with `doc_type="official"` (별지 제1호서식, rules_official/_공통.json). Item numbers (1.→가.→1)→가)→(1)→(가)) are assigned by the server; do not write numbers yourself. Dates are normalized from YYYY-MM-DD / YYYY.MM.DD to YYYY. MM. DD.

## License

MIT © 2026 Upstage

Created by Mia(윤승미)
