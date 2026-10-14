# Changelog

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
