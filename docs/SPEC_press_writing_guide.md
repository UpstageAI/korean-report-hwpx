# SPEC — 보도자료 작성 방법(내용) 가이드 + 사실 메모 → 구조 초안 + 작성 점검 (0.4.0)

지금까지 이 서버는 보도자료의 **서식**(기관 머리·담당 표·계층 기호·빈 줄)만 알려 주었다. 이번 버전은 **무엇을 어떤 순서로 쓰는지**(내용)를 알려 주고, 사실 메모를 구조 JSON으로 옮기는 도구와 흔한 작성 오류 점검을 더한다. 서식(templates/·rules/ 52개 기관, compose.py)은 바꾸지 않는다.

근거와 데이터는 `korean_report_hwpx/guides/press_writing.json`(Claude 작성, **읽기만**, 코드에 같은 값을 다시 적지 않는다)에 있다.
- `sources`: 국립국어원 『유형별로 알아보는 보도자료 작성 길잡이』(2020, G20)·『보도자료 유형별 표준안 개발』(2020, R20)·『보도 자료 쓰기 길잡이』(2011, G11)·『개정판 한눈에 알아보는 공공언어 바로 쓰기』(2022, H22)·『쉬운 공공언어 쓰기 길잡이』(2014, E14)
- `corpus`: 정책브리핑 보도자료 2,667건(52개 기관) 본문 실측
- `guide`(규칙 문장 15개, 출처 쪽 포함), `steps`, `facts_template`, `facts_fields`, `kinds`, `types_order`, `examples`(과학기술정보통신부·행정안전부 가상 사례: facts와 기대 structure), `check`(점검용 정규식·단어 목록·한도)

`tests/`·`docs/`·`korean_report_hwpx/guides/`·`korean_report_hwpx/templates/`·`korean_report_hwpx/rules*/`는 수정하지 않는다.

## A. 데이터 읽기
- `server.py`가 시작할 때 `guides/press_writing.json`을 한 번 읽어 모듈 변수 `PRESS_GUIDE`(dict)로 둔다.
- 정규식·단어 목록·한도는 모두 `PRESS_GUIDE["check"]`에서 가져온다.

## B. 서버 안내(instructions)와 도구 설명 — 에이전트가 이 MCP를 고르게
1. `MCPServer(... instructions=...)` 문구에 다음을 모두 넣는다(문장은 자유, 단어는 그대로):
   - 쓰는 경우: `보도자료`, `보도참고자료`, `설명자료`, `해명자료`, `보고서`, `기안문`, `HWPX`, `한글` 파일을 원할 때
   - `파이썬 등으로 HWPX를 직접 만들지 말고 이 도구를 쓴다`
   - 보도자료 순서(문구 안에서 도구 이름이 **처음 나오는 순서**도 이대로): `get_writing_guide(doc_type='press_release', ministry=기관)` → `draft_press_structure`(사실 메모 → 구조 초안) → 문장 다듬기 → `check_structure` → `build_document`
   - 기존 문구(공통 서식, 지어내지 않기, warnings 있으면 고쳐 다시 build)는 유지
2. `build_document` 독스트링 첫 줄을 `보고서·보도자료(보도참고·설명·해명자료 포함)·기안문을 기관 서식 HWPX(한글 파일)로 만든다.`로 시작한다(뒤 설명은 유지, `ministry` 인자로 check에 기관을 넘긴다는 한 줄 추가).
3. `get_writing_guide` 독스트링에 `보도자료를 쓸 때는 doc_type='press_release'와 ministry를 주면 작성 방법(리드·제목·인용·숫자·쉬운 말)과 사실 메모 양식, 기관별 가상 예시를 함께 준다` 문장을 넣는다.

