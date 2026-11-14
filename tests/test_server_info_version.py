"""initialize 응답의 serverInfo.version이 비지 않고 설치된 패키지 버전과 같은지. 작성 Mia(윤승미)

2026-11-14 `uvx korean-report-hwpx==0.5.5`의 initialize 응답에서 serverInfo.version이 ''였다
(MCPServer에 version을 넘기지 않았다). korean-tax-mcp 0.15.2와 같은 방식으로 패키지 메타데이터 버전을 넘긴다.
"""
import asyncio
from importlib.metadata import version

from mcp import Client

import korean_report_hwpx
from korean_report_hwpx.server import mcp


def test_server_info_version_matches_installed_package():
    async def run():
        async with Client(mcp) as c:
            return c.server_info

    info = asyncio.run(run())
    assert info is not None and info.name == "korean-report-hwpx"
    assert info.version, "serverInfo.version이 비어 있음"
    assert info.version == version("korean-report-hwpx") == korean_report_hwpx.__version__
