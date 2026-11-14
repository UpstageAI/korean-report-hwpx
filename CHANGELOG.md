# Changelog

## 0.5.6 (2026-11-14)

작성: Claude(공개 MCP 노출면 점검에서 나온 고칠 점). 생성 문서·도구 동작은 바뀌지 않음.

- serverInfo.version: `MCPServer`에 버전을 넘기지 않아 initialize 응답의 `serverInfo.version`이 빈 문자열이었다. 패키지 메타데이터 버전(`importlib.metadata`)을 `korean_report_hwpx.__version__`으로 두고 서버에 넘김(korean-tax-mcp 0.15.2와 같은 방식). `tests/test_server_info_version.py`.
- README·README-EN 재구성: 열어 두는 것은 한 단락 소개·한 줄 안내·설치(Claude Code 한 줄, Claude 앱 3단계, 윈도 안내 링크)·흐름 그림 1장(메모 → get_writing_guide·draft_press_structure → check_structure → build_document → 기관 서식 HWPX, 세법 MCP와 검토 보고서 연결)·"이렇게 물어보세요" 표·링크 줄. 도구 7개 표, 서식 기능, 간소화·내부 결재, 구조 JSON 예, 지원 기관, 근거, 작성 주체, 유의는 접기 안으로.
- Registry 배지 글자를 옛 이름 `korean-gov-docs`에서 `korean-report-hwpx`로, 배지 링크는 등록 이름 `io.github.UpstageAI/korean-report-hwpx` 검색으로.
- 작성 주체 문구를 CHANGELOG와 맞춤: 0.2.0부터 0.3.x까지 Solar Pro 4 작성·CodeSolar·Claude 검수, 0.4.0부터 뼈대 Solar Pro 4·보완·명세·정답 테스트 Claude(0.5.2·0.5.6은 Claude 작성). 데모 캡션의 "코드는 Solar Pro 4가 작성" 문장 삭제.
- 보도자료 건수 표기 정리: 서식 규칙은 수집 2,670건 전수 파싱, 본문 실측·쪽 설정은 그중 2,667건 기준임을 근거에 밝힘.
- README-EN: 분량 예측 설명을 한글 배치 규칙·실측 54개 문서 일치로 고치고, 국문판에만 있던 서식 기능 표·Claude 앱 설치·간소화 모드·내부 결재 보고서·질문 예를 번역해 넣음.
- pyproject: 설명에 기안문과 도구 7개, `[project.urls]`에 Homepage(소개 페이지)·Documentation·Changelog, keywords `official-draft`. server.json 설명에 기안문(official drafts).
- 라이선스 줄을 `MIT © 2026 Upstage · Created by Mia(윤승미)` 한 줄로.

## 0.5.5 (2026-11-10)

보완 Claude(뼈대 Solar Pro 4). 통합 시나리오(공문서 3종)에서 나온 고칠 점 — 생성 문서는 바뀌지 않음(고정 입력 26건의 header·section XML·md 바이트 동일; 달라진 것은 기안문 예시의 날짜 오탐 경고 1건이 사라진 것뿐). 1002 테스트.