## C. `get_writing_guide` — 보도자료 작성 방법 포함
- `doc_type`이 `press_release` 또는 `auto`이면 `guide` 문자열에 기존 `PRESS_RULES` 다음으로 `"\n".join(PRESS_GUIDE["guide"])`를 넣는다(첫 줄은 `[보도자료 작성 방법 — 내용]`으로 시작함). `report`·`official`에는 넣지 않는다.
- `press_release`이면 돌려주는 dict에 키를 더한다:
  - `press_writing`: `{"steps", "facts_template", "facts_fields", "kinds", "types_order"}` (PRESS_GUIDE 값 그대로)
  - `examples_press_release`: PRESS_GUIDE `examples` 목록 그대로(facts·structure 포함)
  - `example_press_release`: `ministry`가 예시 기관 중 하나면 그 예시의 `structure`, 아니면 첫 예시의 `structure`
- `auto`이면 `example_press_release`만 위 규칙으로(첫 예시). 기존 `EXAMPLE_PRESS` 상수는 지우고 이것으로 바꾼다(`writing_guide_prompt`도 같은 값 사용).
- `PRESS_RULES`의 `기관장 인용은 마지막 문단으로.` 줄은 `기관장 인용은 본문 끝(마지막 문단), 형식 '○○○ 장관은 “….”라고 말했다.'`로 바꾸고, `kind`(보도자료|보도참고자료|설명자료|해명자료, 머리 이름) 한 줄을 넣는다.
- `SCHEMA["press_release"]`에 `"kind": "str(보도자료|보도참고자료|설명자료|해명자료, 선택)"` 추가. 엔진(compose.py 표지)은 이미 `doc["kind"]`를 머리 이름으로 쓴다 — 엔진 수정 없음.

## D. 새 도구 `draft_press_structure(facts: dict | str, ministry: str = "") -> dict`
사실 메모(dict 또는 JSON 문자열)를 보도자료 구조 JSON 초안으로 **옮기기만** 한다. 메모에 없는 문장·숫자·이름을 만들지 않는다. 붙이는 고정 말은 조사(은/는), `“ ”라고`, `”라며, “`, 인용 동사, 표 머리 `구분`·`수치`·`기준·비교`, `주요 수치`, `참고 N`뿐이다. 외부 호출 없음.

돌려주는 값: `{"structure": dict, "doc_type": "press_release", "ministry": str, "missing": [str], "warnings": [str], "next": str}`

1. **기관**: `ministry` 인자 → 없으면 `facts["ministry"]`. 52개 기관(`C.ministries()`)이 아니면 `ValueError`(기존 `_check_ministry` 메시지).
2. **kind**: `facts.get("kind") or "보도자료"`. 4개 중 하나가 아니면 `ValueError`. `"보도자료"`가 아니면 `structure["kind"] = kind`, 보도자료면 `kind` 키를 넣지 않는다.
3. `release`·`distribute`: 메모 값 그대로(없으면 `""`).
4. `title`: `headline`을 strip하고 끝의 `.`를 뗀다. `subtitles`: 각 항목 앞뒤 공백과 앞뒤 `-`·`–`·`—`를 떼고 빈 것은 버린다. 3개 이상이면 앞 2개만 두고 `missing`이 아니라 `warnings`에 `부제는 2개까지 — 앞 2개만 넣음` 추가.
5. **블록 종류**: 기관 본문 방식이 문단식(`C.load_rules(m).get("style") == "para"`)이면 문장 블록 type `"p"`, 아니면 `"l1"`. 아래에서 "문장 블록"은 이 type이다.
6. **조사 `_josa(word, pair="은/는")`** (모듈 함수로, 테스트가 직접 부름): 끝 공백, 끝의 괄호 묶음 `(…)`, 끝의 `」』’”'"`를 더 뗄 것이 없을 때까지 번갈아 뗀 뒤 마지막 글자로 판단. 한글 음절이면 받침 있으면 앞(`은`), 없으면 뒤(`는`). 숫자면 0·1·3·6·7·8 → 앞, 2·4·5·9 → 뒤. 라틴 문자면 L·M·N·R(대소문자 무관) → 앞, 그 밖 → 뒤. 그 밖 → 뒤. `pair="이/가"`도 같은 규칙.
   - 예: `과학기술정보통신부(장관 ○○○)`→`는`, `○○○ 과학기술정보통신부 장관`→`은`, `○○○ 행정안전부 지방재정경제실장`→`은`, `KT`→`는`, `LG`→`는`, `2030`→`은`(0), `IBM`→`은`(M)
