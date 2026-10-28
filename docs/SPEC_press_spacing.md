# SPEC — 보도자료 본문 문단 간격 되살리기 (0.4.0)

문제(한글 화면 대조): 0.2.1에서 보고서 서식을 정리하며 `compose.Composer.blocks`의 계층 사이 빈 줄을 모든 문서에서 없애고(`14차 Fix: g = None`), `item`의 문단 위 간격을 보고서 값(l1 1000, l2·l3 500, note·ref 300, p 0)으로 고정했다. 보도자료도 같은 Composer를 써서, 문단식 기관 보도자료가 문단 사이 간격 없이 붙어 나온다. 실제 보도자료는 기관마다 ① 빈 줄(과학기술정보통신부 p→p 10pt 빈 줄 561건) 또는 ② 문단 위 간격(행정안전부 p 문단 위 10pt 1,088/1,324건, p→p 빈 줄 없음 924건)으로 문단을 띄운다.

규칙값(Claude 작성, 읽기만):
- 빈 줄: `rules/<기관>.json`의 `gaps`(기존 값, `Composer.gap_pt`가 이미 읽음 — 빈 줄이 없는 경우가 더 많으면 None)
- 문단 위 간격: `rules/_문단위간격.json` — `기관[<기관>][계층]`, 없으면 `전체[계층]`(모두 0). 계층 이름 p·l1·l2·l3·note·ref. 근거 건수는 `근거`.

`tests/`·`docs/`·`korean_report_hwpx/rules*/`·`templates/`·`guides/` 수정 금지.

## 1. 보도자료에만 적용
- `compose.Composer`(보도자료)에서만 바꾸고, 보고서(`report.ReportComposer`)·기안문(`official.OfficialComposer`)의 지금 동작(빈 줄 없음, 고정 문단 위 간격)은 그대로 둔다. 하위 클래스 판별은 클래스 속성(예: `PRESS_SPACING = True`를 Composer에, 하위 클래스에서 False) 등으로 한다.
- `blocks`: 보도자료이면 이전 블록과 이번 블록 사이에 `self.gap(prev, lv)`(0.2.0까지의 동작: 규칙 `gaps`의 `"{앞}>{뒤}"`, 상자 뒤는 `box_gap_pt`)를 넣는다. `gap`이 None이면 넣지 않는다. caption·h 앞은 지금처럼 caption·heading 자체의 문단 위 간격으로 처리(빈 줄 없음).
- `item`: 보도자료이면 문단 위 간격 = `_문단위간격.json`의 기관값(그 계층) → 없으면 전체값. 보고서·기안문은 지금 값(l1 1000, l2·l3 500, note·ref 300, p 0).

## 2. 확인
- 행정안전부(문단식): 본문 p 문단의 문단 위 간격 1000, p와 p 사이 빈 줄 없음.
- 과학기술정보통신부(문단식): 본문 p 문단의 문단 위 간격 0, p와 p 사이 빈 줄 1개(10pt).
- 보고서·기안문 생성 결과는 바뀌지 않는다(기존 테스트).

## 완료 조건
`tests/test_press_spacing.py` 전부 통과(수정 금지) + 기존 테스트 전부 통과.
