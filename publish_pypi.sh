#!/bin/sh
# PyPI 업로드: 맥 키체인의 계정 전체 범위 토큰(korean-tax-calc-mcp-pypi) 우선 사용, 없으면 korean-report-hwpx-pypi,
# 둘 다 없으면 클립보드의 pypi- 토큰을 키체인(korean-report-hwpx-pypi)에 저장. 화면 출력 없음
cd "$(dirname "$0")"
T="$(security find-generic-password -s korean-tax-calc-mcp-pypi -w 2>/dev/null)"
[ -z "$T" ] && T="$(security find-generic-password -s korean-report-hwpx-pypi -w 2>/dev/null)"
if [ -z "$T" ]; then
  T="$(pbpaste | tr -d '[:space:]')"
  case "$T" in
    pypi-*) security add-generic-password -U -a __token__ -s korean-report-hwpx-pypi -w "$T" && echo "토큰을 키체인에 저장했습니다(다음부터 복사 불필요)";;
    *) echo "키체인에 토큰이 없고 클립보드도 pypi- 토큰이 아닙니다 — PyPI에서 새 토큰을 만들고 Copy token 후 다시 실행"; exit 1;;
  esac
fi
PY=.venv/bin/python; [ -x "$PY" ] || PY=../korean-tax-calc-mcp/.venv/bin/python
V=$(sed -n 's/^version = "\(.*\)"/\1/p' pyproject.toml)
TWINE_USERNAME=__token__ TWINE_PASSWORD="$T" "$PY" -c "import truststore,sys;truststore.inject_into_ssl();from twine.__main__ import main;sys.argv=['twine','upload','--non-interactive','--skip-existing','dist/korean_report_hwpx-$V-py3-none-any.whl','dist/korean_report_hwpx-$V.tar.gz'];sys.exit(main())" >/dev/null && echo "업로드완료 $V"
