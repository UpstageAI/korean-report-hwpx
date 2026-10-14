# SPEC h1 — 기안문(시행문) 서식 추가 + 코드 정리 (2026-10-14, korean-report-hwpx 0.3.0)

근거(법제처 2026-01-01 시행본, law_article로 확인): 「행정업무의 운영 및 혁신에 관한 규정」 제7조④⑤(숫자는 아라비아, 날짜는 `2026. 10. 14.`, 시각 `14:30`), 같은 규정 시행규칙 제2조①(항목 구분 1., 가., 1), 가), (1), (가), ①, ㉮)·②(금액 `금113,560원(금일십일만삼천오백육십원)`), 제3조(별지 제1호서식), 제4조(두문·본문·결문 구성, 수신란, 붙임, "끝" 표시, 결문 항목), 제6조①(발의자 ★, 보고자 ⊙)·③("(의견 있음)"). 서식 값은 `rules_official/_공통.json`(Claude 작성, 수정 금지)에서 읽는다(코드 상수 금지). `tests/` 아래 파일·이 문서 수정 금지.

## A. 새 문서 종류 `doc_type="official"` — 기안문·시행문(별지 제1호서식)
`build_document`·`check_structure`·`get_writing_guide`·`list_ministries`·`get_rules`가 `official`을 받는다. 구조:
```json
{
  "org": "행정안전부",                 // 두문 행정기관명(필수). 상급기관 병기는 "국무조정실 ○○위원회"처럼 한 줄로
  "to": "수신자 참조",                 // 필수. "내부결재" | "○○장관(○○과장)" | "수신자 참조"
  "via": "",                           // 경유(선택). 있으면 "(경유)" 줄에 표시
  "title": "2026년 ○○ 계획 알림",      // 필수
  "body": [ {"type": "l1", "text": "..."}, {"type": "l2", "text": "..."}, {"type": "table", "rows": [[...]]}, {"type": "lines", "lines": [...]} ],
  "attachments": ["○○ 계획서 1부.", "○○ 명단 1부."],   // 선택
  "recipients": ["○○부장관", "○○청장"],                // to가 "수신자 참조"일 때 결문 발신 명의 다음 줄에 표시
  "sender": "행정안전부장관",            // 발신 명의(필수)
  "approval": {                          // 결재란(필수: drafter·approver)
    "drafter":   {"title": "주무관", "name": "", "mark": ""},     // mark: "★"(발의자) | "⊙"(보고자) | ""
    "reviewers": [{"title": "과장", "name": "", "opinion": false}],
    "approver":  {"title": "국장", "name": ""},
    "coordinators": [{"title": "○○과장"}]
  },
  "doc_no": {"issue": "○○과-1234", "issue_date": "2026. 10. 14.", "receive": "", "receive_date": ""},
  "contact": {"zip": "30112", "address": "세종특별자치시 ○○로 00", "homepage": "www.mois.go.kr",
              "phone": "044-000-0000", "fax": "044-000-0001", "email": "○○○@korea.kr", "disclosure": "공개"}
}
```

렌더링(위→아래, 값은 규칙 파일에서):
1. **두문**: `org` 가운데 정렬 큰 글씨(규칙 `org`). 다음 줄 "수신  {to}". `via`가 있으면 "(경유)  {via}" 줄. `to`가 "내부결재"면 그대로 "수신  내부결재"(제4조②2호가목)
2. **본문**: "제목  {title}" 줄. 본문 블록:
   - `l1`~`l6` 항목 번호를 자동 부여: 1. / 가. / 1) / 가) / (1) / (가) (제2조①). 같은 계층 안에서 순서대로 증가, 상위 계층이 바뀌면 하위 계층 번호 초기화. text에 이미 같은 형태 번호가 있으면 떼고 다시 붙임(기존 `_strip_existing_number` 재사용). 둘째 계층부터 상위 계층 번호 시작 위치에서 2타(한 글자) 오른쪽에서 시작(들여쓰기 규칙 `indent_per_level`)
   - `table`·`lines`는 보고서와 같은 렌더링
   - 금액 표기 점검: `금\d` 또는 `\d{1,3}(,\d{3})+원` 뒤에 `(금…원)` 한글 병기가 없으면 warnings에 "금액 한글 병기 필요(시행규칙 제2조②): …" (제2조②). 생성은 막지 않음
