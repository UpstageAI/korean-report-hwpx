# SPEC — 쪽 설정(편집 용지)을 모든 문서 종류에 (0.4.0, 보도자료 작성 가이드와 같은 배포)

문제: 기안문(`doc_type="official"`) 결과에는 구역 정의(`<hp:secPr>`·`<hp:pagePr>`·`<hp:margin>`)가 없어 한글이 기본 편집 용지(좌우 30mm, 본문폭 150mm)로 연다 → 170mm 표가 넘친다. 보고서 공통 서식은 위·아래 10mm, 머리말·꼬리말 15mm로 실제 문서와 위아래가 뒤바뀌어 있다. 기관 템플릿 16곳은 쪽 여백이 그 기관 최빈값과 달랐다(Claude가 템플릿 데이터를 기관 최빈값으로 고침, 이번 커밋에 포함).

규칙값: `korean_report_hwpx/rules/_쪽설정.json`(Claude 작성, 읽기만)
- `default`: A4 210×297(59528×84188), 좌우 20mm(5669), 위·아래 15mm(4252), 머리말·꼬리말 10mm(2835), gutter 0
- `text_width`: 본문폭 = width − left − right = 48190(170mm)
- `출처`: 정책브리핑 보도자료 원본 2,667건 중 A4·좌우 20mm 2,640건, 위15·아래15·머리10·꼬리10 1,817건(최빈), 과학기술정보통신부 118건 중 100건, 행정안전부 135건 중 120건 등
- `기관값`: 기관별 적용 값과 근거(기관 최빈값 n/N건 또는 표본 10건 미만 → 공통값)

`tests/`·`docs/`·`korean_report_hwpx/rules*/`·`templates/`·`guides/` 수정 금지.

## 1. 쪽 설정 고르기 (한 곳)
- `engine/blank.py`에 `page_settings(org="")` 추가: `rules/_쪽설정.json`의 `default`를 바탕으로, `org`가 있고 `templates/<org>.json`이 있으면 그 `page`의 `width`·`height`·`left`·`right`·`top`·`bottom`·`header`·`footer`·`gutter`가 덮어쓴다. dict 반환.
- `sec_pr(page)`의 빠진 키 기본값은 코드 상수(4252·2834 등)가 아니라 `_쪽설정.json` `default`에서 가져온다.
- 보고서(`report.py`, 기관 있음·없음, standard·internal·simplified), 보도자료(`compose.py`), 기안문(`official.py`)이 모두 `page_settings(org)`로 쪽 설정을 정한다. 기안문은 기관 템플릿을 쓰지 않으므로 `default`.

## 2. 기안문에 구역 정의 넣기
- `official.py` 결과 section0.xml 첫 문단의 첫 글자 조각에 `B.sec_pr(page)`(보고서와 같은 방식: `<hp:run charPrIDRef="0">{sec}</hp:run>`)를 넣는다. 문서 전체에 `<hp:secPr`는 정확히 1개.
- 기안문 본문폭·표 폭 계산(`text_w` 등)도 같은 `page`로 한다.

## 3. 표 폭
- 모든 문서 종류에서 표(`<hp:tbl>`)의 `<hp:sz width>`는 그 문서의 본문폭(width − left − right) 이하. 넘으면 본문폭으로 줄이고 칸 폭을 같은 비율로 줄인다(지금 넘는 표가 없으면 계산만 확인).

## 4. 문서
- README·README-EN에 "서식 근거" 단락: 쪽 설정 A4·좌우 20mm·위아래 15mm·머리말·꼬리말 10mm와 위 출처 숫자(2,667건 중 2,640건·1,817건), 기관 템플릿이 있으면 기관값.
- CHANGELOG 0.4.0에 한 줄(기안문 쪽 설정 누락 수정, 보고서 공통 여백 수정, 기관 여백 최빈값 반영).

## 완료 조건
`tests/test_page_settings.py` 전부 통과(수정 금지) + 기존 테스트 전부 통과.