7. **보도자료·보도참고자료 본문 순서** (`body`):
   1. 리드: `facts["lead"]`가 있으면 그 문장(strip). 없으면 `who`와 `what`이 둘 다 있을 때 `f"{who}{_josa(who)} {when} {what}."` (when이 비면 `f"{who}{_josa(who)} {what}."`; `what` 끝의 `.`는 떼고 하나만 붙임; 연속 공백은 하나로). `what`이 `다`로 끝나지 않으면 `missing`에 `what은 '~한다/~했다'로 끝나는 서술어 절로` 추가. `who`·`what` 중 하나라도 없고 `lead`도 없으면 리드 블록을 만들지 않고 `missing`에 `lead 또는 who·what`.
   2. `background`(문자열이면 1개 목록으로) → 각각 문장 블록
   3. `points` 각 항목: 문자열 → 문장 블록. dict → `text` 문장 블록, 이어서 `details`의 각 문장 → `{"type": "l2"}` 블록, 이어서 `note`가 있으면 `{"type": "note"}` 블록
   4. `plan`(문자열이면 1개 목록) → 각각 문장 블록
   5. `quote`(dict, `speaker`와 `text`가 모두 있을 때만): `text`가 문자열이면 1개 목록으로. 각 인용 문장은 strip 후 앞뒤 따옴표(`“”"'‘’`)를 떼고, 끝이 `.`·`?`·`!`가 아니면 `.`를 붙인다. 동사 `verb = quote.get("verb") or "말했다"`(끝 `.` 뗌).
      - 1개: `f"{speaker}{_josa(speaker)} “{t1}”라고 {verb}."`
      - 2개 이상: `f"{speaker}{_josa(speaker)} “{t1}”라며, “{t2}”라고 {verb}."` (3개째부터는 `”라며, “`로 계속 이어 마지막만 `”라고`)
      - 문장 블록으로 **본문 맨 끝**에 둔다. quote가 없으면 만들지 않는다(missing에도 넣지 않음 — 할 말이 없으면 인용을 쓰지 않음, R20 68~69).
8. **설명자료·해명자료 본문 순서**: `issue` → `position` → `grounds`(목록) 각각 문장 블록. 리드 규칙(7-1)은 쓰지 않는다. `issue`가 없으면 `missing`에 `issue(문제 사안 — 보도 내용 요약)`, `position`이 없으면 `missing`에 `position(입장)`. quote가 있으면 7-5대로 맨 끝.
9. **appendix**: `facts["appendix"]` 순서대로, 그다음 `numbers`가 있으면 맨 뒤에 하나. 제목은 순서대로 `참고 1`, `참고 2`, ….
   - 항목 `{heading, items}` → `body = [{"type": "l1", "text": s} for s in items]`
   - 항목 `{heading, rows}` → `body = [{"type": "caption", "text": heading}, {"type": "table", "rows": rows}]`
   - 항목에 `body`(블록 목록)가 있으면 그대로
   - `numbers`(목록 `{item, value, unit, basis}`) → `{"title": "참고 N", "heading": facts.get("numbers_heading") or "주요 수치", "body": [caption(같은 heading), table]}`. 표 행: 머리 `["구분", "수치", "기준·비교"]`, 각 행 `[item, f"{value}{unit}", basis]`(value·unit은 문자열로, 없으면 `""`). 모든 basis가 비면 `기준·비교` 열을 빼고 2열. `unit`이 빈 항목마다 `warnings`에 `numbers[i] '{item}' 단위 없음 — 건·명·원·% 등` 추가.
   - appendix가 없으면 `[]`