- □(l1) '두괄식 한 문장' 점검이 공문서 날짜 표기 '2026. 11. 3.(화)'·'11. 2.'·''26. 10. 8.'·'2026. 11.'의 온점을 문장 끝으로 세던 오탐 수정(`_count_sentences`). 소수(3.5)·약어(p.·No.·etc.)·줄임표도 제외. '…했다. 그리고 …'처럼 진짜 두 문장은 그대로 경고하고, 문장 끝 뒤에 마침표 없는 절이 이어져도 한 문장으로 센다(끝의 '붙임 N' 꼬리표 제외).
- 날짜 빈칸 규칙을 작성 가이드에 명시: 연·월·일 온점 뒤 빈칸 하나(행정안전부 공문서 작성법). 본문 문장의 날짜·숫자+단위 빈칸은 2026-10-08부터 줄 끝에서 갈라지지 않도록 묶음 빈칸(`<hp:nbSpace/>`)으로 저장해 왔고 한글 화면에는 '11. 3.(화)'로 보인다 — 태그만 떼는 텍스트 추출기에서 '11.3.(화)'처럼 보이는 것은 압축이 아님. 표 칸은 보통 빈칸 그대로(문서 XML 변경 없음, 테스트로 고정).
- 기안문 입력 형태 검증: body를 문자열 목록으로, approval을 `{"drafter":"주무관 김철수","approver":"시장"}`처럼 납작하게, doc_no·contact를 문자열로 주면 check_structure·build_document가 스택 추적('Error executing tool') 대신 기대 형태(`{title, name, mark}`·`[{type, text}]` 등)와 example_official 위치를 적은 한국어 오류를 돌려준다. 납작한 approval이 check_structure를 통과하던 문제도 막음. 그 밖의 AttributeError도 스키마 안내 문구로.
- 도구 설명: `get_writing_guide`에 doc_type 'official' 명시, `build_document`에 기안문 body·approval·doc_no·contact 하위 필드, `draft_press_structure`는 facts를 `dict | str`로 받고 facts_template 위치·한 줄 예시를 설명에 넣음. 산문을 주면 'Expecting value' 대신 template 위치를 안내.
- `list_ministries`가 기관마다 TextContent 53개로 쪼개져 가던 것을 JSON 배열 하나(문자열)로.
- 1쪽 보고서 안내 보강: 줄이는 문서가 아니라 꽉 채우는 문서(핵심 수치·표로 압축, 세부는 주요 내용마다 붙임, 항목 단순 삭제 금지). 기관 서식(예: 행정안전부)은 □ 전체가 제목 서체(HY헤드라인M)로 찍혀 **…** 강조가 드러나지 않으므로 키워드 강조만 원하면 공통 서식을 쓰라고 안내.

## 0.5.4 (2026-11-10)

보완 Claude(뼈대 Solar Pro 4). 생성 문서는 바뀌지 않음(고정 입력 26건의 header·section XML·md 바이트 동일, 984 테스트).

- engine을 정식 패키지 `korean_report_hwpx.engine`으로 — 그동안 server·tests·polish가 sys.path를 고쳐 `compose`·`report`·`fit`·`pages` 같은 흔한 이름을 최상위 모듈로 import했다(다른 패키지와 이름 충돌 가능). 상대 import로 바꾸고 sys.path 조작 제거. 휠 내용(engine·rules·templates·guides)과 콘솔 스크립트는 그대로.
- HWPX XML 조각을 `engine/xml.py` 도우미(`tbl_xml`·`tc_xml`·`border_xml`·`para_xml`·`sublist_xml`)와 상수(`PT`·`TEXT_PAD`·`CELL_MARGIN`·`TBL_MARGIN`·`BOX_MARGIN`)로 — 손으로 쓰던 `<hp:tbl>` 4곳·`<hp:subList>` 5곳·`<hp:p id="0">` 9곳·borderFill 4곳이 0, 여백 리터럴 53곳 → 5곳.

## 0.5.3 (2026-11-10)

보완 Claude(뼈대 Solar Pro 4). 생성 문서는 바뀌지 않음(고정 입력 26건의 header·section XML·md 바이트 동일 확인).

