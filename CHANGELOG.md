# Changelog

## 0.4.1 (2026-10-28)
- 보도자료 머리: 기관 서식에 테두리가 있으면 한 상자 안에 [기관명 | 보도자료 | 빈칸]으로 — 로고 그림 대신 기관명을 글로 쓴다(빈 '기관 로고' 자리표시 대신).
- 보도자료 제목 상자: 부제 칸이 없는 기관 서식은 부제를 제목 상자 안, 제목 아래에 '- 부제'(왼쪽 정렬, 내어쓰기)로 넣는다. 이전에는 상자 밖에 가운데 정렬 '- 부제 -'로 나와 줄이 넘어가면 끝의 '-'가 혼자 남았다.
- 제목 상자 높이: 부제 칸 없는 서식은 내용 높이로(제목만 있을 때 빈 공간 줄임).
- 보도자료 초안(draft_press_structure): 문단식 기관은 세부 문장을 ○ 줄로 쪼개지 않고 같은 문단에 이어 쓰고, 배경 문장도 한 문단으로. 본문에 이미 나온 숫자는 '주요 수치' 참고 표로 되풀이하지 않음. 참고 자료가 있으면 제목이 '참고 1'로 바뀌던 버그 수정.
- 작성 가이드 16번(기사체 말투)과 과학기술정보통신부 예시 문장을 실제 보도자료 말투로 고침.
- doc_type을 비우면 구조 키로 문서 종류를 정함(release·subtitles → 보도자료, to·sender → 기안문). 보도자료 구조가 보고서로 만들어지던 문제 방지.
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