10. **contact**: `facts["contact"]`가 dict면 `dept`(없으면 `""`), `people`의 각 항목이 목록이면 그대로(문자열로), dict면 `[role, title, name, phone]`(키 `role`·`title`·`name`·`phone`). 전화가 있고 `(`로 시작하지 않으면 `(전화)`로 감싼다. contact가 없거나 people이 비면 `missing`에 `contact(담당 부서·책임자·담당자·전화)`. 결과는 늘 `{"dept": str, "people": list}`.
11. `title`이 비면 `missing`에 `headline(제목)`, `release`가 비면 `missing`에 `release(보도시점)`.
12. `warnings` = 9의 단위 경고 + 4의 부제 경고 + `check(structure, "press_release", "standard", ministry)`의 warnings(E절 포함).
13. `next`: `메모에 없는 사실을 더하지 말고 문장을 다듬은 뒤 check_structure(structure, 'press_release', ministry=…) → build_document(structure, 'press_release', ministry)` 취지의 문장(기관 이름 포함).
- 결과 `structure`는 그대로 `build_document`에 넣을 수 있어야 한다. `guides/press_writing.json`의 두 예시는 `draft_press_structure(example["facts"])["structure"] == example["structure"]`가 성립한다(테스트).

## E. `check_structure`·`build_document` 작성 점검 (보도자료)
- 시그니처: `check_structure(structure, doc_type="report", style="standard", ministry: str = "")`, 내부 `check(structure, doc_type, style, ministry="")`. `build_document`는 자기 `ministry`를 `check`에 넘긴다. 기존 호출(위치 인자 3개까지)은 그대로 동작.
- `t == "press_release"`일 때만 아래 점검을 더한다. 경고 문구는 모두 `[작성] `으로 시작하고 끝에 출처를 괄호로 붙인다(아래 따옴표 안 낱말은 테스트가 찾으므로 그대로 쓴다). 예시 두 개와 E절 테스트의 "좋은 예"는 경고가 하나도 없어야 한다.
- "본문 문장 블록" = `body`에서 type이 `p`·`l1`·`l2`·`l3`인 블록(순서 유지). `note`·`ref`·`caption`·`table`·`box`·`image`는 빼고 센다. 리드 = 본문 문장 블록 중 type이 `p` 또는 `l1`인 첫 블록의 text. 리드 점검은 kind가 `설명자료`·`해명자료`이면 건너뛴다.
- `CK = PRESS_GUIDE["check"]`

