# SPEC: out_path에 폴더를 주면 그 안에 저장

## 문제
`build_document(out_path=".")`나 `out_path="/작업/폴더"`처럼 폴더를 주면 `IsADirectoryError`로 문서가 만들어지지 않는다. AI 에이전트는 "작업 폴더에 저장"을 흔히 이렇게 넘긴다.

## 바꿀 것 (`korean_report_hwpx/server.py`의 `_dst`만)
`_dst(ministry, title, out_path, doc_type)`가 돌려주는 경로 규칙:
1. `out_path`가 비어 있으면 지금처럼 `out_dir()/기본이름.hwpx`.
2. `out_path`가 이미 있는 폴더이거나 `/`(또는 os.sep)로 끝나면 → 그 폴더 안에 기본 파일 이름(`{기관 또는 공통}_{LABEL}_{제목 정리 30자}.hwpx`, 지금과 같은 규칙).
3. 그 밖에 확장자가 없으면 `.hwpx`를 붙인다(`보고서` → `보고서.hwpx`).
4. `~`는 지금처럼 풀어 준다.
5. 돌려주기 전에 부모 폴더가 없으면 만든다(`mkdir(parents=True, exist_ok=True)`).

기본 파일 이름을 만드는 식은 한 곳(작은 함수)에 두고 1·2가 같이 쓴다.

## 하지 말 것
- 다른 함수·서식 코드 수정 금지, 테스트 파일 수정 금지
- build_document 독스트링의 out_path 설명만 한 줄 추가 가능: "폴더를 주면 그 안에 기본 이름으로 저장"

## 통과 기준
`tests/test_out_path.py` + 기존 테스트 전부 통과.
