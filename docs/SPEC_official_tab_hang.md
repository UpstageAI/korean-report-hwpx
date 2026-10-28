# SPEC — 기안문 항목 내어쓰기를 탭으로 정확히 맞추기 (2026-10-28)

## 배경
기안문(별지 제1호서식) 본문 항목(1. 가. 1) …)과 붙임의 둘째 줄이 항목 내용 첫 글자 밑에 정확히 오지 않는다. 지금은 내어쓰기 값을 번호 글자 폭 추정(영문·숫자 0.55자, 한글 1자)으로 정해 "1. "·"가. "·"1) "마다 실제 폭과 어긋난다.
공문서작성법(「표시위치 및 띄우기」): 항목 내용이 한 줄 이상이면 항목 내용의 첫 줄 첫 글자에 맞추어 정렬한다(Shift+Tab). 파일로는 **번호 뒤 탭 + 같은 거리의 탭 위치 + 같은 거리의 내어쓰기**로 표현하면 글자 폭과 상관없이 정확히 맞는다.

대상: `korean_report_hwpx/engine/official.py`(OfficialComposer 본문·붙임), `korean_report_hwpx/engine/hwpx_doc.py`(`Hwpx.text`), 필요하면 `korean_report_hwpx/engine/compose.py`(문단 모양·탭 모양 생성, 다른 문서 종류 동작은 바꾸지 않음).
정답 테스트: `tests/test_official_tab_hang.py`(새, 수정 금지). 기존 테스트 전부 통과(`tests/test_public_tree.py`·`tests/test_press_writing.py`는 작업 트리의 다른 진행 중 파일 때문에 이미 실패 — 판단에서 뺀다).

## 1. 값 (본문 글자 크기 pt = 규칙 body.pt, 한 글자 C = pt × 100 HWPUNIT)
- 항목 내어쓰기 거리 H = 2 × C (한글 2자). 모든 계층 같은 값.
- 항목 계층 level(0부터)의 왼쪽 여백 left = level × (indent_per_level / 2) × C (지금과 같음: 0, C, 2C …).
- 붙임: 라벨("붙임") 2자 + 띄움 1자 = 3C 지점에 번호, 번호 뒤 탭으로 5C 지점에 명칭.

## 2. 본문 항목 문단 (l1~l6, 번호가 붙는 경우)
- 문단 글: 번호(예 `1.`, `가.`, `1)`, `가)`, `(1)`, `(가)`, `①`, `㉮`) **바로 뒤에 탭**, 그 뒤 내용. 번호와 탭 사이에 공백 없음.
- 탭은 `<hp:t>` 안의 `<hp:tab width="…" leader="0" type="1"/>` 요소(한글 원본 형식). width는 H − 번호 폭 추정(최소 100) — 한글이 열 때 다시 계산하므로 근사값으로 충분.
- 문단 모양: 왼쪽 여백 left, 내어쓰기 intent = −H, 탭 모양 `tabPrIDRef` = 아래 탭 모양.
- 탭 모양 `<hh:tabPr id="…" autoTabLeft="1" autoTabRight="0">` 안에 탭 위치 하나: `<hp:switch><hp:case hp:required-namespace="http://www.hancom.co.kr/hwpml/2016/HwpUnitChar"><hh:tabItem pos="H" type="LEFT" leader="NONE" unit="HWPUNIT"/></hp:case><hp:default><hh:tabItem pos="2H" type="LEFT" leader="NONE"/></hp:default></hp:switch>` (한글 원본과 같은 모양: default는 2배 단위). 탭 위치는 문단 왼쪽 여백 기준.
- `<hh:tabProperties itemCnt="…">`는 실제 탭 모양 수와 같게.
- 항목이 하나뿐이어서 번호를 붙이지 않는 문단(이미 구현됨)은 탭 없음, 내어쓰기 0.

## 3. 붙임
- 둘 이상: 첫 문단 글 `붙임{label_gap}1.` + 탭 + 명칭, 이어지는 문단 글 탭 + `2.` + 탭 + 명칭(마지막 문단 끝에 지금처럼 `{gap}끝.`).
- 문단 모양: 왼쪽 여백 0, 내어쓰기 −5C, 탭 모양 = 탭 위치 두 개 3C·5C(위 형식, 각각 case·default).
- 하나: 지금처럼 `붙임{label_gap}명칭{gap}끝.`, 내어쓰기 −3C(탭 없음).

## 4. `Hwpx.text`
`<hp:tab …/>`를 공백 한 칸으로 읽는다(`<hp:nbSpace/>`와 같은 방식). 그래서 기존 테스트의 "1. 국산"·"붙임  1. 실증"·줄 앞 공백 제거 후 "2. 실증" 같은 글 비교가 그대로 맞는다.

## 5. 바꾸지 않는 것
보고서·보도자료 경로, 규칙 파일(rules*/), tests/(새 정답 테스트 포함)·docs/ 수정 금지.