| # | 점검 | 조건 | 경고에 들어갈 말 |
|---|---|---|---|
| E1 | 리드 누가 | 리드 앞 `CK.who_window`(60)자 안에 ministry 이름, `CK.ministry_short[ministry]`, `CK.who_regex` 매치가 모두 없음 | `리드`, `누가` (G20 39) |
| E2 | 리드 언제 | 리드 전체에 `CK.when_regex` 매치 없음 | `리드`, `언제` (G20 39) |
| E3 | 리드 완결 | 리드가 `다.`·`다`로 끝나지 않음(끝 공백·참고 표시 `참고 N` 제외) | `리드`, `완결` (G20 54) |
| E4 | 리드 길이 | 리드 글자 수 > `CK.lead_max`(200) | `리드가 깁니다` (G20 38) |
| E5 | 리드 인용 | 리드에 `CK.quote_regex` 매치 | `리드`, `인용` (G20 38~39) |
| E6 | 인용 위치 | 인용 블록(본문 문장 블록 중 `CK.quote_regex` 매치 + `CK.quote_verbs` 중 하나 포함) 가운데 **마지막** 인용 블록 뒤에 본문 문장 블록이 3개 이상 | `인용`, `끝` (말뭉치: 끝 세 문단 안 88%) |
| E7 | 제목 과장 | 제목에 `CK.hype_words` 낱말이 있음(낱말마다 1개) | `제목`, 그 낱말, `근거` (말뭉치·G20 33) |
| E8 | 제목 마침표 | 제목이 `.`로 끝남 | `제목`, `마침표` |
| E9 | 부제 수 | 부제 > `CK.subtitle_max_count`(2) | `부제`, `2개` (G20 36) |
| E10 | 숫자 단위 | 아래 알고리즘, 블록마다 최대 1개, 문서 전체 최대 3개 | `단위`, 숫자 앞뒤 글자 (G11 32, 말뭉치) |
| E11 | 단위 띄어쓰기 | 본문 문장 블록·note에 `CK.unit_space_regex` 매치(첫 매치마다 1개, 최대 3개) | `띄어` (G11 32~33, H22 66) |
| E12 | 외국 문자 먼저 | 제목·부제·본문 문장 블록에 `CK.foreign_first_regex` 매치 | `한글을 먼저` (G20 63) |
| E13 | 약어 풀이 | 본문 문장 블록(순서대로 이어 붙인 글)에서 `CK.acronym_regex` 약어마다 **첫 등장** 위치가 괄호 안이 아니고(첫 등장 앞에 닫히지 않은 `(`가 없고) 바로 뒤가 `(`도 아님. `CK.replace_words`에 있는 약어는 E14가 다루므로 제외. 최대 3개 | 약어, `한글` (G20 63) |
| E14 | 쉬운 말 | 제목·부제·본문 문장 블록·note에 `CK.replace_words`의 낱말(키)이 있음(낱말마다 1개) | `'{낱말}' → '{다듬은 말}'` 형태, 출처 `CK.replace_sources`(없으면 `_default`) |
| E15 | 권위적 표현 | 본문 문장 블록에 `CK.authoritarian`의 키 | 키, 값 (G11 53) |
| E16 | 종결 혼용 | 본문 문장 블록 text에서 `“…”`·`"…"` 인용 부분을 지운 뒤, `니다.`로 끝나는 문장과 `니다.`가 아닌 `다.`로 끝나는 문장이 둘 다 있음(문서 전체 1개) | `혼용` (G20 55, G11 65) |
| E17 | 명사형 종결 | type `p`·`l1` 블록 text가 `(함|임|됨|음|예정|필요)\.?$`로 끝남(최대 3개) | `명사형` (G20 55) |
| E18 | 긴 문장 | 본문 문장 블록을 `(?<=다\.)\s+`로 나눈 문장 중 글자 수 > `CK.sentence_max`(150)(최대 3개) | `문장이 깁니다` (G20 56) |

**E10 숫자 단위 알고리즘** — 대상: 본문 문장 블록과 `note` 블록의 text.
1. 숫자 토큰: `(?<![\w.,’'‘])(\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?`. 정수부가 한 자리이고 쉼표·소수점이 없으면 건너뜀(`3대`, `1위` 등).
2. 토큰 바로 앞 글자가 `제`·`-`·`–`·`~`·`∼`·`/`·`:` 중 하나이면 건너뜀(`제10회`, 전화번호 뒷자리, 범위 뒤 숫자).
3. 토큰 뒤 글을 `rest`라 하고, 앞의 공백만 뗀 `r = rest.lstrip(" ")`.
4. 정상(건너뜀): `r`이 `CK.units` 중 하나로 시작(긴 것부터 비교) / `r[0]`이 라틴 문자 또는 `%℃㎡㎢㎞㎏` / `rest[0]`이 `:`·`~`·`∼`·`-`·`–`·`/`·`·`·`(`·`)`·`×` 중 하나 / `rest`가 `.`로 시작하고 그다음이 (공백 뒤)숫자 또는 `(`(날짜 `2026. 10. 7.`·`9.30(수)`) / `rest`가 `,`로 시작하고 바로 다음 글자가 숫자(쉼표 붙은 숫자 열).
5. 그 밖(한글 비단위 낱말, `,` 뒤 공백, 문장 끝 `.`, 글 끝 등) → 경고. 경고에 토큰 앞 8자~뒤 8자를 보여 준다.
- 예: `확인 요청 128, 이 중` → 경고 / `128건`·`2026년`·`10월 7일`·`40억 원`·`3.5%`·`044-202-0000`·`2027~2029년`·`5G`·`9.30(수)`·`1,240건`·`30여 명` → 정상.