- 보고서 빌드 때 조립(compose)을 2번 하던 것을 1번으로 — 분량 예측(`pages.estimate`)이 임시 HWPX를 만들지 않고 이미 조립한 XML을 받는다. 3쪽 보고서 build_document 0.156초 → 0.080초. polish=True·logo_path가 있는 경우는 종전 경로 그대로.
- 규칙 JSON(공통·기관·문단위간격·참고머리)을 매번 읽던 것을 경로별 캐시(`engine/blank.py` `load_json`) + 반환 시 deepcopy로 — 호출자가 반환 dict를 고쳐도 다음 호출에 새지 않음(테스트 8건). 기관 보고서 1회 빌드 규칙 파일 열람 10회 → 첫 빌드 2회·이후 0회, `list_ministries` 104회 → 0회.
- `build_from_structure`에 target_pages 전달, polish 경로에 style·report_kind 전달(빠져 있던 통로).
- 죽은 코드·중복 정의 정리(PR #13): 호출 0인 함수 13개, 번호 접두사 정규식 3벌 → 1벌(기안문·마크다운 경로도 "Ⅺ."·"XIII." 제거), `_convert_table_titles`·`_unroll_table_merges` 단일 정의, 기안문 금액 경고 판정 한 곳. −359줄.

## 0.5.2 (2026-11-08)

> 작성: Claude(데모 검토서에서 찾은 쪽 나눔 문제).

### 짧은 표는 쪽을 나누지 않음
- 표가 모두 '줄 단위로 나눔(pageBreak TABLE)·떠 있는 개체'라, 쪽 끝에 표 제목과 머리 줄만 남고 본문 행이 다음 쪽으로 넘어가는 일이 있었다.
- 줄바꿈까지 넣은 높이가 본문 높이의 1/3(23,000 HWPUNIT) 이하인 표는 글자처럼 취급(treatAsChar=1)·나누지 않음(NONE)으로 만든다. 표 제목(keepWithNext)과 함께 통째로 다음 쪽으로 넘어간다. 긴 표는 종전처럼 줄 단위로 나누고 머리 줄을 반복한다.
- 떠 있는 표에 '나누지 않음'만 주면 표만 다음 쪽으로 가고 뒤 본문이 앞으로 올라와 순서가 바뀐다(한글 실측) — 그래서 글자처럼 취급을 같이 바꿨다.
- 분량 예측 정답 중 표 묶음 3개(table_013·022·024)를 한글에서 다시 쟀다(쪽수 같음, 마지막 쪽 채움만 바뀜). 대조 문서는 종전 값 그대로. `tests/test_short_table_no_split.py`.

## 0.5.1 (2026-11-08)

> 작성: 명세·정답 테스트(한글 실측 54개) Claude, 코드 Solar Pro 4(2회), 검증 Claude.

### 분량 예측(estimate)을 한글 배치 규칙으로
- pages.estimate가 근사 보정 상수(W_EST 0.8, 쪽 높이 73000 등) 대신 실제 생성 HWPX를 임시 파일로 만든 뒤 header.xml(charPr·paraPr·글꼴)과 section0.xml(문단·표)을 읽어 한글 배치 규칙대로 쌓아 예측한다.
- 본문_쪽수·마지막쪽_채움·본문_줄수·전체_쪽수 키와 뜻은 그대로. 여러 쪽 문서에서 실제보다 1쪽 적게 나오던 문제 해결(한글 실측 54개: 이전 29개 일치 → 54개 모두 쪽수 일치, 마지막 쪽 채움 ±2%).
- 표 행 높이 = max(hp:cellSz height, 내용 높이). 내용 높이는 셀 안 문단을 셀 안쪽 폭(cellSz width − cellMargin left − right)의 1.03배로 줄 나눔해 쌓은 높이(마지막 줄 줄간격 몫 제외) + cellMargin top + bottom.
- 외톨이줄 보호(widowOrphan=1): 쪽을 넘길 때 앞 쪽에 1줄만 남으면 문단 전체를 다음 쪽으로. keepWithNext(소제목·표 제목): 문단 전체 + 다음 문단 첫 줄(다음 문단이 외톨이줄 보호면 첫 2줄)이 지금 쪽에 다 들어가지 않으면 이 문단부터 새 쪽으로.
- check_structure에 report_kind 인자 추가('standard'·'internal'). 이제 내부 결재 보고서 분량을 내부 결재 기준으로 잰다.

### 간소화 모드 번호 확장
- 소제목 번호가 11개 이상이면 Ⅰ~Ⅹ(유니코드) → Ⅺ Ⅻ(유니코드) → XIII·XIV…(ASCII 로마 숫자)로 이어짐. 13번째부터 IndexError 대신 로마 숫자 ASCII.
- 중항목·소항목 아래 번호(가.~하.)가 14개를 넘으면 거.·너.·더.·러.·머.·버.·서.·어.·저.·처.·커.·터.·퍼.·허. → 고.·노.·도.·로.·모.·보.·소.·오.·조.·초.·코.·토.·포.·호. 순으로 이어짐.
- _EXISTING_NUMBER_RE(_strip_existing_number)도 Ⅺ Ⅻ, ASCII 로마 숫자, 거~허/고~호 번호를 지우도록 확장.
- ASCII 로마 숫자는 XIII. 이후 번호 모양일 때만 지운다. 문장 앞 약어(IT. DX. VIP.)는 그대로(CodeSolar 리뷰 반영).

## 0.5.0 (2026-11-07)

### 1쪽 보고서와 분량 점검
- `check_structure`·`build_document`: 보고서면 `분량`(본문 쪽수·마지막 쪽 채움·본문 줄 수·전체 쪽수)을 돌려준다. 생성 엔진과 같은 글자 크기·줄 간격·문단 간격·표 칸 폭으로 계산한다.
- `target_pages` 인자: 목표 쪽수를 주면 '본문이 N쪽을 넘음', '덜 참(80% 미만)', '주요 내용을 받칠 붙임이 없음'을 경고한다. 경고가 오면 사용자 AI가 고쳐 다시 만든다.
- 쪽수 예측은 맥 한컴오피스 한글 실측(이 서식은 1쪽에 20줄, 21줄부터 2쪽)으로 맞췄고, 정답에 쓰지 않은 검증 문서 7개도 쪽수가 일치했다. 간소화 모드·내부 결재 서식은 실측 정답이 없다.
- 작성 가이드 `[1쪽 보고서]`: 되묻지 않게 꽉 채우기, □마다 무엇·왜·누가·언제·숫자, 나열은 표, 주요 내용마다 붙임, 마지막 붙임은 출처, 예상 질문 3개로 점검.

### 문서 서식
- 문장 끝 '붙임 N'·'참고 N' 표시: 끝맺음이 '~가동', '~확대'처럼 무엇이든 상자로 그린다(이전에는 '~정·~함·~임' 등 뒤에서만). 문장 중간 '붙임 1과 같이'는 그대로 글자.
- 보고서 표: 위·아래 0.5mm, 머리 행 아래 이중선, 안쪽 0.12mm, 좌우 바깥선 없음, 머리 행 #F2F2F2(공무원 문서 실측 기준). 보도자료 표는 기관별 서식 그대로.
- 표 본문 칸 정렬을 열 단위로: 열의 칸이 모두 한 줄이면 가운데, 한 칸이라도 줄이 바뀌면 열 전체 양쪽 정렬(짧은 숫자·날짜 칸은 가운데).

### 작성 가이드
- 핵심 문구·결과·수치는 굵게(한 문장 1~3곳), 약어·용어·규모는 `*`·`**` 각주, □는 한 문장에 주체·언제·무엇·결과 압축, 개요는 2열 표, 첫 장이 보고의 전부.

- 개발: 코드는 Solar Pro 4, 정답 테스트·한글 실측 자료·가이드 문구와 검수 중 보완은 Claude, 리뷰 CodeSolar.

## 0.4.1 (2026-10-28)
- 보도자료 머리: 기관 서식에 테두리가 있으면 한 상자 안에 [기관명 | 보도자료 | 빈칸]으로 — 로고 그림 대신 기관명을 글로 쓴다(빈 '기관 로고' 자리표시 대신).
- 보도자료 제목 상자: 부제 칸이 없는 기관 서식은 부제를 제목 상자 안, 제목 아래에 '- 부제'(왼쪽 정렬, 내어쓰기)로 넣는다. 이전에는 상자 밖에 가운데 정렬 '- 부제 -'로 나와 줄이 넘어가면 끝의 '-'가 혼자 남았다.
- 제목 상자 높이: 부제 칸 없는 서식은 내용 높이로(제목만 있을 때 빈 공간 줄임).
- 보도자료 초안(draft_press_structure): 문단식 기관은 세부 문장을 ○ 줄로 쪼개지 않고 같은 문단에 이어 쓰고, 배경 문장도 한 문단으로. 본문에 이미 나온 숫자는 '주요 수치' 참고 표로 되풀이하지 않음. 참고 자료가 있으면 제목이 '참고 1'로 바뀌던 버그 수정.
- 작성 가이드 16번(기사체 말투)과 과학기술정보통신부 예시 문장을 실제 보도자료 말투로 고침.
- doc_type을 비우면 구조 키로 문서 종류를 정함(release·subtitles → 보도자료, to·sender → 기안문). 보도자료 구조가 보고서로 만들어지던 문제 방지.
- 도구 입력 오류 메시지를 MCP 클라이언트(모델)에 그대로 전달. 이전에는 MCP SDK가 'Error executing tool build_document'만 돌려줘, 모델이 원인을 모른 채 같은 호출을 되풀이했음.
- ministry에 자주 쓰는 약칭(과기정통부·행안부·식약처 등)을 주면 정식 기관명으로 바꿔 처리.
- 개발: 기존 뼈대는 Solar Pro 4, 이번 보완은 Claude.

## 0.4.0 (2026-10-28)

### 신규 기능
- `draft_press_structure(facts, ministry)`: 사실 메모(dict 또는 JSON 문자열)를 보도자료 구조 JSON 초안으로 옮긴다. 메모에 없는 문장·숫자·이름을 만들지 않으며, 리드·인용·표·참고 자료를 국립국어원 지침과 정책브리핑 실측에 맞게 배치한다.
- `get_writing_guide(doc_type='press_release', ministry)`: 보도자료 작성 방법(리드·제목·인용·숫자·쉬운 말), 사실 메모 양식(facts_template)·필드 설명(facts_fields), 종류별 순서(types_order), 기관별 가상 예시(facts·structure)를 함께 제공한다.
- `check_structure`·`build_document`의 보도자료 작성 점검(E1~E18): 리드 누가·언제·완결·길이·인용, 제목 과장·마침표, 부제 수, 숫자 단위·단위 띄어쓰기, 외국 문자 먼저, 약어 풀이, 쉬운 말, 권위적 표현, 종결 혼용, 명사형 종결, 긴 문장.
- `ministry` 인자: `check_structure(structure, doc_type, ministry=기관)`으로 보도자료 작성 점검을 수행한다. `build_document`는 자기 ministry를 check에 넘긴다.
- `_josa(word, pair)`: 조사 붙이기 모듈 함수 — 끝 공백·괄호·따옴표를 번갈아 떼고 마지막 글자로 판단(한글 받침·숫자 끝자리·라틴 L·M·N·R).
- 보도참고자료·설명자료·해명자료도 `draft_press_structure`로 구조 초안을 만들 수 있다(문제 사안→입장→근거 순서, 리드는 만들지 않음).
- 머리 이름 기본값: `kind`가 없으면 템플릿 서식 표본과 관계없이 '보도자료'를 머리에 찍는다(서식 표본이 보도참고·보도설명자료였던 9개 기관 — 과학기술정보통신부·공정거래위원회·국세청 등 — 이 '보도참고자료'·'보도설명자료'로 나오던 것 바로잡음).
- 담당 부서 유지: `placeholder_contact=True`이고 people이 비어도 dept가 있으면 그 부서명을 유지하고 people만 자리표시로 채운다.

### 데이터
- `korean_report_hwpx/guides/press_writing.json`: 국립국어원 지침 5종(G20·R20·G11·H22·E14), 정책브리핑 2,667건 실측(C), 가이드 규칙 문장 15개, 사실 메모 양식·필드, 종류별 설명, 과학기술정보통신부·행정안전부 가상 예시 2건(facts·기대 structure), 작성 점검용 정규식·단어 목록·한도.

### 문서
- README·README-EN: 도구 표에 `draft_press_structure` 추가, "보도자료 작성 방법" 단락과 사실 메모 예시, 출처 목록 추가.
- SPEC: `docs/SPEC_press_writing_guide.md`에 전체 사양 기록.

### 호환성
- 보고서·기안문 점검과 동작은 그대로(빈 줄 없음·고정 문단 위 간격 유지). 기존 테스트 전부 통과.
- 보도자료 본문 문단 간격 복원: `Composer.blocks`의 계층 사이 빈 줄을 `rules/<기관>.json` gaps 값대로 넣고(`gap_pt`가 None이면 없음), `Composer.item`의 문단 위 간격(prev)을 `rules/_문단위간격.json` 기관값(그 계층)→전체값(모두 0)으로 적용한다. 예: 행정안전부 p 문단 위 1000·p↔p 빈 줄 없음, 과학기술정보통신부 p 문단 위 0·p↔p 빈 줄 1개(10pt).
- `EXAMPLE_PRESS` 상수는 제거하고 PRESS_GUIDE 예시로 대체(`writing_guide_prompt`도 같은 값 사용).

### 기안문 항목 내어쓰기
- 항목 번호(1.·가.·1) 등)와 붙임 뒤에 탭을 넣고 내어쓰기와 같은 위치에 탭을 두어, 둘째 줄이 번호 뒤 첫 글자 아래에서 시작한다(글꼴 너비와 관계없음).

