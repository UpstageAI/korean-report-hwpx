# Windows 호환성 안내

korean-report-hwpx는 기본적으로 Windows에서도 동작합니다. 다만 일부 기능은 플랫폼 제한이 있습니다.

## 동작하는 기능 (Windows 포함 모든 플랫폼)

- `get_writing_guide` — 작성 규칙 안내
- `check_structure` — 구조 JSON 점검
- `build_document` / `build_from_structure` — HWPX 생성 (표준 모드, 간소화 모드)
- `export_markdown=True` — 마크다운 동시 출력
- `list_ministries` — 지원 기관 목록
- `get_rules` — 서식 규칙값 조회

## macOS 전용 기능 (Windows에서 생략됨)

### polish=True (자간 다듬기)

**현황**: `polish=True` 옵션은 macOS + 한컴오피스 HWP가 있을 때만 실제 줄 배치를 받아 문단별 자간을 다듬습니다.

**Windows 동작**: Windows에서 `polish=True`를 지정해도 오류 없이 생성만 수행되며, 자간 다듬기는 생략됩니다. 로그로 "polish는 macOS + 한컴오피스 한글 필요 — Windows/리눅스에서는 생략" 메시지가 출력됩니다.

**이유**: macOS 전용 기술에 의존합니다:
- `osascript` (AppleScript) — 한글 앱 메뉴 조작
- `ioreg` — 사용자 입력 대기 시간 확인
- `pgrep` — 한글 프로세스 확인
- `open -a` — 맥 앱 실행
- `screencapture` — 화면 캡처
- `/Applications/Hancom Office HWP.app` 경로

### Hancom Office HWP 필요

맥에서 polish를 사용하려면 한컴오피스 한글이 설치되어 있어야 합니다. Windows용 한글도 존재하지만, 현재 polish 구현은 macOS 전용 AppleScript 기반으로 작성되어 있어 Windows용 한글 자동화는 지원하지 않습니다.

## 경로 관련 참고

- 출력 디렉토리 기본값: `~/korean-report-hwpx/` (Windows에서도 `%USERPROFILE%\korean-report-hwpx\`로 정상 동작)
- 환경변수 `KOREAN_REPORT_HWPX_OUT_DIR` 또는 `KOREAN_GOV_DOCS_OUT_DIR`로 변경 가능
- `out_path` 인자로 임의의 Windows 경로(예: `C:\Users\user\Documents\report.hwpx`) 지정 가능

## 주의사항

- 생성된 HWPX 파일은 Windows용 한글(또는 한컴오피스)에서 열 수 있습니다.
- 글꼴은 사용하는 컴퓨터에 설치된 글꼴로 표시됩니다. Windows에 없는 글꼴( HY헤드라인M, 함초롬바탕 등)은 대체 글꼴로 표시됩니다.
- 간소화 모드(`style="simplified"`)는 플랫폼 무관하게 모든 기능이 동작합니다.
