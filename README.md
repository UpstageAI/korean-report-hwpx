# press-release-hwpx — 정부 보도자료 서식 HWPX MCP

<!-- mcp-name: io.github.UpstageAI/press-release-hwpx -->

<!-- TODO: docs/demo.gif 녹화 후 추가(아직 없음) -->
![데모: 원고 → 기관 서식 보도자료](https://raw.githubusercontent.com/UpstageAI/press-release-hwpx/main/docs/demo.gif)

[![PyPI](https://img.shields.io/pypi/v/press-release-hwpx)](https://pypi.org/project/press-release-hwpx/) [![MCP Registry](https://img.shields.io/badge/MCP%20Registry-press--release--hwpx-blue)](https://registry.modelcontextprotocol.io/v0/servers?search=press-release-hwpx) [![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE) · [English](README-EN.md)

**Korean government press releases as HWPX, in each ministry's own format.** 52 central government agencies, rules measured from 2,670 published press releases. Builds the file from rules — no source documents, no logos bundled. → [English README](README-EN.md)

---

> 보도자료 원고를 기관 서식에 맞춰 한글(HWPX) 파일로 만듭니다. 기관마다 다른 본문 방식(문단식/□식), 기호·글꼴·크기·내어쓰기·빈 줄을 정책브리핑 보도자료 전수 조사 규칙값으로 계산해 그립니다.

**이렇게 물어보세요**

- "이 원고를 행정안전부 보도자료 서식 HWPX로 만들어줘"
- "국세청 보도자료로 — 보도시점 2026. 10. 8.(목) 조간, 담당은 김○○ 사무관 044-000-0000"
- "산림청은 본문 방식이 문단식이야 □식이야? 계층별 글꼴·크기 규칙 보여줘"
- "아까 만든 구조 JSON에서 부제만 바꿔서 다시 만들어줘"
- "우리 기관 로고 파일(logo.png) 넣어서 만들어줘"

**설치 한 줄** — `claude mcp add press-release-hwpx -- uvx press-release-hwpx`

- **기관별 서식** — 52개 중앙행정기관의 표지·보도시점·제목·담당 표, 본문 방식(문단식 37곳/□식 15곳)
- **규칙으로 계산** — 내어쓰기 = (기호 앞 공백×0.5 + 기호 폭 + 기호 뒤 공백×0.5) × 글자 크기, 계층 사이 빈 줄은 기관 실측값
- **줄 끝 정리** — 문단마다 자간을 골라 짧은 마지막 줄·어절 중간 끊김을 줄임
- **원본·로고 미포함** — 빈 HWPX를 코드로 만들고 서식 수치만 사용

## 설치

[uv](https://docs.astral.sh/uv/)가 있으면 설치 없이 바로 실행됩니다.

```json
{
  "mcpServers": {
    "press-release-hwpx": {
      "command": "uvx",
      "args": ["press-release-hwpx"],
      "env": { "UPSTAGE_API_KEY": "make_press_release를 쓸 때만" }
    }
  }
}
```

Claude Code: `claude mcp add press-release-hwpx -- uvx press-release-hwpx`

만든 파일은 `~/press-release-hwpx/`에 저장됩니다(`PRESS_RELEASE_OUT_DIR`로 변경).

## 도구

| 도구 | 하는 일 | 외부 전송 |
|---|---|---|
| `list_ministries` | 지원 기관과 본문 방식(문단식/□식) | 없음 |
| `get_rules` | 기관 서식 규칙값(계층별 기호·기호 앞 공백·글꼴·크기·줄 간격, 계층 사이 빈 줄) | 없음 |
| `build_from_structure` | 구조 JSON(보도시점·제목·부제·본문 블록·참고·담당자) → 기관 서식 HWPX | 없음 |
| `make_press_release` | 원고(글 또는 .hwpx/.hwp/.pdf/.docx/.txt/.md) → Solar로 구조화 → 기관 서식 HWPX | 원고가 Solar API로 전송 |

구조 JSON 예:

```json
{
  "release": "2026. 10. 8.(목) 조간", "distribute": "2026. 10. 7.(수) 10:00",
  "title": "제목 한 줄", "subtitles": ["부제"],
  "body": [{"type": "l1", "text": "대항목 문장"}, {"type": "l2", "text": "중항목 문장"}, {"type": "note", "text": "각주"},
           {"type": "table", "rows": [["구분", "값"], ["가", "1"]]}],
  "appendix": [{"title": "참고 1", "heading": "세부 내용", "body": [{"type": "l1", "text": "..."}]}],
  "contact": {"dept": "○○과", "people": [["책임자", "과장", "이○○", "(044-000-0000)"], ["담당자", "사무관", "김○○", "(044-000-0000)"]]}
}
```

블록 종류: `l1`(□) `l2`(ㅇ) `l3`(-) `p`(문단) `note`(*) `ref`(※) `h`(소제목) `caption`(표 제목) `table` `box`(강조 상자) `image`. 문단식 기관은 `l1`을 문단으로 바꿔 씁니다. 원고에 담당자가 없으면 담당 표를 `○○과 / 김○○ / 044-000-0000` 자리표시로 채웁니다(`placeholder_contact`).

## 기관 로고·슬로건

정부상징·기관 로고는 사용 규정상 이 패키지에 포함하지 않습니다. 소속 기관 담당자가 자기 기관 로고 파일을 지정하세요.

1. `logo_path`로 로고 그림 파일을 지정하면 표지의 로고 자리(기관별 크기)에 들어갑니다. 슬로건 그림은 `slogan_path`.
2. 또는 만든 파일을 한글에서 열어 「기관 로고」 상자의 글을 지우고 그림을 넣으세요.

## 지원 기관 (52곳)

| 기관 | 본문 방식 | 기관 | 본문 방식 |
|---|---|---|---|
| 개인정보보호위원회 | 문단식 | 경찰청 | 문단식 |
| 고용노동부 | 문단식 | 공정거래위원회 | 문단식 |
| 과학기술정보통신부 | 문단식 | 관세청 | 문단식 |
| 교육부 | 문단식 | 국가교육위원회 | 문단식 |
| 국가데이터처 | □식 | 국가보훈부 | 문단식 |
| 국가유산청 | 문단식 | 국무조정실 | □식 |
| 국민권익위원회 | □식 | 국방부 | □식 |
| 국세청 | □식 | 국토교통부 | □식 |
| 금융위원회 | 문단식 | 기본사회위원회 | □식 |
| 기상청 | 문단식 | 기획예산처 | 문단식 |
| 기후에너지환경부 | 문단식 | 농림축산식품부 | 문단식 |
| 농촌진흥청 | 문단식 | 문화체육관광부 | 문단식 |
| 방송미디어통신위원회 | 문단식 | 방위사업청 | 문단식 |
| 법무부 | □식 | 법제처 | 문단식 |
| 병무청 | 문단식 | 보건복지부 | 문단식 |
| 산림청 | 문단식 | 산업통상부 | 문단식 |
| 새만금개발청 | □식 | 성평등가족부 | □식 |
| 소방청 | □식 | 식품의약품안전처 | 문단식 |
| 외교부 | 문단식 | 우주항공청 | 문단식 |
| 원자력안전위원회 | □식 | 인구전략위원회 | 문단식 |
| 인사혁신처 | 문단식 | 재외동포청 | □식 |
| 재정경제부 | 문단식 | 조달청 | 문단식 |
| 중소벤처기업부 | 문단식 | 지식재산처 | 문단식 |
| 질병관리청 | 문단식 | 통일부 | □식 |
| 해양경찰청 | □식 | 해양수산부 | 문단식 |
| 행정안전부 | 문단식 | 행정중심복합도시건설청 | 문단식 |

문단식 = 기호 없는 기사체 문단 위주, □식 = □ → ㅇ → - 개조식.

## 선택 기능: 자간 다듬기(polish)

`make_press_release(..., polish=True)`는 **macOS + 한컴오피스 한글**이 있을 때만 동작합니다. 한글로 실제 줄 배치를 받아 문단별 자간을 다시 고릅니다(한글 창이 여러 번 열리고 수 분 걸림). 기본 생성에는 한글이 필요 없습니다.

## 데이터 전송 안내

- 기본 생성(`build_from_structure`)은 외부 전송 없음 — 설치한 컴퓨터 안에서 파일을 만듭니다.
- `make_press_release`는 원고가 Upstage API(`api.upstage.ai`)로 전송되니 개인정보 등 민감정보를 넣지 마세요.
- 망분리 환경에서는 `PRESS_RELEASE_SOLAR_BASE_URL`로 내부 Solar 주소를 지정하세요(키는 `PRESS_RELEASE_SOLAR_KEY`, 모델 이름은 `PRESS_RELEASE_MODEL`).

## 규칙 근거

- 정책브리핑(korea.kr) 보도자료 HWPX **2,670건(52개 중앙행정기관)** 전수 파싱. 본문 서식은 2,016건의 문단 35,465개·빈 줄 35,434개·표 칸 32,392개 실측.
- 공식 기준: 행정업무의 운영 및 혁신에 관한 규정 시행규칙(항목 구분).
- 규칙 문서: [보도자료 서식 규칙](press_release_hwpx/refs/보도자료_서식_규칙.md), [보고서형 구간 서식 규칙](press_release_hwpx/refs/보고서_서식_규칙.md). 규칙값: `rules/`, `rules_report/`, 기관 표지·담당 표 수치: `templates/`.
- 원자료는 정책브리핑에 공공누리로 공개된 보도자료이며, 이 저장소에는 원본 파일·본문·그림을 포함하지 않고 서식 수치만 담았습니다.

## 유의

- 결과물은 초안입니다. 배포 전 한글에서 확인하세요.
- 글꼴은 사용하는 컴퓨터에 설치된 글꼴로 표시됩니다(휴먼명조·HY헤드라인M 등 미설치 시 대체 글꼴).

## 라이선스

MIT © 2026 Upstage

Created by Mia(윤승미)