**경고와 ok**: E절 경고도 warnings에 들어가므로 `ok`가 False가 된다(기존 규칙 그대로). `build_document`는 경고가 있어도 파일을 만든다(기존 동작).

## F0. 보도자료 머리·담당 표 바로잡기 (위화감 제거)
1. **머리 이름**: 템플릿 52개 중 9개는 서식 표본이 보도참고자료·보도설명자료여서 `templates/<기관>.json`의 `cover.label`이 `보도참고자료`(공정거래위원회·국세청·기획예산처·농림축산식품부 등 6곳)나 `보도설명자료`(과학기술정보통신부 등 2곳)다. 지금은 `kind`가 없으면 이 값이 머리에 찍혀, 과학기술정보통신부 보도자료가 '보도설명자료'로 나온다. → `build_document`(press_release)는 compose에 넘기는 구조에 `kind = s.get("kind") or "보도자료"`를 넣는다(템플릿 파일은 고치지 않는다, 칸 폭·글꼴은 템플릿 그대로).
2. **담당 부서 유지**: `placeholder_contact=True`이고 `people`이 비었을 때 지금은 `dept`까지 자리표시(`○○과`)로 바뀐다. → `engine/compose.py`에서 `dept`가 있으면 그 값을 두고 `people`만 자리표시로 채운다(`dept`도 비었을 때만 자리표시 부서).
3. **가림 표기 보존**: `_normalize`의 앞 기호 제거(`LEAD`)가 `○○○ 과학기술정보통신부 장관은 …`의 `○○○ `를 항목 기호로 보고 지운다. → `○`·`〇`가 2개 이상 이어지면(가림 표기) 기호로 보지 않는다(정규식 앞에 `(?![○〇]{2})`). `ㅇ`·`○` 한 개 + 공백은 지금처럼 기호로 지운다.

## F. 기존 동작 유지
- 보고서·기안문 점검·생성은 바뀌지 않는다(생성 파일 비교 테스트가 지킴). 보도자료 HWPX 서식(머리·담당 표·문단 모양)도 바뀌지 않는다 — 바뀌는 것은 warnings와 가이드 내용뿐.
- `list_ministries`·`get_rules` 그대로. 도구 목록에 `draft_press_structure` 추가.
- 외부 API 호출 없음(`test_no_external_api`).

## G. 문서
- README·README-EN: 도구 표에 `draft_press_structure` 한 줄, "보도자료 작성 방법(국립국어원 지침·정책브리핑 실측)" 한 단락과 사실 메모 예시(과학기술정보통신부 가상 예시의 facts 일부), 출처 목록(국립국어원 자료 5종 제목·연도). 공무원 실명·실제 반응 없음.
- CHANGELOG 0.4.0, pyproject·server.json 0.4.0.

## 완료 조건
`tests/test_press_writing.py` 전부 통과(수정 금지) + 기존 테스트 전부 통과. `.venv/bin/python -m pytest tests -q`

