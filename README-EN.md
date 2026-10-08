# korean-gov-docs — Korean Government Documents MCP (reports and press releases as HWPX)

<!-- mcp-name: io.github.UpstageAI/korean-gov-docs -->

![Demo: memo → agency-format report and press release](https://raw.githubusercontent.com/UpstageAI/korean-gov-docs/main/docs/demo.gif)

[![PyPI](https://img.shields.io/pypi/v/korean-gov-docs)](https://pypi.org/project/korean-gov-docs/) [![MCP Registry](https://img.shields.io/badge/MCP%20Registry-korean--gov--docs-blue)](https://registry.modelcontextprotocol.io/v0/servers?search=korean-gov-docs) [![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE) · [한국어](README.md)

**Korean civil-service documents (reports and press releases) as HWPX, in each agency's format.** Your own AI (Claude, ChatGPT, …) structures the memo or draft, and the server draws a Hangul (HWPX) file from format rules for 52 central government agencies.

**Nothing leaves your machine · no API key** — everything runs locally; the draft is never sent anywhere by this server.

> One request — "write this up like an official document" (공문서처럼 써 줘) — produces an outline-style report (□ → ㅇ → -) or a press release in the agency's format. Rules were measured from 2,670 published press releases; no source documents or logos are bundled.

**Try asking**

- "Turn this memo into a Ministry of the Interior and Safety (행안부) report"
- "These are meeting notes — format them as an official document" (no agency given → common format)
- "Make this a National Tax Service (국세청) press release — embargo 2026. 10. 8.(Thu) morning papers"
- "Rebuild the report from before with a new □ sentence in section Ⅲ"
- "Show the report format rules for 산림청 (marks, fonts, sizes per level)"

**One-line install** — `claude mcp add korean-gov-docs -- uvx korean-gov-docs`

## Document types

| Type | Layout | Agency | Rules |
|---|---|---|---|
| **Report (개조식 outline)** | Title box, date/department line (optional), section headings (Ⅰ. Ⅱ.) → □ → ㅇ → - → *, ※ notes, tables, attachment pages (붙임·참고) | Optional — 42 agencies have their own rules; others or none use common rules | `rules_report/` (1,326 report-style sections) |
| **Press release (보도자료)** | Cover (logo slot), embargo/distribution, title and subtitles, body (paragraph / □ outline), contact table, appendix pages | Required — 52 agencies | `rules/`, `templates/` (2,670 releases) |
| Draft approval document (기안문) | — | — | Planned for the next version |

**Flow** — ask your AI "turn this memo into a 행안부 report" → it reads `get_writing_guide` → writes the structure JSON → calls `build_document` → if `warnings` come back, it fixes the structure and builds again.

Type choice (in the guide): public announcement or distribution → press release; internal reporting, plans or reviews → report.

## Install

With [uv](https://docs.astral.sh/uv/) it runs without a separate install.

```json
{
  "mcpServers": {
    "korean-gov-docs": {
      "command": "uvx",
      "args": ["korean-gov-docs"]
    }
  }
}
```

Claude Code: `claude mcp add korean-gov-docs -- uvx korean-gov-docs`

- No API key or environment variables required.
- Files are written to `~/korean-gov-docs/` (override with `KOREAN_GOV_DOCS_OUT_DIR`).

## Tools

| Tool | What it does |
|---|---|
| `get_writing_guide` | Type-choice criteria, writing rules (□ one-sentence conclusion first, ㅇ grounds, - details, noun-form endings, no invented facts or numbers, no marks inside text, appendix structure), structure JSON schema and examples. Also exposed as MCP prompt `writing_guide` |
| `check_structure` | Pre-build check: required fields, marks inside text, skipped levels, multi-sentence □, non-noun-form endings, long titles |
| `build_document` | Structure JSON → agency-format HWPX; normalizes input (strips marks, dashes, leading spaces) and returns `warnings` to fix. `build_from_structure` is an alias |
| `list_ministries` | Supported agencies and support per document type |
| `get_rules` | Format rules per agency and document type (marks, fonts, sizes, indents, gaps, title box, table header) |

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

## Where the rules come from

- Full parse of **2,670 press release HWPX files (52 central agencies)** from Korea.kr (정책브리핑). Press release body formatting measured on 2,016 releases: 35,465 paragraphs, 35,434 blank lines, 32,392 table cells.
- Report formatting comes from the **1,326** releases that contain a report-style attachment section (13,757 paragraphs), per agency (42 agencies with 3+ documents). The common skeleton (□ - * ※ marks, one space after the mark, one-row title box, table header in 맑은 고딕 centered bold) agrees across 90%+ of agencies.
- Official standard: Enforcement Rule of the Regulation on Administrative Business Operation (item numbering).
- Rule documents: `korean_gov_docs/refs/`. Rule values: `rules/`, `rules_report/`; press release cover/contact numbers: `templates/`.
- Source releases are published on Korea.kr under KOGL (공공누리). This repository contains no source files, text or images — only format numbers.

## Notes

- Output is a draft. Check it in Hangul before use.
- Line ends (e.g. a one- or two-character last line) are fitted from estimated glyph widths, so some may remain. With **macOS + Hancom Office Hangul**, `polish=True` reads the real line layout and re-chooses spacing per paragraph (Hangul windows open several times; takes minutes).
- Fonts render with whatever is installed; missing fonts (e.g. 휴먼명조, HY헤드라인M) are substituted.
- Draft approval documents (기안문) are planned for the next version.

## License

MIT © 2026 Upstage

Created by Mia(윤승미)
