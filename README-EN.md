# press-release-hwpx — Korean Government Press Release HWPX MCP

<!-- mcp-name: io.github.UpstageAI/press-release-hwpx -->

![Demo: manuscript → ministry-format press release](https://raw.githubusercontent.com/UpstageAI/press-release-hwpx/main/docs/demo.gif)

[![PyPI](https://img.shields.io/pypi/v/press-release-hwpx)](https://pypi.org/project/press-release-hwpx/) [![MCP Registry](https://img.shields.io/badge/MCP%20Registry-press--release--hwpx-blue)](https://registry.modelcontextprotocol.io/v0/servers?search=press-release-hwpx) [![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE) · [한국어](README.md)

**Turns a manuscript into a Korean government press release (HWPX, the Hangul word processor format) in a specific ministry's format.** Covers 52 central government agencies. Formatting rules were measured from 2,670 published press releases. Files are drawn from rules: no source documents or logos are bundled.

**Try asking**

- "Make this draft into a Ministry of the Interior and Safety (행정안전부) press release HWPX"
- "National Tax Service (국세청) format — embargo 2026. 10. 8.(Thu) morning papers, contact 김○○ 사무관 044-000-0000"
- "Does 산림청 use paragraph style or □ outline style? Show its level fonts and sizes"
- "Rebuild the structure JSON from before with a new subtitle"
- "Use our agency logo file (logo.png)"

**One-line install** — `claude mcp add press-release-hwpx -- uvx press-release-hwpx`

- **Per-agency format** — cover, embargo/distribution, title and contact tables; body style (paragraph 37 / □ outline 15)
- **Computed, not copied** — hanging indent = (spaces before mark × 0.5 + mark width + spaces after × 0.5) × font size; gaps between levels use each agency's measured values
- **Line-end tidying** — per-paragraph character spacing to avoid short last lines and mid-word breaks
- **No source files or logos** — a blank HWPX is generated in code; only format numbers are used

## Install

With [uv](https://docs.astral.sh/uv/) it runs without a separate install.

```json
{
  "mcpServers": {
    "press-release-hwpx": {
      "command": "uvx",
      "args": ["press-release-hwpx"],
      "env": { "UPSTAGE_API_KEY": "only for make_press_release" }
    }
  }
}
```

Claude Code: `claude mcp add press-release-hwpx -- uvx press-release-hwpx`

Files are written to `~/press-release-hwpx/` (override with `PRESS_RELEASE_OUT_DIR`).

## Tools

| Tool | What it does | Sends data out |
|---|---|---|
| `list_ministries` | Supported agencies and body style (paragraph / □ outline) | No |
| `get_rules` | Agency format rules (marks, leading spaces, fonts, sizes, line spacing, gaps between levels) | No |
| `build_from_structure` | Structure JSON (embargo, title, subtitles, body blocks, appendix, contacts) → agency-format HWPX | No |
| `make_press_release` | Manuscript (text or .hwpx/.hwp/.pdf/.docx/.txt/.md) → structured by Solar → agency-format HWPX | Manuscript is sent to the Solar API |

Block types: `l1` (□) `l2` (ㅇ) `l3` (-) `p` (paragraph) `note` (*) `ref` (※) `h` (subheading) `caption` `table` `box` `image`. If the manuscript has no contact, the contact table is filled with placeholders `○○과 / 김○○ / 044-000-0000` (`placeholder_contact`).

## Agency logos and slogans

Government emblems and agency logos are not bundled, under the rules on the use of government symbols. Staff of the agency should supply their own logo file.

1. Pass `logo_path` to place the logo in the cover's logo slot (sized per agency). Use `slogan_path` for a slogan image.
2. Or open the file in Hangul, delete the text in the 「기관 로고」 box and insert the picture.

## Supported agencies (52)

| Agency | Body style | Agency | Body style |
|---|---|---|---|
| 개인정보보호위원회 | paragraph | 경찰청 | paragraph |
| 고용노동부 | paragraph | 공정거래위원회 | paragraph |
| 과학기술정보통신부 | paragraph | 관세청 | paragraph |
| 교육부 | paragraph | 국가교육위원회 | paragraph |
| 국가데이터처 | □ outline | 국가보훈부 | paragraph |
| 국가유산청 | paragraph | 국무조정실 | □ outline |
| 국민권익위원회 | □ outline | 국방부 | □ outline |
| 국세청 | □ outline | 국토교통부 | □ outline |
| 금융위원회 | paragraph | 기본사회위원회 | □ outline |
| 기상청 | paragraph | 기획예산처 | paragraph |
| 기후에너지환경부 | paragraph | 농림축산식품부 | paragraph |
| 농촌진흥청 | paragraph | 문화체육관광부 | paragraph |
| 방송미디어통신위원회 | paragraph | 방위사업청 | paragraph |
| 법무부 | □ outline | 법제처 | paragraph |
| 병무청 | paragraph | 보건복지부 | paragraph |
| 산림청 | paragraph | 산업통상부 | paragraph |
| 새만금개발청 | □ outline | 성평등가족부 | □ outline |
| 소방청 | □ outline | 식품의약품안전처 | paragraph |
| 외교부 | paragraph | 우주항공청 | paragraph |
| 원자력안전위원회 | □ outline | 인구전략위원회 | paragraph |
| 인사혁신처 | paragraph | 재외동포청 | □ outline |
| 재정경제부 | paragraph | 조달청 | paragraph |
| 중소벤처기업부 | paragraph | 지식재산처 | paragraph |
| 질병관리청 | paragraph | 통일부 | □ outline |
| 해양경찰청 | □ outline | 해양수산부 | paragraph |
| 행정안전부 | paragraph | 행정중심복합도시건설청 | paragraph |

## Optional: spacing polish

`make_press_release(..., polish=True)` works only on **macOS with Hancom Office Hangul** installed. It reads the real line layout from Hangul and re-chooses character spacing per paragraph (Hangul windows open several times; takes minutes). Normal generation does not need Hangul.

## Data transmission

- Basic generation (`build_from_structure`) sends nothing out; the file is built on your machine.
- `make_press_release` sends the manuscript to the Upstage API (`api.upstage.ai`). Do not include personal or other sensitive data.
- On air-gapped networks, set `PRESS_RELEASE_SOLAR_BASE_URL` to an internal Solar endpoint (`PRESS_RELEASE_SOLAR_KEY` for its key, `PRESS_RELEASE_MODEL` for the model name).

## Where the rules come from

- Full parse of **2,670 press release HWPX files (52 central agencies)** from Korea.kr (정책브리핑). Body formatting measured on 2,016 releases: 35,465 paragraphs, 35,434 blank lines, 32,392 table cells.
- Official standard: Enforcement Rule of the Regulation on Administrative Business Operation (item numbering).
- Rule documents: `press_release_hwpx/refs/`. Rule values: `rules/`, `rules_report/`; agency cover/contact table numbers: `templates/`.
- Source releases are published on Korea.kr under KOGL (공공누리). This repository contains no source files, text or images — only format numbers.

## Notes

- Output is a draft. Check it in Hangul before release.
- Fonts render with whatever is installed; missing fonts (e.g. 휴먼명조, HY헤드라인M) are substituted.
- Normal generation fits line ends from estimated glyph widths; exact line-end cleanup needs the polish option (macOS + Hangul).

## License

MIT © 2026 Upstage

Created by Mia(윤승미)