3. **붙임**: `attachments`가 있으면 본문 끝난 다음 줄에 "붙임" 표시. 1개면 "붙임  {명칭}", 2개 이상이면 "붙임  1. {명칭}" / "      2. {명칭}"(제4조④, 제2조①)
4. **"끝" 표시**(제4조⑤): 본문(붙임이 있으면 붙임)의 마지막 글자에서 한 글자(공백 2타) 띄우고 "끝.". 본문이 `table`로 끝나고 붙임이 없으면 표 아래 왼쪽 기본선에서 한 글자 띄운 "끝." 줄을 따로 둔다. 문서 전체에서 "끝."은 정확히 한 번
5. **결문**(별지 제1호서식 실물 기준, 2026-10-14 수정): `sender` 가운데 정렬 큰 글씨(규칙 `sender`). `to`가 "수신자 참조"면 다음 줄 "수신자  {recipients를 ', '로}". 그 아래 **회색 구분 띠**, 그 아래 **칸 선 없는 줄글**로 ① 기안자·검토자·결재권자의 "{mark}{직위}{(의견 있음)}  {성명}"을 가로로 나눠 한 줄(서명 칸 줄 없음) ② "협조자  {직위들}"(없으면 라벨만) ③ "시행  {issue} ({issue_date})" 와 접수 값이 있을 때 같은 줄 오른쪽 "접수  {receive} ({receive_date})" ④ "우 {zip}  {address}  /  {homepage}" ⑤ "전화번호 {phone}  팩스번호 {fax}  /  {email}  /  {disclosure}", 맨 아래 **가로선**. 두문의 제목 줄 아래에도 가로선. 서식의 "기안자·검토자·결재권자·발신명" 같은 용어는 표시하지 않고 내용만 적는다(서식 비고)
6. 날짜·시각은 그대로 받되 `YYYY-MM-DD`·`YYYY.MM.DD` 꼴이면 `YYYY. MM. DD.`로 정규화(영 제7조⑤). `disclosure`는 "공개"|"부분공개"|"비공개"만, 아니면 `check_structure` 오류
7. 성명·전화는 보고서·보도자료와 같은 정화 규칙: `name`이 비어 있으면 서명 칸을 비우고(자리표시 "○○○" 아님), 전화·팩스는 입력값 그대로(검증 테스트는 `044-000-0000`류 자리표시 사용)
8. 쪽: 보고서와 같은 A4(영 제7조⑥). 머리·꼬리 없음. 로고(`logo_path`)는 두문 여백에 넣을 수 있음(선택, 보고서 로고 처리 재사용)
9. `export_markdown=True`면 같은 내용을 .md로(제목 `#`, 항목은 번호 글자 그대로, 결문은 표 없이 줄로)

`get_writing_guide(doc_type="official")`: 위 구조와 규칙(항목 구분·날짜·금액·끝 표시·붙임)을 사용자 AI용 지침으로 돌려준다. 기존 `writing_guide_prompt`도 official 지원.

## B. 코드 정리 (Solar Pro 4 품질 보강)
- `server.py`와 `engine/report.py`에 중복된 `_strip_existing_number`·`_simplify_numbers`·`_add_table_numbers`를 `engine/report.py` 한 곳으로 모으고 server는 import해서 쓴다
- `build_document`의 간소화 모드 표 병합 풀기(`s_for_md` 조립)를 함수로 빼서 report·official이 같이 쓴다
- `check_structure`에 official 검증 추가(필수 키, to·disclosure 허용값, 결재란 drafter·approver 필수, attachments는 문자열 목록)
- 바꾼 뒤에도 기존 테스트 전부 통과. 새 기능 외 동작 변경 없음(생성 파일 비교 테스트 `test_report`·`test_simplified`·`test_internal_spacing`이 지킴)

## C. 문서
- README·README-EN: 문서 종류 표의 "기안문 — 다음 버전 예정"을 지원으로 바꾸고 구조 예시 1개, "한글 '개요' 번호 연동은 다음 버전"은 그대로
- CHANGELOG 0.3.0, pyproject 0.3.0

## 완료 조건
`tests/test_official.py` 전부 통과(수정 금지) + 기존 테스트 전부 통과. `.venv/bin/python -m pytest tests -q`