### 쪽 설정(편집 용지)
- 기안문에도 구역 정의(`<hp:secPr>`·`<hp:pagePr>`·`<hp:margin>`)를 넣어 한글이 기본 편집 용지(좌우 30mm, 본문폭 150mm)로 열리던 문제를 수정. 보고서와 같은 방식으로 첫 문단 첫 글자 조각에 `B.sec_pr(page)`를 삽입.
- 보고서 공통 여백을 위·아래 10mm·머리말·꼬리말 15mm에서 위·아래 15mm·머리말·꼬리말 10mm로 정정(정책브리핑 2,667건 중 최빈값 1,817건).
- 기관 템플릿 19곳(`templates/<기관>.json`)의 쪽 여백이 그 기관 보도자료 최빈값과 달라 최빈값으로 바꿈(표본 10건 미만 기관은 공통값). 과학기술정보통신부는 118건 중 100건, 행정안전부는 135건 중 120건이 위15·아래15·머리말10·꼬리말10. 근거는 `rules/_쪽설정.json`의 `기관값`.
- 표(`<hp:tbl>`) 폭이 모든 문서 종류에서 본문폭(width − left − right, 170mm) 이하인지 테스트로 확인.

### 개발
- 기존 뼈대는 Solar Pro 4, 이번 보완 중 기안문 항목 위치·붙임 내어쓰기는 Claude. 보도자료 작성 가이드 데이터·명세·정답 테스트는 Claude, 구현은 Solar Pro 4.

