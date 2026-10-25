# SPEC: structure를 JSON 문자열로 받아도 처리

## 문제
일부 모델(Solar Pro 4 등)은 객체 인자를 `"structure": "{...}"`처럼 JSON 문자열로 넘긴다. 지금은 MCP 입력 검증에서 `rejected arguments: ['structure']`로 거부되어, 모델이 내용을 줄인 문서를 만들거나 다른 방법으로 우회한다.

## 바꿀 것 (`korean_report_hwpx/server.py`)
1. `check_structure`·`build_document`·`build_from_structure`의 `structure` 타입을 `dict | str`로.
2. 공통 함수 하나(예: `_as_structure(structure)`)로: 문자열이면 `json.loads`, 결과가 dict가 아니거나 JSON이 아니면 `ValueError("structure는 JSON 객체(또는 그 문자열)여야 함: ...")`. 세 함수가 맨 앞에서 이 함수를 부른다.
3. 독스트링에 "structure는 JSON 문자열로 줘도 됨" 한 마디.

## 하지 말 것
서식·엔진 코드 수정 금지, 테스트·명세 수정 금지.

## 통과 기준
`tests/test_structure_json_string.py` + 기존 테스트 전부.