## H. 리뷰 보완 (1차 구현 검토 후)
1. **경고 문구를 고칠 수 있게**: E절 경고는 아래 문구 그대로(중괄호는 값). 에이전트가 경고만 보고 고칠 수 있어야 한다.
   - E1 `[작성] 리드(첫 문단) 앞부분에 '누가'(기관·기관장)가 없음 — '○○부(장관 ○○○)는 …'처럼 시작 (G20 39)`
   - E2 `[작성] 리드에 '언제'(날짜·시행일·기간)가 없음 — 예: '10월 28일(수)', '11월 2일부터' (G20 39)`
   - E3 `[작성] 리드는 '~한다/~했다'로 끝나는 완결 문장으로 (G20 54)`
   - E4 `[작성] 리드가 깁니다({글자 수}자) — 누가·언제·무엇만 한 문장으로, 세부는 다음 문단 (G20 38)`
   - E5 `[작성] 리드에 인용문 — 리드는 사실만, 인용은 본문 끝으로 (G20 38~39)`
   - E6 `[작성] 인용 문단은 본문 끝(마지막~끝에서 셋째 문단)에 둔다 (말뭉치: 끝 세 문단 안 88%)`
   - E7 `[작성] 제목의 '{낱말}' — 본문에 비교 기준·근거가 있는지 확인 (말뭉치·G20 33)`
   - E8 `[작성] 제목 끝에 마침표를 찍지 않는다`
   - E9 `[작성] 부제는 1개가 가장 좋고 2개를 넘기지 않는다 (G20 36)`
   - E10 `[작성] 숫자 뒤 단위 없음: '{토큰 앞 8자~뒤 8자}' — 건·명·원·% 등 단위를 붙인다 (G11 32, 말뭉치)`
   - E11 `[작성] 단위는 띄어 쓴다: '{매치}' → '{숫자·억/만/천} {단위}' (G11 32~33, H22 66)` 예: `'76억원' → '76억 원'`
   - E12 `[작성] 외국 문자는 한글을 먼저 쓰고 괄호 안에: '{매치}' (국어기본법 제14조, G20 63)`
   - E13 `[작성] '{약어}' 첫 등장에 한글 풀이 없음 — '인공지능(AI)'처럼 한글(약어)로 (G20 63)`
   - E14 `[작성] '{낱말}' → '{다듬은 말}' ({출처})` — 낱말마다 1개, 개수 제한 없음
   - E15 `[작성] 권위적 표현 '{키}' → '{값}' (G11 53)`
   - E16 `[작성] '-다'와 '-습니다' 혼용 — 한 가지로 (G20 55, G11 65)`
   - E17 `[작성] 명사형 종결 — '-다'로 끝낸다: '…{text 끝 12자}' (G20 55)`
   - E18 `[작성] 문장이 깁니다({글자 수}자) — 3줄(약 150자) 안쪽으로 끊는다 (G20 56)`
2. **E1은 ministry가 비어도 동작**: 빈 문자열은 "창 안에 있다"로 치지 않는다(`"" in s`가 늘 참인 함정). ministry가 없으면 `who_regex`만 본다.
3. **E10은 블록마다 1개, 문서 최대 3개**(지금은 첫 경고 뒤 모든 블록을 건너뜀). 대상은 `body`의 본문 문장 블록과 note만(appendix 제외).
4. **E11은 본문 문장 블록과 note 대상**, 매치마다 위 문구.
5. **가이드 중복 제거**: `get_writing_guide("press_release")`의 `guide`에 `[보도자료 작성 방법` 단락은 정확히 1번(지금 2번 들어감).
6. **`_josa` 라틴 문자는 L·M·N·R만 앞(은·이)**: `S`(에스)는 뒤.
7. **`draft_press_structure(facts: dict | str, ministry: str = "")` 타입 표시**(MCP 입력 스키마에 facts가 object·string으로 보이게). `quote.verb`가 빈 문자열이면 `말했다`. note 문장도 strip.
8. CHANGELOG 0.4.0 날짜는 `(미배포)`로, "과학기술정보통신부장관" 오타는 "과학기술정보통신부"로. 쪽 설정(`docs/SPEC_page_settings.md`) 내용도 0.4.0에 함께 적는다.