## 0.3.2 (2026-10-25)

- `check_structure`·`build_document`·`build_from_structure`: `structure`를 JSON 문자열로 줘도 처리(일부 모델이 객체 인자를 문자열로 넘겨 입력 검증에서 거부되던 문제). JSON이 아니거나 객체가 아니면 이유를 담은 오류
- Solar Pro 4 작성, CodeSolar·Claude 검수

## 0.3.1 (2026-10-25)

- `build_document`·`build_from_structure`: `out_path`에 폴더를 주면 그 안에 기본 파일 이름(`{기관 또는 공통}_{종류}_{제목}.hwpx`)으로 저장 — 이전에는 `IsADirectoryError`로 문서가 만들어지지 않음. 확장자 없는 이름은 `.hwpx`를 붙이고, 없는 부모 폴더는 만듦
- `server.json` 버전 표기를 패키지 버전과 맞춤(0.2.1로 남아 있던 것)
- Solar Pro 4 작성, CodeSolar·Claude 검수

## 0.3.0 (2026-10-14)

### 신규 기능
- 기안문·시행문(별지 제1호서식) 지원: `doc_type="official"`로 두문·본문·붙임·끝 표시·결문을 기관 서식 HWPX로 생성
- 항목 번호 자동 부여: l1→1. / l2→가. / l3→1) / l4→가) / l5→(1) / l6→(가) (행정업무규정 시행규칙 제2조①)
- 날짜 정규화: YYYY-MM-DD·YYYY.MM.DD → YYYY. MM. DD. (영 제7조⑤)
- 금액 한글 병기 경고: `금\d` 또는 `\d{1,3}(,\d{3})+원` 형태 뒤에 `(금…원)`이 없으면 `warnings` 통지 (시행규칙 제2조②)
- 결문: 발신 명의·수신자란·결재란 표(마크+직위+의견)·협조자·시행/접수·주소·연락처·공개구분 렌더링
- `get_writing_guide`·`check_structure`·`build_document`·`list_ministries`·`get_rules` 모두 `doc_type="official"` 지원
- `export_markdown=True` 시 기안문 내용도 .md로 저장

### 코드 정리
- `server.py`와 `engine/report.py`에 중복된 `_strip_existing_number`·`_simplify_numbers`·`_add_table_numbers`를 `engine/report.py` 한 곳으로 통합, server는 import해서 사용
- 간소화 모드 s_for_md 조립(표 병합 풀어쓰기 등)을 `_prepare_simplified_for_md` 함수로 추출하여 report·official이 공유
- `_unroll_table_rows`를 `engine/official.py`로 이동, server는 `O._unroll_table_rows`로 호출

### 문서
- README·README-EN: 문서 종류 표에 기안문 지원 추가, 구조 예시·작성 규칙·유의 사항 업데이트
- pyproject.toml: 0.2.1 → 0.3.0

### 근거
- 「행정업무의 운영 및 혁신에 관한 규정」 제7조④⑤⑥, 같은 규정 시행규칙 제2조·제4조·제6조(법제처 2026-01-01 시행본)
- 서식 값: `rules_official/_공통.json`(코드 상수 금지)

### 호환성
- 기존 보고서·보도자료 동작 변경 없음. 기존 테스트 733개 전부 통과.
