"""korean-report-hwpx — 한국 공문서 HWPX 생성 MCP 서버."""
from importlib.metadata import PackageNotFoundError, version as _pkg_version

# 버전은 pyproject.toml 한 곳에서만 관리한다. MCPServer에 넘기지 않아 initialize 응답의 serverInfo.version이 ''였다(2026-11-14).
try:
    __version__ = _pkg_version("korean-report-hwpx")
except PackageNotFoundError:  # 설치하지 않고 소스 폴더에서 바로 돌릴 때
    __version__ = "0.0.0+unknown"
